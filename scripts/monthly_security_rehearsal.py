#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import Notifier, load_config


CONFIG = load_config(
    {
        "MONTHLY_REHEARSAL_NOTIFY_ENABLED": "true",
        "MONTHLY_REHEARSAL_NOTIFY_SEND_ON_OK": "false",
        "MONTHLY_REHEARSAL_NOTIFY_TITLE": "Monthly Security Rehearsal",
        "MONTHLY_REHEARSAL_NOTIFY_REPORT_FILE": "logs/monthly_security_rehearsal_notify_latest.json",
        "MONTHLY_REHEARSAL_TICKET_MD_FILE": "logs/monthly_security_rehearsal_ticket_latest.md",
        "MONTHLY_REHEARSAL_API_SEND_ON_OK": "false",
        "MONTHLY_REHEARSAL_TICKET_API_ENABLED": "false",
        "MONTHLY_REHEARSAL_TICKET_API_URL": "",
        "MONTHLY_REHEARSAL_TICKET_API_TOKEN": "",
        "MONTHLY_REHEARSAL_CALENDAR_API_ENABLED": "false",
        "MONTHLY_REHEARSAL_CALENDAR_API_URL": "",
        "MONTHLY_REHEARSAL_CALENDAR_API_TOKEN": "",
    }
)

LATEST_REPORT = ROOT / "logs" / "monthly_security_rehearsal_latest.json"
HISTORY_REPORT = ROOT / "logs" / "monthly_security_rehearsal_history.jsonl"
NOTIFY_REPORT = ROOT / str(CONFIG.get("MONTHLY_REHEARSAL_NOTIFY_REPORT_FILE", "logs/monthly_security_rehearsal_notify_latest.json"))
TICKET_MD = ROOT / str(CONFIG.get("MONTHLY_REHEARSAL_TICKET_MD_FILE", "logs/monthly_security_rehearsal_ticket_latest.md"))


def _to_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _py_cmd(args: List[str]) -> List[str]:
    launcher = "py" if sys.platform.startswith("win") else sys.executable
    if launcher == "py":
        return ["py", "-3"] + args
    return [launcher] + args


def _run(name: str, cmd: List[str], timeout: int = 180) -> Dict[str, Any]:
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=max(30, int(timeout)),
            check=False,
        )
        return {
            "name": name,
            "ok": proc.returncode == 0,
            "returncode": int(proc.returncode),
            "started_at": started,
            "stdout": (proc.stdout or "").strip()[-4000:],
            "stderr": (proc.stderr or "").strip()[-4000:],
            "command": cmd,
        }
    except Exception as e:
        return {
            "name": name,
            "ok": False,
            "returncode": -1,
            "started_at": started,
            "stdout": "",
            "stderr": str(e),
            "command": cmd,
        }


def _build_publish_content(payload: Dict[str, object]) -> Tuple[str, str, Dict[str, int]]:
    steps = payload.get("steps") if isinstance(payload, dict) else []
    if not isinstance(steps, list):
        steps = []

    total = len(steps)
    failed = [s for s in steps if isinstance(s, dict) and not bool(s.get("ok"))]
    fail_count = len(failed)
    success_count = total - fail_count

    lines = [
        "[Monthly Security Rehearsal]",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- overall_ok: {bool(payload.get('ok'))}",
        f"- step_count: {total}",
        f"- success_count: {success_count}",
        f"- fail_count: {fail_count}",
    ]
    for row in failed[:5]:
        lines.append(
            f"  - fail: {row.get('name')} rc={row.get('returncode')} err={str(row.get('stderr', '') or '')[:120]}"
        )
    message = "\n".join(lines)

    md_lines = [
        f"# Monthly Security Rehearsal ({payload.get('generated_at', '')})",
        "",
        f"- overall_ok: `{bool(payload.get('ok'))}`",
        f"- step_count: `{total}`",
        f"- success_count: `{success_count}`",
        f"- fail_count: `{fail_count}`",
        "",
        "## Steps",
        "| step | ok | rc |",
        "|---|---:|---:|",
    ]
    for step in steps:
        if not isinstance(step, dict):
            continue
        md_lines.append(f"| {step.get('name', '')} | {bool(step.get('ok'))} | {int(step.get('returncode') or 0)} |")

    if failed:
        md_lines.append("")
        md_lines.append("## Failures")
        for row in failed:
            md_lines.append(f"- `{row.get('name')}`: {str(row.get('stderr', '') or '')[:500]}")

    stats = {
        "step_count": total,
        "success_count": success_count,
        "fail_count": fail_count,
    }
    return message, "\n".join(md_lines), stats


def _post_json(url: str, payload: Dict[str, object], token: str = "", timeout: int = 10) -> Dict[str, object]:
    target = str(url or "").strip()
    if not target:
        return {"ok": False, "status": 0, "reason": "missing_url"}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(target, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if str(token or "").strip():
        req.add_header("Authorization", f"Bearer {str(token).strip()}")

    try:
        with urllib.request.urlopen(req, timeout=max(3, int(timeout))) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            return {"ok": 200 <= status < 300, "status": status, "reason": "sent"}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": int(e.code or 0), "reason": f"http_error:{e.code}"}
    except Exception as e:
        return {"ok": False, "status": 0, "reason": f"request_error:{e}"}


def _publish(payload: Dict[str, object], *, dry_run_notify: bool) -> Dict[str, object]:
    message, ticket_md, stats = _build_publish_content(payload)

    TICKET_MD.parent.mkdir(parents=True, exist_ok=True)
    TICKET_MD.write_text(ticket_md, encoding="utf-8")

    notify_enabled = _to_bool(CONFIG.get("MONTHLY_REHEARSAL_NOTIFY_ENABLED", "true"), True)
    send_on_ok = _to_bool(CONFIG.get("MONTHLY_REHEARSAL_NOTIFY_SEND_ON_OK", "false"), False)
    should_send = bool(notify_enabled) and (bool(send_on_ok) or not bool(payload.get("ok")))

    sent = False
    notify_ok = True
    reason = "send_condition_not_met"

    discord_url = str(CONFIG.get("DISCORD_WEBHOOK_URL", "")).strip()
    slack_url = str(CONFIG.get("SLACK_WEBHOOK_URL", "")).strip()

    if should_send:
        if dry_run_notify:
            reason = "dry_run_notify"
            notify_ok = True
        elif not discord_url and not slack_url:
            reason = "no_webhook_configured"
            notify_ok = True
        else:
            notifier = Notifier(discord_url=discord_url, slack_url=slack_url)
            sent = bool(notifier.send(message, title=str(CONFIG.get("MONTHLY_REHEARSAL_NOTIFY_TITLE", "Monthly Security Rehearsal"))))
            notify_ok = bool(sent)
            reason = "sent" if sent else "send_failed"

    api_send_on_ok = _to_bool(CONFIG.get("MONTHLY_REHEARSAL_API_SEND_ON_OK", "false"), False)
    should_send_api = bool(api_send_on_ok) or not bool(payload.get("ok"))

    ticket_api_enabled = _to_bool(CONFIG.get("MONTHLY_REHEARSAL_TICKET_API_ENABLED", "false"), False)
    ticket_api_url = str(CONFIG.get("MONTHLY_REHEARSAL_TICKET_API_URL", "")).strip()
    ticket_api_token = str(CONFIG.get("MONTHLY_REHEARSAL_TICKET_API_TOKEN", "")).strip()

    calendar_api_enabled = _to_bool(CONFIG.get("MONTHLY_REHEARSAL_CALENDAR_API_ENABLED", "false"), False)
    calendar_api_url = str(CONFIG.get("MONTHLY_REHEARSAL_CALENDAR_API_URL", "")).strip()
    calendar_api_token = str(CONFIG.get("MONTHLY_REHEARSAL_CALENDAR_API_TOKEN", "")).strip()

    ticket_api_result: Dict[str, object] = {"enabled": bool(ticket_api_enabled), "attempted": False, "ok": True, "reason": "disabled"}
    calendar_api_result: Dict[str, object] = {"enabled": bool(calendar_api_enabled), "attempted": False, "ok": True, "reason": "disabled"}

    if ticket_api_enabled:
        if should_send_api:
            payload_ticket = {
                "title": str(CONFIG.get("MONTHLY_REHEARSAL_NOTIFY_TITLE", "Monthly Security Rehearsal")),
                "generated_at": str(payload.get("generated_at") or ""),
                "overall_ok": bool(payload.get("ok")),
                "stats": stats,
                "ticket_markdown": ticket_md,
                "source_report": str(LATEST_REPORT),
            }
            if dry_run_notify:
                ticket_api_result = {
                    "enabled": True,
                    "attempted": False,
                    "ok": True,
                    "reason": "dry_run_notify",
                }
            elif not ticket_api_url:
                ticket_api_result = {
                    "enabled": True,
                    "attempted": False,
                    "ok": False,
                    "reason": "missing_ticket_api_url",
                }
            else:
                res = _post_json(ticket_api_url, payload_ticket, token=ticket_api_token, timeout=10)
                ticket_api_result = {
                    "enabled": True,
                    "attempted": True,
                    "ok": bool(res.get("ok")),
                    "reason": str(res.get("reason") or ""),
                    "status": int(res.get("status") or 0),
                }
        else:
            ticket_api_result = {
                "enabled": True,
                "attempted": False,
                "ok": True,
                "reason": "send_condition_not_met",
            }

    if calendar_api_enabled:
        if should_send_api:
            payload_calendar = {
                "title": str(CONFIG.get("MONTHLY_REHEARSAL_NOTIFY_TITLE", "Monthly Security Rehearsal")),
                "generated_at": str(payload.get("generated_at") or ""),
                "overall_ok": bool(payload.get("ok")),
                "stats": stats,
                "summary": message,
                "source_report": str(LATEST_REPORT),
            }
            if dry_run_notify:
                calendar_api_result = {
                    "enabled": True,
                    "attempted": False,
                    "ok": True,
                    "reason": "dry_run_notify",
                }
            elif not calendar_api_url:
                calendar_api_result = {
                    "enabled": True,
                    "attempted": False,
                    "ok": False,
                    "reason": "missing_calendar_api_url",
                }
            else:
                res = _post_json(calendar_api_url, payload_calendar, token=calendar_api_token, timeout=10)
                calendar_api_result = {
                    "enabled": True,
                    "attempted": True,
                    "ok": bool(res.get("ok")),
                    "reason": str(res.get("reason") or ""),
                    "status": int(res.get("status") or 0),
                }
        else:
            calendar_api_result = {
                "enabled": True,
                "attempted": False,
                "ok": True,
                "reason": "send_condition_not_met",
            }

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": bool(notify_ok) and bool(ticket_api_result.get("ok", True)) and bool(calendar_api_result.get("ok", True)),
        "should_send": bool(should_send),
        "sent": bool(sent),
        "reason": reason,
        "dry_run_notify": bool(dry_run_notify),
        "stats": stats,
        "ticket_md": str(TICKET_MD),
        "latest_report": str(LATEST_REPORT),
        "message": message,
        "api_send_on_ok": bool(api_send_on_ok),
        "should_send_api": bool(should_send_api),
        "ticket_api": ticket_api_result,
        "calendar_api": calendar_api_result,
    }

    NOTIFY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    NOTIFY_REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def run_rehearsal(*, dry_run_notify: bool = False) -> int:
    steps: List[Dict[str, Any]] = []
    steps.append(_run("tenant_onboarding_validation", _py_cmd(["scripts/validate_tenant_onboarding.py", "--strict"]), timeout=120))
    steps.append(_run("tenant_usage_billing_report", _py_cmd(["scripts/tenant_usage_billing_report.py", "--strict"]), timeout=120))
    steps.append(
        _run(
            "tenant_threshold_policy",
            _py_cmd(["scripts/enforce_tenant_threshold_policy.py", "--strict", "--apply-registry"]),
            timeout=120,
        )
    )
    steps.append(_run("tenant_policy_notify", _py_cmd(["scripts/tenant_policy_notify.py"]), timeout=120))
    steps.append(_run("security_watchdog_60m", _py_cmd(["scripts/security_event_watchdog.py", "--lookback-min", "60"]), timeout=120))
    steps.append(
        _run(
            "tenant_policy_recovery_preview",
            _py_cmd(["scripts/tenant_policy_recovery.py", "--all-disabled", "--with-blocked-keys"]),
            timeout=120,
        )
    )

    ok = all(bool(step.get("ok")) for step in steps)
    payload: Dict[str, object] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": bool(ok),
        "step_count": len(steps),
        "steps": steps,
    }

    LATEST_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LATEST_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with HISTORY_REPORT.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")

    publish = _publish(payload, dry_run_notify=bool(dry_run_notify))
    payload["publish"] = publish
    LATEST_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "report": str(LATEST_REPORT),
                "step_count": len(steps),
                "publish_should_send": publish.get("should_send"),
                "publish_sent": publish.get("sent"),
            },
            ensure_ascii=False,
        )
    )

    final_ok = bool(payload["ok"]) and bool(publish.get("ok", True))
    return 0 if final_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run monthly SeoulMNA security rehearsal")
    parser.add_argument("--dry-run-notify", action="store_true", default=False)
    args = parser.parse_args()
    return run_rehearsal(dry_run_notify=bool(args.dry_run_notify))


if __name__ == "__main__":
    raise SystemExit(main())
