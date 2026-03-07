import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, List

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import load_config, setup_logger

CONFIG = load_config(
    {
        "CLOUDFLARE_API_TOKEN": "",
        "CLOUDFLARE_ZONE_ID": "",
        "CLOUDFLARE_SECURITY_LEVEL": "high",
        "CLOUDFLARE_ALWAYS_USE_HTTPS": "on",
        "CLOUDFLARE_BROWSER_CHECK": "on",
        "CLOUDFLARE_REPORT_FILE": "logs/cloudflare_baseline_latest.json",
    }
)

logger = setup_logger(name="cloudflare_baseline")


def _api_request(
    method: str,
    zone_id: str,
    token: str,
    setting_id: str,
    value: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/{setting_id}"
    payload = {"value": value}
    if dry_run:
        return {"ok": True, "dry_run": True, "setting": setting_id, "value": value}
    res = requests.patch(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=20,
    )
    body = {}
    try:
        body = res.json()
    except Exception:
        body = {"raw": res.text[:500]}
    ok = bool(res.status_code < 300 and body.get("success"))
    return {
        "ok": ok,
        "status": int(res.status_code),
        "setting": setting_id,
        "value": value,
        "response": body if not ok else {"success": True},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply baseline Cloudflare security settings")
    parser.add_argument("--token", default=str(CONFIG.get("CLOUDFLARE_API_TOKEN", "")).strip())
    parser.add_argument("--zone-id", default=str(CONFIG.get("CLOUDFLARE_ZONE_ID", "")).strip())
    parser.add_argument("--security-level", default=str(CONFIG.get("CLOUDFLARE_SECURITY_LEVEL", "high")).strip() or "high")
    parser.add_argument("--always-use-https", default=str(CONFIG.get("CLOUDFLARE_ALWAYS_USE_HTTPS", "on")).strip() or "on")
    parser.add_argument("--browser-check", default=str(CONFIG.get("CLOUDFLARE_BROWSER_CHECK", "on")).strip() or "on")
    parser.add_argument("--report", default=str(CONFIG.get("CLOUDFLARE_REPORT_FILE", "logs/cloudflare_baseline_latest.json")).strip())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.token or not args.zone_id:
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "skipped": True,
            "reason": "missing_cloudflare_credentials",
            "required_env": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ZONE_ID"],
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    steps: List[Dict[str, Any]] = []
    steps.append(
        _api_request(
            method="PATCH",
            zone_id=args.zone_id,
            token=args.token,
            setting_id="security_level",
            value=args.security_level,
            dry_run=bool(args.dry_run),
        )
    )
    steps.append(
        _api_request(
            method="PATCH",
            zone_id=args.zone_id,
            token=args.token,
            setting_id="always_use_https",
            value=args.always_use_https,
            dry_run=bool(args.dry_run),
        )
    )
    steps.append(
        _api_request(
            method="PATCH",
            zone_id=args.zone_id,
            token=args.token,
            setting_id="browser_check",
            value=args.browser_check,
            dry_run=bool(args.dry_run),
        )
    )

    ok = all(bool(s.get("ok")) for s in steps)
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok,
        "dry_run": bool(args.dry_run),
        "zone_id_masked": (args.zone_id[:6] + "***") if args.zone_id else "",
        "steps": steps,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if ok:
        logger.info("cloudflare baseline applied: zone=%s dry_run=%s", report["zone_id_masked"], bool(args.dry_run))
    else:
        logger.warning("cloudflare baseline partially failed: zone=%s", report["zone_id_masked"])
    print(json.dumps(report, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
