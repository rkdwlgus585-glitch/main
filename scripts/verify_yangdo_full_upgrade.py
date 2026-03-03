import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]


def _check_url_contains(url: str, required: List[str], timeout: int = 25) -> Dict:
    out = {
        "url": url,
        "ok": False,
        "status_code": 0,
        "found": {},
        "error": "",
        "length": 0,
    }
    try:
        res = requests.get(url, timeout=timeout)
        body = res.text or ""
        out["status_code"] = int(res.status_code)
        out["length"] = len(body)
        for key in required:
            if key.startswith("re:"):
                out["found"][key] = bool(re.search(key[3:], body, flags=re.I))
            else:
                out["found"][key] = bool(key in body)
        out["ok"] = res.status_code == 200 and all(bool(v) for v in out["found"].values())
    except Exception as e:
        out["error"] = str(e)
    return out


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify full upgrade status for co.kr banner and kr calculator")
    parser.add_argument("--co-home", default="https://seoulmna.co.kr/")
    parser.add_argument("--co-mna", default="https://seoulmna.co.kr/mna")
    parser.add_argument("--kr-customer", default="https://seoulmna.kr/yangdo-ai-customer/")
    parser.add_argument("--kr-acquisition", default="https://seoulmna.kr/ai-license-acquisition-calculator/")
    parser.add_argument("--report", default="logs/yangdo_full_upgrade_verify_latest.json")
    args = parser.parse_args()

    checks = []
    co_required = [
        "SEOULMNA GLOBAL BANNER START",
        "smna-global-banner",
        "https://seoulmna.kr/yangdo-ai-customer/",
        "https://seoulmna.kr/ai-license-acquisition-calculator/",
        "btn-chat",
    ]
    checks.append(_check_url_contains(args.co_home, co_required))
    checks.append(_check_url_contains(args.co_mna, co_required))

    checks.append(
        _check_url_contains(
            args.kr_customer,
            [
                'id="seoulmna-yangdo-calculator"',
                'id="btn-estimate"',
                'id="btn-mail-consult"',
                'id="btn-submit-consult"',
                'id="consult-summary"',
                'id="recommend-actions"',
                "const consultEndpoint",
                "has_any_signal",
                "openchat",
                "AI 양도가 산정 계산기",
            ],
        )
    )
    checks.append(
        _check_url_contains(
            args.kr_acquisition,
            [
                'id="smna-acq-calculator"',
                'id="acq-btn-calc"',
                'id="acq-btn-mail"',
                "const consultEndpoint",
                "AI 건설업 신규등록 비용 산정 계산기",
            ],
        )
    )

    overall_ok = all(bool(c.get("ok")) for c in checks)
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": overall_ok,
        "checks": checks,
    }
    out_path = (ROOT / args.report).resolve()
    _save_json(out_path, report)
    print(f"[saved] {out_path}")
    print(f"[overall_ok] {overall_ok}")
    for c in checks:
        print(f"- {c['url']} :: ok={c['ok']} status={c['status_code']} length={c['length']}")
        if c.get("error"):
            print(f"  error: {c['error']}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
