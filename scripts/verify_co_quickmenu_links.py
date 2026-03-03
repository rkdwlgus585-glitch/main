import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]
FALLBACK_URL_BY_LABEL: Dict[str, str] = {
    "한국정보통신공사협회": "https://search.naver.com/search.naver?query=%ED%95%9C%EA%B5%AD%EC%A0%95%EB%B3%B4%ED%86%B5%EC%8B%A0%EA%B3%B5%EC%82%AC%ED%98%91%ED%9A%8C",
}


def _extract_map_from_snippet(snippet_text: str) -> Dict[str, str]:
    patt = re.compile(r"var\s+QUICK_MENU_LINK_MAP\s*=\s*\{(.*?)\};", flags=re.S)
    m = patt.search(snippet_text)
    if not m:
        return {}
    body = m.group(1)
    kv_patt = re.compile(r'"([^"]+)"\s*:\s*"([^"]+)"')
    out: Dict[str, str] = {}
    for k, v in kv_patt.findall(body):
        key = str(k or "").strip()
        val = str(v or "").strip()
        if key and val:
            out[key] = val
    return out


def _check_url(url: str, timeout_sec: int) -> Dict[str, object]:
    try:
        res = requests.get(
            str(url),
            timeout=max(5, int(timeout_sec)),
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
            verify=False,
        )
        return {
            "ok": bool(200 <= int(res.status_code) < 400),
            "status_code": int(res.status_code),
            "final_url": str(res.url or ""),
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": None,
            "final_url": "",
            "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate outbound quick-menu links from global banner snippet")
    parser.add_argument("--snippet", default="logs/co_global_banner_snippet.html")
    parser.add_argument("--report", default="logs/co_quickmenu_target_link_health_latest.json")
    parser.add_argument("--timeout-sec", type=int, default=20)
    args = parser.parse_args()

    snippet_path = (ROOT / str(args.snippet)).resolve()
    if not snippet_path.exists():
        raise SystemExit(f"snippet file not found: {snippet_path}")

    snippet_text = snippet_path.read_text(encoding="utf-8", errors="replace")
    link_map = _extract_map_from_snippet(snippet_text)
    if not link_map:
        raise SystemExit("QUICK_MENU_LINK_MAP not found in snippet")

    requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]

    rows: List[Dict[str, object]] = []
    ok_count = 0
    for label, url in link_map.items():
        chk = _check_url(url, timeout_sec=int(args.timeout_sec))
        primary_ok = bool(chk.get("ok"))
        fallback_url = str(FALLBACK_URL_BY_LABEL.get(label, "")).strip()
        fallback_chk: Dict[str, object] = {}
        effective_ok = primary_ok
        if (not primary_ok) and fallback_url:
            fallback_chk = _check_url(fallback_url, timeout_sec=int(args.timeout_sec))
            effective_ok = bool(fallback_chk.get("ok"))
        ok = bool(effective_ok)
        if ok:
            ok_count += 1
        rows.append(
            {
                "label": label,
                "url": url,
                "ok": ok,
                "primary_ok": primary_ok,
                "status_code": chk.get("status_code"),
                "final_url": chk.get("final_url"),
                "error": chk.get("error"),
                "fallback_url": fallback_url,
                "fallback_ok": bool(fallback_chk.get("ok")) if fallback_chk else False,
                "fallback_status_code": fallback_chk.get("status_code") if fallback_chk else None,
                "fallback_final_url": fallback_chk.get("final_url") if fallback_chk else "",
                "fallback_error": fallback_chk.get("error") if fallback_chk else "",
            }
        )

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok_count": ok_count,
        "total_count": len(rows),
        "ok_rate": round((ok_count / max(1, len(rows))) * 100.0, 2),
        "results": rows,
    }

    out_path = (ROOT / str(args.report)).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[saved] {out_path}")
    print(f"[ok_rate] {report['ok_rate']}% ({ok_count}/{len(rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
