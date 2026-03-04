import argparse
import json
import time
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"json root must be object: {path}")
    return data


def _check_report(path: Path, max_age_hours: float, must_ok: bool) -> Dict:
    row: Dict = {
        "path": str(path),
        "exists": path.exists(),
        "age_hours": None,
        "fresh": False,
        "has_ok": False,
        "ok_value": None,
        "pass": False,
        "error": "",
    }
    if not path.exists():
        row["error"] = "missing"
        return row

    try:
        payload = _read_json(path)
        age_hours = (time.time() - path.stat().st_mtime) / 3600.0
        row["age_hours"] = round(age_hours, 3)
        row["fresh"] = age_hours <= float(max_age_hours)
        row["has_ok"] = "ok" in payload
        row["ok_value"] = payload.get("ok")
        row["pass"] = row["fresh"] and ((row["has_ok"] and bool(payload.get("ok"))) if must_ok else True)
        if not row["fresh"]:
            row["error"] = f"stale>{max_age_hours}h"
        elif must_ok and not bool(payload.get("ok")):
            row["error"] = "ok=false"
        elif must_ok and not row["has_ok"]:
            row["error"] = "ok-key-missing"
    except Exception as exc:
        row["error"] = str(exc)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate freshness/health of WP+CX guard reports.")
    parser.add_argument("--wp-site-guard", default="logs/wp_site_guard_latest.json")
    parser.add_argument("--rankmath-detail", default="logs/rankmath_detail_opt_latest.json")
    parser.add_argument("--cx-probe", default="logs/site_cx_probe_latest.json")
    parser.add_argument("--cx-autoheal", default="logs/site_cx_autoheal_latest.json")
    parser.add_argument("--dom-snapshot", default="logs/site_dom_snapshot_latest.json")
    parser.add_argument("--health-rollup", default="logs/site_cx_health_rollup_latest.json")
    parser.add_argument("--health-digest", default="logs/site_cx_health_digest_latest.json")
    parser.add_argument("--force-recover", default="logs/site_cx_force_recover_latest.json")
    parser.add_argument("--max-age-hours", type=float, default=8.0)
    parser.add_argument("--allow-autoheal-missing", action="store_true")
    parser.add_argument("--allow-dom-missing", action="store_true")
    parser.add_argument("--allow-rollup-missing", action="store_true")
    parser.add_argument("--allow-digest-missing", action="store_true")
    parser.add_argument("--allow-force-recover-missing", action="store_true")
    args = parser.parse_args()

    checks: List[Dict] = []
    checks.append(
        _check_report((ROOT / str(args.wp_site_guard)).resolve(), float(args.max_age_hours), must_ok=True)
    )
    checks.append(
        _check_report((ROOT / str(args.rankmath_detail)).resolve(), float(args.max_age_hours), must_ok=True)
    )
    checks.append(
        _check_report((ROOT / str(args.cx_probe)).resolve(), float(args.max_age_hours), must_ok=True)
    )

    autoheal_path = (ROOT / str(args.cx_autoheal)).resolve()
    autoheal = _check_report(autoheal_path, float(args.max_age_hours), must_ok=True)
    if bool(args.allow_autoheal_missing) and (not autoheal.get("exists")):
        autoheal["pass"] = True
        autoheal["error"] = ""
    checks.append(autoheal)

    dom_path = (ROOT / str(args.dom_snapshot)).resolve()
    dom = _check_report(dom_path, float(args.max_age_hours), must_ok=True)
    if bool(args.allow_dom_missing) and (not dom.get("exists")):
        dom["pass"] = True
        dom["error"] = ""
    checks.append(dom)

    rollup_path = (ROOT / str(args.health_rollup)).resolve()
    rollup = _check_report(rollup_path, float(args.max_age_hours), must_ok=True)
    if bool(args.allow_rollup_missing) and (not rollup.get("exists")):
        rollup["pass"] = True
        rollup["error"] = ""
    checks.append(rollup)

    digest_path = (ROOT / str(args.health_digest)).resolve()
    digest = _check_report(digest_path, float(args.max_age_hours), must_ok=False)
    if bool(args.allow_digest_missing) and (not digest.get("exists")):
        digest["pass"] = True
        digest["error"] = ""
    checks.append(digest)

    force_path = (ROOT / str(args.force_recover)).resolve()
    force_report = _check_report(force_path, float(args.max_age_hours), must_ok=False)
    if bool(args.allow_force_recover_missing) and (not force_report.get("exists")):
        force_report["pass"] = True
        force_report["error"] = ""
    checks.append(force_report)

    overall = all(bool(row.get("pass")) for row in checks)
    print(f"[summary] ok={overall} checks={len(checks)}")
    for row in checks:
        print(
            "[check] "
            + f"path={row.get('path')} "
            + f"pass={row.get('pass')} "
            + f"fresh={row.get('fresh')} "
            + f"ok={row.get('ok_value')} "
            + f"age_h={row.get('age_hours')} "
            + f"err={row.get('error')}"
        )
    return 0 if overall else 2


if __name__ == "__main__":
    raise SystemExit(main())
