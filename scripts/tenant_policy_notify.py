#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import Notifier, load_config, setup_logger


CONFIG = load_config(
    {
        "TENANT_POLICY_ACTIONS_FILE": "logs/tenant_policy_actions_latest.json",
        "TENANT_POLICY_NOTIFY_REPORT_FILE": "logs/tenant_policy_notify_latest.json",
        "TENANT_POLICY_NOTIFY_SEND_ON_OK": "false",
        "TENANT_POLICY_NOTIFY_TITLE": "Tenant Policy Alert",
    }
)

logger = setup_logger(name="tenant_policy_notify")


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


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_message(payload: Dict[str, object]) -> Tuple[str, Dict[str, int]]:
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    actions = payload.get("actions") if isinstance(payload, dict) else []
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(actions, list):
        actions = []

    action_count = int(summary.get("action_count") or 0)
    unresolved = int(summary.get("unresolved_action_count") or 0)
    high = int(summary.get("high_severity_count") or 0)
    warning = int(summary.get("warning_count") or 0)
    applied = int(summary.get("applied_change_count") or 0)

    lines: List[str] = [
        "[Tenant Policy]",
        f"- action_count: {action_count}",
        f"- unresolved_action_count: {unresolved}",
        f"- high_severity_count: {high}",
        f"- warning_count: {warning}",
        f"- applied_change_count: {applied}",
    ]

    top = []
    for row in actions:
        if not isinstance(row, dict):
            continue
        tenant_id = str(row.get("tenant_id") or "").strip() or "unknown"
        policy_action = str(row.get("policy_action") or "").strip() or "notify"
        rec = str(row.get("recommended_action") or "").strip() or "unknown"
        msg = str(row.get("message") or "").strip()
        top.append(f"{tenant_id}: {policy_action} ({rec}) {msg}".strip())
        if len(top) >= 5:
            break

    if top:
        lines.append("- top_actions:")
        lines.extend([f"  {item}" for item in top])

    return "\n".join(lines), {
        "action_count": action_count,
        "unresolved_action_count": unresolved,
        "high_severity_count": high,
        "warning_count": warning,
        "applied_change_count": applied,
    }


def run(
    *,
    policy_path: Path,
    report_path: Path,
    title: str,
    send_on_ok: bool,
    dry_run: bool,
    strict: bool,
) -> int:
    if not policy_path.exists():
        raise FileNotFoundError(f"policy report not found: {policy_path}")

    payload = _load_json(policy_path)
    message, stats = _build_message(payload)

    should_send = bool(send_on_ok) or int(stats["action_count"]) > 0 or int(stats["unresolved_action_count"]) > 0
    sent = False
    notification_ok = False

    if should_send:
        if dry_run:
            notification_ok = True
        else:
            notifier = Notifier(
                discord_url=str(CONFIG.get("DISCORD_WEBHOOK_URL", "")).strip(),
                slack_url=str(CONFIG.get("SLACK_WEBHOOK_URL", "")).strip(),
            )
            notification_ok = bool(notifier.send(message, title=title))
            sent = bool(notification_ok)
    else:
        notification_ok = True

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": bool(notification_ok),
        "should_send": bool(should_send),
        "sent": bool(sent),
        "dry_run": bool(dry_run),
        "title": str(title or ""),
        "stats": stats,
        "message": message,
        "policy_report": str(policy_path),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": result["ok"], "report": str(report_path), "should_send": should_send, "sent": sent}, ensure_ascii=False))

    if strict and int(stats["unresolved_action_count"]) > 0 and not bool(notification_ok):
        logger.error("strict mode: unresolved actions exist and notification failed")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify tenant policy actions to Discord/Slack")
    parser.add_argument("--policy-report", default=str(CONFIG.get("TENANT_POLICY_ACTIONS_FILE", "logs/tenant_policy_actions_latest.json")))
    parser.add_argument("--report", default=str(CONFIG.get("TENANT_POLICY_NOTIFY_REPORT_FILE", "logs/tenant_policy_notify_latest.json")))
    parser.add_argument("--title", default=str(CONFIG.get("TENANT_POLICY_NOTIFY_TITLE", "Tenant Policy Alert")))
    parser.add_argument("--send-on-ok", action="store_true", default=False)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--strict", action="store_true", default=False)
    args = parser.parse_args()

    send_on_ok = bool(args.send_on_ok) or _to_bool(CONFIG.get("TENANT_POLICY_NOTIFY_SEND_ON_OK", "false"), False)
    return run(
        policy_path=Path(str(args.policy_report)).resolve(),
        report_path=Path(str(args.report)).resolve(),
        title=str(args.title or "Tenant Policy Alert"),
        send_on_ok=bool(send_on_ok),
        dry_run=bool(args.dry_run),
        strict=bool(args.strict),
    )


if __name__ == "__main__":
    raise SystemExit(main())
