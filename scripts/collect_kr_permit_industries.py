import argparse
import base64
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_URL = "https://www.localdata.go.kr/data/allDataView.do?menuNo=10002"
DEFAULT_OUTPUT_PATH = ROOT / "config" / "kr_permit_industries_localdata.json"


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _fetch_html_via_powershell(url: str, timeout_sec: int) -> str:
    safe_url = str(url or "").replace("'", "''").strip()
    if not safe_url:
        raise ValueError("source url is empty")
    command = (
        "$ProgressPreference='SilentlyContinue'; "
        f"$resp=Invoke-WebRequest -UseBasicParsing '{safe_url}' -TimeoutSec {max(5, int(timeout_sec))}; "
        "if($null -ne $resp.RawContentStream){"
        "$ms=New-Object System.IO.MemoryStream; "
        "$resp.RawContentStream.Position=0; "
        "$resp.RawContentStream.CopyTo($ms); "
        "$bytes=$ms.ToArray();"
        "} else {"
        "$bytes=[System.Text.Encoding]::UTF8.GetBytes([string]$resp.Content);"
        "}; "
        "[Convert]::ToBase64String($bytes)"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        stderr = _compact(proc.stderr)
        stdout = _compact(proc.stdout)
        detail = stderr or stdout or f"exit_code={proc.returncode}"
        raise RuntimeError(f"failed to fetch source html via powershell: {detail}")
    encoded = _compact(proc.stdout)
    if not encoded:
        raise RuntimeError("fetched html is empty")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
        return raw.decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"failed to decode powershell fetch payload: {exc}") from exc


def _parse_localdata_html(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    major_map = {}
    for li in soup.select("li.opncategory-li[id^='cateli-']"):
        code = str(li.get("id", "")).replace("cateli-", "").strip()
        if not code:
            continue
        texts = [_compact(p.get_text(" ", strip=True)) for p in li.select("p")]
        declared_group_count = None
        if len(texts) >= 4:
            m = re.search(r"(\d+)", texts[3])
            if m:
                declared_group_count = int(m.group(1))
        major_map[code] = {
            "major_code": code,
            "major_name": texts[1] if len(texts) > 1 else "",
            "major_description": texts[2] if len(texts) > 2 else "",
            "declared_group_count": declared_group_count,
        }

    industries = []
    for li in soup.select("li.group-li"):
        classes = list(li.get("class", []) or [])
        major_code = ""
        for cls in classes:
            m = re.match(r"opncategory_(\d+)$", str(cls))
            if m:
                major_code = m.group(1)
                break
        if not major_code:
            continue

        group_info = li.select_one("div.grouplist-info")
        group_name = ""
        group_description = ""
        group_total = None
        if group_info:
            group_name_node = group_info.select_one(".grouplist-icon p:last-of-type")
            if group_name_node:
                group_name = _compact(group_name_node.get_text(" ", strip=True))
            direct_divs = group_info.find_all("div", recursive=False)
            if len(direct_divs) >= 2:
                group_description = _compact(direct_divs[1].get_text(" ", strip=True))
            if len(direct_divs) >= 3:
                m = re.search(r"(\d+)", _compact(direct_divs[2].get_text(" ", strip=True)))
                if m:
                    group_total = int(m.group(1))

        for anchor in li.select("ul.opnsvclist-info a[href*='fDataViewD']"):
            href = str(anchor.get("href", ""))
            m = re.search(
                r"fDataViewD\('([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\)",
                href,
            )
            if not m:
                continue
            cat_code, grp_code, svc_code = m.group(1), m.group(2), m.group(3)
            service_name = _compact(anchor.get_text(" ", strip=True))
            detail_url = (
                "https://www.localdata.go.kr/data/dataView.do"
                f"?ctgryGbn={cat_code}&groupGbn={grp_code}&opnSvcId={svc_code}"
            )
            major_meta = major_map.get(cat_code, {})
            industries.append(
                {
                    "major_code": cat_code,
                    "major_name": major_meta.get("major_name", ""),
                    "group_code": grp_code,
                    "group_name": group_name,
                    "group_description": group_description,
                    "group_declared_total": group_total,
                    "service_code": svc_code,
                    "service_name": service_name,
                    "detail_url": detail_url,
                }
            )

    dedup = {}
    for row in industries:
        dedup[row["service_code"]] = row
    industries_sorted = sorted(dedup.values(), key=lambda r: r["service_code"])

    counts_by_major = Counter(row.get("major_name", "") for row in industries_sorted)
    counts_by_major = {k: counts_by_major[k] for k in sorted(counts_by_major)}

    group_counter = Counter(
        (row.get("major_code", ""), row.get("group_code", ""), row.get("group_name", ""))
        for row in industries_sorted
    )
    groups = []
    for key in sorted(group_counter, key=lambda x: (x[0], x[1], x[2])):
        major_code, group_code, group_name = key
        sample = next(
            (
                row
                for row in industries_sorted
                if row.get("major_code") == major_code
                and row.get("group_code") == group_code
                and row.get("group_name") == group_name
            ),
            {},
        )
        groups.append(
            {
                "major_code": major_code,
                "major_name": sample.get("major_name", ""),
                "group_code": group_code,
                "group_name": group_name,
                "group_description": sample.get("group_description", ""),
                "industry_count": int(group_counter[key]),
                "group_declared_total": sample.get("group_declared_total"),
            }
        )

    major_categories = []
    for code in sorted(major_map):
        info = dict(major_map[code])
        name = info.get("major_name", "")
        info["industry_count"] = int(counts_by_major.get(name, 0))
        major_categories.append(info)

    return {
        "source": {
            "name": "LOCALDATA 지방행정인허가데이터개방",
            "url": source_url,
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        },
        "summary": {
            "industry_total": len(industries_sorted),
            "major_category_total": len(major_categories),
            "group_total": len(groups),
            "counts_by_major": counts_by_major,
        },
        "major_categories": major_categories,
        "groups": groups,
        "industries": industries_sorted,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect all Korean permit/licensing industries from LOCALDATA and export JSON",
    )
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument(
        "--input-html",
        default="",
        help="Optional local HTML path. If provided, skip network fetch and parse this file.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--expect-total", type=int, default=195)
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code if total count mismatches.")
    parser.add_argument("--timeout-sec", type=int, default=30)
    args = parser.parse_args()

    input_html = str(args.input_html or "").strip()
    source_url = str(args.source_url or "").strip() or DEFAULT_SOURCE_URL
    if input_html:
        html_path = Path(input_html).expanduser().resolve()
        html = html_path.read_text(encoding="utf-8", errors="replace")
    else:
        html = _fetch_html_via_powershell(source_url, timeout_sec=max(5, int(args.timeout_sec)))

    payload = _parse_localdata_html(html, source_url=source_url)
    industry_total = int(payload.get("summary", {}).get("industry_total", 0))
    expected_total = int(args.expect_total or 0)

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[saved] {output_path}")
    print(f"[summary] total_industries={industry_total}, expected={expected_total}")
    print(f"[summary] counts_by_major={json.dumps(payload.get('summary', {}).get('counts_by_major', {}), ensure_ascii=False)}")

    if expected_total > 0 and industry_total != expected_total:
        msg = f"[warn] collected industry count mismatch: expected={expected_total}, actual={industry_total}"
        print(msg)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
