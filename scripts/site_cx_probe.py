import argparse
import json
import re
import sys
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


def _probe_url(url: str, rules: List[Dict[str, Any]], timeout_sec: int) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "url": url,
        "ok": False,
        "status_code": 0,
        "elapsed_ms": 0,
        "rules": [],
        "error": "",
    }
    started = time.perf_counter()
    try:
        res = requests.get(
            url,
            timeout=max(5, int(timeout_sec)),
            headers={"User-Agent": "Mozilla/5.0 (compatible; SeoulMNA-CX-Probe/1.0)"},
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        body = res.text or ""
        row["status_code"] = int(res.status_code)
        row["elapsed_ms"] = elapsed_ms
        row["html_len"] = len(body)

        for rule in rules:
            hit, found_map = _check_patterns(body, list(rule.get("patterns", [])), str(rule.get("mode", "any")))
            row["rules"].append(
                {
                    "id": str(rule.get("id", "")),
                    "ok": bool(hit),
                    "required": bool(rule.get("required", True)),
                    "mode": str(rule.get("mode", "any")),
                    "found": found_map,
                }
            )

        required_ok = all(bool(r.get("ok")) for r in row["rules"] if bool(r.get("required", True)))
        row["latency_warn"] = False
        row["ok"] = int(res.status_code) == 200 and required_ok
    except Exception as exc:
        row["error"] = str(exc)
        row["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    return row


def _write_report(report: Dict[str, Any], out_rel: str) -> Tuple[Path, Path]:
    latest = (ROOT / str(out_rel)).resolve()
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stamped = latest.with_name(f"{latest.stem}_{stamp}{latest.suffix}")
    stamped.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return latest, stamped


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe SeoulMNA public CX markers and basic availability.")
    parser.add_argument("--report", default="logs/site_cx_probe_latest.json")
    parser.add_argument("--timeout-sec", type=int, default=20)
    parser.add_argument("--latency-warn-ms", type=int, default=3500)
    args = parser.parse_args()

    # Required checks focus on critical customer journey paths.
    probes = [
        {
            "url": "https://seoulmna.kr/",
            "rules": [
                {"id": "title_brand", "mode": "any", "patterns": ["서울건설정보", "<title"]},
                {"id": "footer_or_contact", "mode": "any", "patterns": ["<footer", "010-9926-8661", "대표"]},
                {"id": "login_signal", "mode": "any", "patterns": ["로그인", "wp-login.php", "login"]},
                {"id": "calc_signal_optional", "mode": "any", "required": False, "patterns": ["양도", "계산기", "consult"]},
            ],
        },
        {
            "url": "https://seoulmna.co.kr/",
            "rules": [
                {"id": "quickmenu", "mode": "any", "patterns": ["quick_menu", "smna-quick", "id=\"quicks\""]},
                {"id": "login_signal", "mode": "any", "patterns": ["/bbs/login.php", "로그인", "login"]},
                {"id": "global_banner", "mode": "any", "patterns": ["smna-global-banner", "SEOULMNA GLOBAL BANNER START"]},
                {"id": "traffic_counter", "mode": "any", "patterns": ["SEOULMNA TRAFFIC COUNTER START", "__smna_tc__"]},
                {"id": "footer_or_address", "mode": "any", "patterns": ["주소", "대표전화", "사업자", "footer"]},
            ],
        },
        {
            "url": "https://seoulmna.kr/yangdo-ai-customer/",
            "rules": [
                {"id": "form_buttons", "mode": "all", "patterns": ['id="btn-estimate"', 'id="btn-mail-consult"', 'id="btn-submit-consult"']},
                {"id": "result_blocks", "mode": "any", "patterns": ['id="consult-summary"', "recommend-actions", "openchat"]},
            ],
        },
        {
            "url": "https://seoulmna.kr/ai-license-acquisition-calculator/",
            "rules": [
                {"id": "acq_buttons", "mode": "all", "patterns": ['id="acq-btn-calc"', 'id="acq-btn-mail"']},
                {"id": "acq_root", "mode": "any", "patterns": ['id="smna-acq-calculator"', "consultEndpoint"]},
            ],
        },
    ]

    rows: List[Dict[str, Any]] = []
    for p in probes:
        row = _probe_url(str(p["url"]), list(p["rules"]), timeout_sec=int(args.timeout_sec))
        row["latency_warn"] = row.get("elapsed_ms", 0) > int(args.latency_warn_ms)
        rows.append(row)

    total = len(rows)
    ok_count = sum(1 for r in rows if bool(r.get("ok")))
    hard_ok = ok_count == total
    latency_warn_count = sum(1 for r in rows if bool(r.get("latency_warn")))

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": hard_ok,
        "ok_count": ok_count,
        "total_count": total,
        "latency_warn_count": latency_warn_count,
        "latency_warn_ms": int(args.latency_warn_ms),
        "results": rows,
    }

    latest, stamped = _write_report(report, args.report)
    print(f"[saved] {latest}")
    print(f"[saved] {stamped}")
    print(f"[summary] ok={hard_ok} ok_count={ok_count}/{total} latency_warn={latency_warn_count}")
    return 0 if hard_ok else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    raise SystemExit(main())
