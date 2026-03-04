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


def _run(cmd: List[str]) -> Dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "cmd": cmd,
        "rc": int(proc.returncode),
        "elapsed_sec": round(time.time() - started, 3),
        "stdout_tail": (proc.stdout or "").splitlines()[-30:],
        "stderr_tail": (proc.stderr or "").splitlines()[-30:],
    }


def _load_history_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as f:
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
    return rows


def _consecutive_failures(rollup: Dict[str, Any], history_rows: List[Dict[str, Any]]) -> int:
    val = int(rollup.get("consecutive_failures", 0) or 0)
    if val > 0:
        return val
    streak = 0
    for row in reversed(history_rows):
        if bool(row.get("ok", False)):
            break
        streak += 1
    return streak


def main() -> int:
    parser = argparse.ArgumentParser(description="Force-recovery sequence for repeated site CX failures.")
    parser.add_argument("--rollup-file", default="logs/site_cx_health_rollup_latest.json")
    parser.add_argument("--rollup-history", default="logs/site_cx_health_history.jsonl")
    parser.add_argument("--state-file", default="logs/site_cx_force_recover_state.json")
    parser.add_argument("--report", default="logs/site_cx_force_recover_latest.json")
    parser.add_argument("--failure-threshold", type=int, default=2)
    parser.add_argument("--cooldown-min", type=float, default=180.0)
    parser.add_argument("--wp-description", default="건설업 면허 양도양수·신규등록·기업진단 전문")
    args = parser.parse_args()

    rollup_path = (ROOT / str(args.rollup_file)).resolve()
    history_path = (ROOT / str(args.rollup_history)).resolve()
    state_path = (ROOT / str(args.state_file)).resolve()
    report_path = (ROOT / str(args.report)).resolve()

    rollup = _read_json(rollup_path)
    history_rows = _load_history_rows(history_path)
    state = _read_json(state_path)

    now_epoch = time.time()
    cooldown_sec = max(0.0, float(args.cooldown_min) * 60.0)
    last_attempt_epoch = float(state.get("last_attempt_epoch", 0.0) or 0.0)
    cooldown_ok = (now_epoch - last_attempt_epoch) >= cooldown_sec
    fail_streak = _consecutive_failures(rollup, history_rows)
    threshold = max(1, int(args.failure_threshold))
    rollup_ok = bool(rollup.get("ok", True))

    report: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rollup_file": str(rollup_path),
        "history_file": str(history_path),
        "state_file": str(state_path),
        "failure_streak": fail_streak,
        "failure_threshold": threshold,
        "cooldown_min": float(args.cooldown_min),
        "cooldown_ok": cooldown_ok,
        "rollup_ok": rollup_ok,
        "attempted": False,
        "recovered": rollup_ok,
        "actions": [],
        "reason": "",
    }

    if rollup_ok:
        report["reason"] = "rollup_ok"
        _write_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[summary] attempted=false reason=rollup_ok")
        return 0

    if fail_streak < threshold:
        report["reason"] = "below_threshold"
        _write_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[summary] attempted=false reason=below_threshold")
        return 0

    if not cooldown_ok:
        report["reason"] = "cooldown_active"
        _write_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[summary] attempted=false reason=cooldown_active")
        return 0

    report["attempted"] = True
    report["reason"] = "threshold_reached"

    sequence = [
        [
            sys.executable,
            "scripts/optimize_wp_kr.py",
            "--apply",
            "--description",
            str(args.wp_description),
            "--report",
            "logs/wp_site_guard_latest.json",
        ],
        [
            sys.executable,
            "scripts/rankmath_detail_optimizer.py",
            "--report",
            "logs/rankmath_detail_opt_latest.json",
        ],
        [
            sys.executable,
            "scripts/site_cx_probe.py",
            "--report",
            "logs/site_cx_probe_latest.json",
        ],
        [
            sys.executable,
            "scripts/site_cx_autoheal.py",
            "--force",
            "--probe-report",
            "logs/site_cx_probe_latest.json",
            "--summary-report",
            "logs/site_cx_autoheal_latest.json",
            "--apply-report",
            "logs/co_global_banner_apply_latest.json",
        ],
        [
            sys.executable,
            "scripts/site_dom_snapshot.py",
            "--report",
            "logs/site_dom_snapshot_latest.json",
        ],
        [
            sys.executable,
            "scripts/site_cx_health_rollup.py",
            "--latest-report",
            "logs/site_cx_health_rollup_latest.json",
            "--history",
            "logs/site_cx_health_history.jsonl",
            "--alert-on-change",
            "--alert-state",
            "logs/site_cx_health_alert_state.json",
            "--alert-repeat-min",
            "120",
        ],
    ]

    for cmd in sequence:
        row = _run(cmd)
        report["actions"].append(row)

    refreshed_rollup = _read_json(rollup_path)
    recovered = bool(refreshed_rollup.get("ok", False))
    report["recovered"] = recovered
    report["post_rollup_ok"] = recovered

    alert_event = "site_cx_force_recovered" if recovered else "site_cx_force_failed"
    alert_sev = "info" if recovered else "critical"
    alert_msg = (
        f"site force recover attempted streak={fail_streak} "
        f"threshold={threshold} recovered={recovered}"
    )
    alert_cmd = [
        sys.executable,
        "scripts/site_ops_alert.py",
        "--event",
        alert_event,
        "--severity",
        alert_sev,
        "--message",
        alert_msg,
        "--detail-file",
        str(report_path),
    ]
    report["actions"].append(_run(alert_cmd))

    new_state = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_attempt_epoch": now_epoch,
        "last_attempt_ok": recovered,
        "last_attempt_streak": fail_streak,
    }
    _write_json(state_path, new_state)
    _write_json(report_path, report)
    print(f"[saved] {report_path}")
    print(
        "[summary] "
        + f"attempted={report['attempted']} "
        + f"recovered={recovered} "
        + f"streak={fail_streak}"
    )
    return 0 if recovered else 2


if __name__ == "__main__":
    raise SystemExit(main())
