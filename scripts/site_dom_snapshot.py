import argparse
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


ROOT = Path(__file__).resolve().parents[1]


def _check_patterns(text: str, patterns: List[str], mode: str) -> Tuple[bool, Dict[str, bool]]:
    found: Dict[str, bool] = {}
    for pat in patterns:
        if pat.startswith("re:"):
            ok = bool(re.search(pat[3:], text, flags=re.IGNORECASE))
        else:
            ok = pat.lower() in text.lower()
        found[pat] = ok
    if mode == "all":
        return all(found.values()), found
    return any(found.values()), found


def _digest_html(text: str) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    return hashlib.sha256(compact.encode("utf-8", errors="ignore")).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _save_report(path: Path, report: Dict[str, Any]) -> Tuple[Path, Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stamped = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    stamped.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, stamped


def _snapshot_url(url: str, groups: List[Dict[str, Any]], timeout_sec: int) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "url": url,
        "ok": False,
        "status_code": 0,
        "elapsed_ms": 0,
        "html_len": 0,
        "html_hash": "",
        "groups": [],
        "error": "",
    }
    started = time.perf_counter()
    try:
        res = requests.get(
            url,
            timeout=max(5, int(timeout_sec)),
            headers={"User-Agent": "Mozilla/5.0 (compatible; SeoulMNA-DOM-Snapshot/1.0)"},
        )
        body = res.text or ""
        row["status_code"] = int(res.status_code)
        row["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        row["html_len"] = len(body)
        row["html_hash"] = _digest_html(body)

        required_ok = True
        for group in groups:
            hit, found_map = _check_patterns(body, list(group.get("patterns", [])), str(group.get("mode", "any")))
            required = bool(group.get("required", True))
            row["groups"].append(
                {
                    "id": str(group.get("id", "")),
                    "required": required,
                    "ok": bool(hit),
                    "mode": str(group.get("mode", "any")),
                    "found": found_map,
                }
            )
            if required and not hit:
                required_ok = False
        row["ok"] = int(res.status_code) == 200 and required_ok
    except Exception as exc:
        row["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        row["error"] = str(exc)
    return row


def _group_ok_map(result: Dict[str, Any]) -> Dict[str, bool]:
    out: Dict[str, bool] = {}
    for g in list(result.get("groups") or []):
        gid = str(g.get("id", "")).strip()
        if gid:
            out[gid] = bool(g.get("ok", False))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture DOM marker snapshot and detect regressions.")
    parser.add_argument("--report", default="logs/site_dom_snapshot_latest.json")
    parser.add_argument("--timeout-sec", type=int, default=20)
    args = parser.parse_args()

    report_path = (ROOT / str(args.report)).resolve()
    prev = _load_json(report_path)
    prev_results = {str(x.get("url", "")): x for x in list(prev.get("results") or [])}

    configs = [
        {
            "url": "https://seoulmna.co.kr/",
            "groups": [
                {"id": "quickmenu", "mode": "any", "patterns": ["quick_menu", "smna-quick", 'id="quicks"']},
                {"id": "login_signal", "mode": "any", "patterns": ["/bbs/login.php", "login"]},
                {"id": "global_banner", "mode": "any", "patterns": ["smna-global-banner", "SEOULMNA GLOBAL BANNER START"]},
                {"id": "footer_or_address", "mode": "any", "patterns": ["footer", "주소", "대표전화"]},
            ],
        },
        {
            "url": "https://seoulmna.kr/",
            "groups": [
                {"id": "footer_exists", "mode": "any", "patterns": ["<footer", "class=\"footer", "id=\"ft"]},
                {"id": "login_signal", "mode": "any", "patterns": ["wp-login.php", "login"]},
            ],
        },
    ]

    results: List[Dict[str, Any]] = []
    regressions: List[Dict[str, Any]] = []
    hash_changes = 0
    for cfg in configs:
        current = _snapshot_url(str(cfg["url"]), list(cfg["groups"]), int(args.timeout_sec))
        results.append(current)
        previous = prev_results.get(str(cfg["url"]))
        if previous:
            if str(previous.get("html_hash", "")) and str(previous.get("html_hash", "")) != str(current.get("html_hash", "")):
                hash_changes += 1
            prev_map = _group_ok_map(previous)
            cur_map = _group_ok_map(current)
            for gid, prev_ok in prev_map.items():
                if prev_ok and (gid in cur_map) and (not cur_map[gid]):
                    regressions.append({"url": str(cfg["url"]), "group": gid, "type": "marker_regression"})

    required_ok = all(bool(r.get("ok", False)) for r in results)
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": required_ok and len(regressions) == 0,
        "result_count": len(results),
        "hash_changes": hash_changes,
        "regression_count": len(regressions),
        "regressions": regressions,
        "results": results,
    }

    latest, stamped = _save_report(report_path, report)
    print(f"[saved] {latest}")
    print(f"[saved] {stamped}")
    print(
        "[summary] "
        + f"ok={report['ok']} "
        + f"results={len(results)} "
        + f"regressions={len(regressions)} "
        + f"hash_changes={hash_changes}"
    )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
