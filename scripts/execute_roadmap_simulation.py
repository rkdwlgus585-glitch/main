import argparse
import json
import locale
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _tail(text: str, max_lines: int = 40) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return text or ""
    return "\n".join(lines[-max_lines:])


def _py_cmd(args: List[str]) -> List[str]:
    if shutil.which("py"):
        return ["py", "-3", *args]
    return [sys.executable, *args]


def _decode_best(data: bytes, preferred_encoding: str) -> str:
    if not data:
        return ""
    candidates = []
    seen = set()
    for enc in (preferred_encoding, "utf-8", "utf-8-sig", "cp949", "euc-kr"):
        key = (enc or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append(enc)

    best_text = ""
    best_score = None
    for enc in candidates:
        try:
            text = data.decode(enc, errors="replace")
        except LookupError:
            continue
        score = text.count("\ufffd")
        if best_score is None or score < best_score:
            best_text = text
            best_score = score
            if score == 0:
                break
    return best_text


def _run(
    name: str,
    cmd: List[str],
    timeout_sec: int,
    cwd: Path = ROOT,
) -> Dict[str, Any]:
    start = time.time()
    cmd_text = " ".join(shlex.quote(part) for part in cmd)
    preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=False,
            capture_output=True,
            timeout=timeout_sec,
        )
        stdout_text = _decode_best(proc.stdout or b"", preferred_encoding)
        stderr_text = _decode_best(proc.stderr or b"", preferred_encoding)
        duration = round(time.time() - start, 2)
        return {
            "name": name,
            "command": cmd_text,
            "returncode": proc.returncode,
            "duration_sec": duration,
            "ok": proc.returncode == 0,
            "stdout_tail": _tail(stdout_text),
            "stderr_tail": _tail(stderr_text),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        duration = round(time.time() - start, 2)
        out = exc.stdout or b""
        err = exc.stderr or b""
        if isinstance(out, str):
            out_text = out
        else:
            out_text = _decode_best(out, preferred_encoding)
        if isinstance(err, str):
            err_text = err
        else:
            err_text = _decode_best(err, preferred_encoding)
        return {
            "name": name,
            "command": cmd_text,
            "returncode": 124,
            "duration_sec": duration,
            "ok": False,
            "stdout_tail": _tail(out_text),
            "stderr_tail": _tail(err_text),
            "timed_out": True,
        }


def _parse_env(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    raw = path.read_text(encoding="utf-8", errors="replace")
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.lower().startswith("export "):
            s = s[7:].strip()
        if "=" not in s:
            continue
        key, value = s.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        data[key] = value
    return data


def _check_file(path: Path, required: bool = True) -> Dict[str, Any]:
    exists = path.exists()
    return {
        "name": f"file:{path.relative_to(ROOT).as_posix()}",
        "required": required,
        "ok": exists if required else True,
        "exists": exists,
    }


def _scan_startup_legacy_artifacts() -> Dict[str, Any]:
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    artifacts: List[str] = []
    if startup.exists():
        for entry in startup.iterdir():
            name = entry.name
            if (
                re.search(r"\.bak_\d{8}", name)
                or re.search(r"\.disabled_\d{8}", name)
                or re.search(r"^MNAKR_AutoScheduler\.cmd(\..+)?$", name)
                or re.search(r"^SeoulMNA_.*\.vbs(\..+)?$", name)
            ):
                artifacts.append(name)
    return {
        "name": "startup:legacy_artifacts_absent",
        "required": True,
        "ok": len(artifacts) == 0,
        "count": len(artifacts),
        "startup_path": str(startup),
        "artifacts": artifacts,
    }


def _query_task(task_name: str) -> Dict[str, Any]:
    row = _run(
        name=f"schtasks:{task_name}",
        cmd=["schtasks", "/Query", "/TN", task_name, "/V", "/FO", "LIST"],
        timeout_sec=20,
        cwd=ROOT,
    )
    parsed: Dict[str, str] = {}
    if row["ok"]:
        for line in (row.get("stdout_tail") or "").splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            parsed[key.strip()] = value.strip()
    return {
        "name": task_name,
        "ok": row["ok"],
        "scheduled_task_state": parsed.get("Scheduled Task State", ""),
        "status": parsed.get("Status", ""),
        "last_result": parsed.get("Last Result", ""),
        "task_to_run": parsed.get("Task To Run", ""),
        "raw_returncode": row["returncode"],
        "raw_stderr_tail": row.get("stderr_tail", ""),
    }


def _env_checks(env_data: Dict[str, str]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    required_listing = ["SITE_URL", "MNA_BOARD_SLUG"]
    for key in required_listing:
        checks.append(
            {
                "name": f"env:{key}",
                "required": True,
                "ok": bool(env_data.get(key)),
                "present": bool(env_data.get(key)),
            }
        )

    json_file_value = env_data.get("JSON_FILE", "service_account.json")
    sheet_name_value = env_data.get("SHEET_NAME", "<all.py-default>")
    checks.append(
        {
            "name": "env:JSON_FILE(default=service_account.json)",
            "required": True,
            "ok": bool(json_file_value),
            "present": bool(env_data.get("JSON_FILE")),
            "effective_value": json_file_value,
        }
    )
    checks.append(
        {
            "name": "env:SHEET_NAME(optional)",
            "required": True,
            "ok": bool(sheet_name_value),
            "present": bool(env_data.get("SHEET_NAME")),
            "effective_value": sheet_name_value,
        }
    )

    checks.append(
        {
            "name": "env:ADMIN_ID_ADMIN_PW",
            "required": True,
            "ok": bool(env_data.get("ADMIN_ID")) and bool(env_data.get("ADMIN_PW")),
            "present": {
                "ADMIN_ID": bool(env_data.get("ADMIN_ID")),
                "ADMIN_PW": bool(env_data.get("ADMIN_PW")),
            },
        }
    )

    has_wp_jwt = bool(env_data.get("WP_JWT_TOKEN"))
    has_wp_user_app = bool(env_data.get("WP_USER")) and bool(env_data.get("WP_APP_PASSWORD"))
    has_wp_user_pw = bool(env_data.get("WP_USER")) and bool(env_data.get("WP_PASSWORD"))
    checks.append(
        {
            "name": "env:WORDPRESS_AUTH",
            "required": True,
            "ok": has_wp_jwt or has_wp_user_app or has_wp_user_pw,
            "present": {
                "WP_JWT_TOKEN": has_wp_jwt,
                "WP_USER+WP_APP_PASSWORD": has_wp_user_app,
                "WP_USER+WP_PASSWORD": has_wp_user_pw,
            },
        }
    )

    checks.append(
        {
            "name": "env:GEMINI_API_KEY",
            "required": True,
            "ok": bool(env_data.get("GEMINI_API_KEY")),
            "present": bool(env_data.get("GEMINI_API_KEY")),
        }
    )
    return checks


def _scan_warnings(step: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    text = (step.get("stdout_tail") or "") + "\n" + (step.get("stderr_tail") or "")
    if "??" in text:
        warnings.append("output_contains_error_marker")
    if re.search(r"\bfailed\b", text, flags=re.IGNORECASE):
        warnings.append("output_contains_failed")
    if re.search(r"\btimeout\b", text, flags=re.IGNORECASE):
        warnings.append("output_contains_timeout")
    return warnings


def _build_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Roadmap Simulation Report")
    lines.append("")
    lines.append(f"- generated_at: `{report['generated_at']}`")
    lines.append(f"- workspace: `{report['workspace']}`")
    lines.append(f"- overall_ok: `{report['ok']}`")
    lines.append("")

    lines.append("## Preflight")
    for row in report["preflight"]:
        lines.append(f"- `{row['name']}`: {'OK' if row.get('ok') else 'FAIL'}")
    lines.append("")

    lines.append("## Task Scheduler")
    for row in report["scheduled_tasks"]:
        lines.append(
            f"- `{row['name']}`: {'OK' if row.get('ok') else 'MISSING/ERROR'} | state=`{row.get('scheduled_task_state','')}` | status=`{row.get('status','')}` | last_result=`{row.get('last_result','')}`"
        )
    lines.append("")

    lines.append("## Simulations")
    for row in report["simulations"]:
        warn_text = ""
        if row.get("warnings"):
            warn_text = " | warnings=" + ",".join(row["warnings"])
        lines.append(
            f"- `{row['name']}`: {'OK' if row.get('ok') else 'FAIL'} | rc={row.get('returncode')} | {row.get('duration_sec')}s{warn_text}"
        )
    lines.append("")

    if report.get("blocking_issues"):
        lines.append("## Blocking Issues")
        for item in report["blocking_issues"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Active Window Policy")
    lines.append("- Weekday: `09:00~23:00`")
    lines.append("- Weekend: `14:00~23:00`")
    lines.append("- now-to-sheet sync slots: `12:00`, `18:00`")
    lines.append("")

    return "\n".join(lines) + "\n"


def build_report(skip_network: bool, timeout_sec: int) -> Dict[str, Any]:
    preflight: List[Dict[str, Any]] = []
    env_data = _parse_env(ROOT / ".env")

    preflight.extend(
        [
            _check_file(ROOT / "all.py"),
            _check_file(ROOT / "mnakr.py"),
            _check_file(ROOT / "tistory_ops" / "run.py"),
            _check_file(ROOT / "service_account.json"),
            _check_file(ROOT / ".env"),
        ]
    )
    preflight.append(_scan_startup_legacy_artifacts())
    preflight.extend(_env_checks(env_data))

    scheduled_tasks = [
        _query_task("SeoulMNA_CoKr_Listing_Watchdog"),
        _query_task("SeoulMNA_CoKr_Notice_Watchdog"),
        _query_task("SeoulMNA_CoKr_AdminMemo_Watchdog"),
        _query_task("SeoulMNA_CoKr_SiteHealth_Watchdog"),
        _query_task("SeoulMNA_Permit_Data_Watchdog"),
        _query_task("SeoulMNA_MnakrScheduler_Watchdog"),
        _query_task("SeoulMNA_Blog_StartupOnce"),
        _query_task("SeoulMNA_Tistory_DailyOnce"),
        _query_task("SeoulMNA_All_Startup"),
    ]

    simulations: List[Dict[str, Any]] = []
    sim_cmds: List[Tuple[str, List[str], int]] = [
        ("entrypoints_strict", _py_cmd(["scripts/show_entrypoints.py", "--strict"]), timeout_sec),
        (
            "tistory_verify_split",
            _py_cmd(
                [
                    "tistory_ops/run.py",
                    "verify-split",
                    "--out",
                    "logs/tistory_split_verify_latest.json",
                ]
            ),
            timeout_sec,
        ),
    ]
    if not skip_network:
        sim_cmds.extend(
            [
                ("mnakr_schedule_check", _py_cmd(["mnakr.py", "--schedule-check"]), timeout_sec),
                ("mnakr_wp_check", _py_cmd(["mnakr.py", "--wp-check"]), timeout_sec),
                (
                    "all_admin_memo_plan_only",
                    _py_cmd(
                        [
                            "all.py",
                            "--fix-admin-memo",
                            "--fix-admin-memo-plan-only",
                            "--fix-admin-memo-pages",
                            "1",
                            "--fix-admin-memo-limit",
                            "20",
                        ]
                    ),
                    timeout_sec,
                ),
                (
                    "all_reconcile_dry_run_sample",
                    _py_cmd(
                        [
                            "all.py",
                            "--reconcile-published",
                            "--reconcile-dry-run",
                            "--reconcile-nowmna-pages",
                            "1",
                            "--reconcile-seoul-pages",
                            "1",
                            "--reconcile-max-updates",
                            "5",
                            "--reconcile-audit-tag",
                            "roadmap_sim",
                        ]
                    ),
                    max(timeout_sec, 180),
                ),
            ]
        )

    for name, cmd, sec in sim_cmds:
        row = _run(name=name, cmd=cmd, timeout_sec=sec)
        row["warnings"] = _scan_warnings(row)
        simulations.append(row)

    blocking_issues: List[str] = []
    for row in preflight:
        if row.get("required") and not row.get("ok"):
            blocking_issues.append(f"preflight_failed:{row['name']}")
    for row in simulations:
        if not row.get("ok"):
            blocking_issues.append(f"simulation_failed:{row['name']}")

    ok = len(blocking_issues) == 0

    return {
        "generated_at": _now_iso(),
        "workspace": str(ROOT),
        "ok": ok,
        "skip_network": skip_network,
        "preflight": preflight,
        "scheduled_tasks": scheduled_tasks,
        "simulations": simulations,
        "blocking_issues": blocking_issues,
        "policy": {
            "weekday_active_window": "09:00-23:00",
            "weekend_active_window": "14:00-23:00",
            "now_to_sheet_slots": ["12:00", "18:00"],
            "startup_delay_recommended_sec": {
                "ops_watchdog": 0,
                "mnakr_scheduler_watchdog": 60,
                "blog_startup_once": 180,
                "tistory_daily_once": 360,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run preflight checks and safe simulations for SeoulMNA execution roadmap."
    )
    parser.add_argument(
        "--out",
        default="logs/roadmap_simulation_latest.json",
        help="Output JSON path (default: logs/roadmap_simulation_latest.json)",
    )
    parser.add_argument(
        "--md-out",
        default="logs/roadmap_simulation_latest.md",
        help="Output Markdown path (default: logs/roadmap_simulation_latest.md)",
    )
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip network-reliant simulation commands (wp-check, reconcile dry-run).",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=90,
        help="Base timeout for each command (seconds).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any required preflight or simulation fails.",
    )
    args = parser.parse_args()

    report = build_report(skip_network=args.skip_network, timeout_sec=max(30, args.timeout_sec))

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = (ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = (ROOT / args.md_out).resolve()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_build_markdown(report), encoding="utf-8")

    print(f"[saved] {out_path}")
    print(f"[saved] {md_path}")
    print(f"[overall_ok] {report['ok']}")
    if report["blocking_issues"]:
        for issue in report["blocking_issues"]:
            print(f"- {issue}")

    if args.strict and not report["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
