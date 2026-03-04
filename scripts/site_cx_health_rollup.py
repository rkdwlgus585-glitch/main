import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _mtime_age_minutes(path: Path) -> float:
    if not path.exists():
        return 10**9
    return (time.time() - path.stat().st_mtime) / 60.0


def _status_row(name: str, path: Path, required: bool, expect_ok: bool, max_age_min: float) -> Dict[str, Any]:
    payload = _read_json(path)
    exists = path.exists()
    age_min = _mtime_age_minutes(path)
    fresh = age_min <= float(max_age_min)
    has_ok = "ok" in payload
    ok_value = payload.get("ok")

    pass_ok = exists and fresh and has_ok and ((not expect_ok) or bool(ok_value))
    return {
        "name": name,
        "path": str(path),
        "required": bool(required),
        "exists": exists,
        "fresh": fresh,
        "age_min": round(age_min, 2),
        "ok_value": ok_value,
        "pass": bool(pass_ok),
    }


def _consecutive_failures(history_path: Path) -> int:
    if not history_path.exists():
        return 0
    rows = []
    with history_path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            s = str(raw or "").strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue
    streak = 0
    for row in reversed(rows):
        if bool(row.get("ok", False)):
            break
        streak += 1
    return streak


def _send_alert_if_needed(
    overall_ok: bool,
    message: str,
    detail_file: str,
    state_path: Path,
    repeat_min: float,
) -> Dict[str, Any]:
    prev = _read_json(state_path)
    prev_ok = bool(prev.get("ok", True))
    prev_alert_epoch = float(prev.get("last_alert_epoch", 0.0) or 0.0)
    now_epoch = time.time()

    should_alert = False
    reason = ""
    if overall_ok != prev_ok:
        should_alert = True
        reason = "state_changed"
    elif (not overall_ok) and ((now_epoch - prev_alert_epoch) >= float(repeat_min) * 60.0):
        should_alert = True
        reason = "repeat_failure"

    result = {
        "alert_sent": False,
        "reason": reason,
        "returncode": None,
        "stdout_tail": [],
        "stderr_tail": [],
    }

    if should_alert:
        severity = "info" if overall_ok else "critical"
        event = "site_cx_health_recovered" if overall_ok else "site_cx_health_failed"
        cmd = [
            sys.executable,
            "scripts/site_ops_alert.py",
            "--event",
            event,
            "--severity",
            severity,
            "--message",
            message,
            "--detail-file",
            detail_file,
        ]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        result["alert_sent"] = proc.returncode == 0
        result["returncode"] = int(proc.returncode)
        result["stdout_tail"] = (proc.stdout or "").splitlines()[-20:]
        result["stderr_tail"] = (proc.stderr or "").splitlines()[-20:]
        prev_alert_epoch = now_epoch

    next_state = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": bool(overall_ok),
        "last_alert_epoch": float(prev_alert_epoch),
    }
    _write_json(state_path, next_state)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build WP/CX health rollup and optionally send alerts.")
    parser.add_argument("--max-age-min", type=float, default=360.0)
    parser.add_argument("--latest-report", default="logs/site_cx_health_rollup_latest.json")
    parser.add_argument("--history", default="logs/site_cx_health_history.jsonl")
    parser.add_argument("--alert-on-change", action="store_true")
    parser.add_argument("--alert-state", default="logs/site_cx_health_alert_state.json")
    parser.add_argument("--alert-repeat-min", type=float, default=120.0)
    args = parser.parse_args()

    latest_path = (ROOT / str(args.latest_report)).resolve()
    history_path = (ROOT / str(args.history)).resolve()
    alert_state_path = (ROOT / str(args.alert_state)).resolve()
    max_age_min = float(args.max_age_min)

    checks = [
        _status_row("wp_site_guard", (ROOT / "logs/wp_site_guard_latest.json").resolve(), True, True, max_age_min),
        _status_row("rankmath_detail_opt", (ROOT / "logs/rankmath_detail_opt_latest.json").resolve(), True, True, max_age_min),
        _status_row("site_cx_probe", (ROOT / "logs/site_cx_probe_latest.json").resolve(), True, True, max_age_min),
        _status_row("site_cx_autoheal", (ROOT / "logs/site_cx_autoheal_latest.json").resolve(), False, True, max_age_min),
        _status_row("site_dom_snapshot", (ROOT / "logs/site_dom_snapshot_latest.json").resolve(), False, True, max_age_min),
    ]

    required_fail = [row for row in checks if row["required"] and (not row["pass"])]
    optional_fail = [row for row in checks if (not row["required"]) and (not row["pass"])]
    overall_ok = len(required_fail) == 0
    prev_streak = _consecutive_failures(history_path)
    fail_streak = 0 if overall_ok else (prev_streak + 1)

    report: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": overall_ok,
        "required_fail_count": len(required_fail),
        "optional_fail_count": len(optional_fail),
        "consecutive_failures": fail_streak,
        "checks": checks,
    }

    _write_json(latest_path, report)
    _append_jsonl(history_path, report)

    if bool(args.alert_on_change):
        short = (
            f"site-cx-health ok={overall_ok} required_fail={len(required_fail)} "
            f"optional_fail={len(optional_fail)} streak={fail_streak}"
        )
        report["alert"] = _send_alert_if_needed(
            overall_ok=overall_ok,
            message=short,
            detail_file=str(latest_path),
            state_path=alert_state_path,
            repeat_min=float(args.alert_repeat_min),
        )
        _write_json(latest_path, report)

    print(f"[saved] {latest_path}")
    print(f"[saved] {history_path}")
    print(
        "[summary] "
        + f"ok={overall_ok} "
        + f"required_fail={len(required_fail)} "
        + f"optional_fail={len(optional_fail)} "
        + f"streak={fail_streak}"
    )
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
