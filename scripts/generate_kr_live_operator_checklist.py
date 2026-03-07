#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIVE_APPLY = ROOT / "logs" / "kr_live_apply_packet_latest.json"
DEFAULT_PROXY_MATRIX = ROOT / "logs" / "kr_proxy_server_matrix_latest.json"
DEFAULT_CUTOVER = ROOT / "logs" / "kr_reverse_proxy_cutover_latest.json"
DEFAULT_TRAFFIC_GATE = ROOT / "logs" / "kr_traffic_gate_audit_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_kr_live_operator_checklist(
    *,
    live_apply_path: Path,
    proxy_matrix_path: Path,
    cutover_path: Path,
    traffic_gate_path: Path,
) -> Dict[str, Any]:
    live_apply = _load_json(live_apply_path)
    proxy_matrix = _load_json(proxy_matrix_path)
    cutover = _load_json(cutover_path)
    traffic_gate = _load_json(traffic_gate_path)

    live_summary = live_apply.get("summary") if isinstance(live_apply.get("summary"), dict) else {}
    proxy_summary = proxy_matrix.get("summary") if isinstance(proxy_matrix.get("summary"), dict) else {}
    cutover_summary = cutover.get("summary") if isinstance(cutover.get("summary"), dict) else {}
    traffic_decision = traffic_gate.get("decision") if isinstance(traffic_gate.get("decision"), dict) else {}

    preflight = [
        {
            "step": 1,
            "key": "backup_current_wp",
            "label": "Current WordPress backup",
            "description": "Back up the live database, uploads, and Astra customization/export before any theme or page changes.",
        },
        {
            "step": 2,
            "key": "confirm_traffic_gate",
            "label": "Traffic gate check",
            "description": "Confirm homepage and knowledge pages still render without any calculator iframe before click.",
        },
        {
            "step": 3,
            "key": "prepare_reverse_proxy",
            "label": "Reverse proxy ready",
            "description": "Prepare the /_calc mount on the live server with cache bypass and hidden upstream origin.",
        },
        {
            "step": 4,
            "key": "confirm_live_yes",
            "label": "Final live confirmation",
            "description": "Only after the checklist is green, run the live release command with --confirm-live YES.",
        },
    ]

    validation = [
        {"step": index + 1, "description": item}
        for index, item in enumerate(live_apply.get("publish_validation") or [])
        if isinstance(item, str) and item.strip()
    ]

    rollback = []
    rollback_map = live_apply.get("rollback_map") if isinstance(live_apply.get("rollback_map"), dict) else {}
    for key, description in rollback_map.items():
        rollback.append({"key": key, "description": str(description)})

    checklist_ready = bool(live_summary.get("apply_packet_ready")) and bool(proxy_summary.get("cutover_ready")) and bool(cutover_summary.get("cutover_ready")) and bool(traffic_decision.get("traffic_leak_blocked"))
    blockers: List[str] = []
    if not bool(live_summary.get("apply_packet_ready")):
        blockers.append("live_apply_packet_not_ready")
    if not bool(proxy_summary.get("cutover_ready")):
        blockers.append("proxy_matrix_not_ready")
    if not bool(cutover_summary.get("cutover_ready")):
        blockers.append("reverse_proxy_cutover_not_ready")
    if not bool(traffic_decision.get("traffic_leak_blocked")):
        blockers.append("traffic_gate_not_ready")

    next_actions = (
        ["Use this checklist as the single operator sequence before running the live release command."]
        if checklist_ready
        else [
            "Resolve the checklist blockers before any live theme/plugin/page change.",
            "Do not run the live release command until the checklist is green.",
        ]
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "checklist_ready": checklist_ready,
            "platform_host": "seoulmna.kr",
            "listing_host": "seoulmna.co.kr",
            "public_mount_path": str(proxy_summary.get("public_mount_path") or ""),
            "preflight_item_count": len(preflight),
            "wordpress_step_count": len(live_apply.get("wordpress_steps") or []),
            "server_step_count": len(live_apply.get("server_steps") or []),
            "validation_step_count": len(validation),
            "rollback_item_count": len(rollback),
            "operator_input_count": len(live_apply.get("operator_inputs") or []),
            "blockers": blockers,
        },
        "preflight": preflight,
        "wordpress_steps": live_apply.get("wordpress_steps") or [],
        "server_steps": live_apply.get("server_steps") or [],
        "validation": validation,
        "rollback": rollback,
        "operator_inputs": live_apply.get("operator_inputs") or [],
        "next_actions": next_actions,
        "references": {
            "live_apply_packet": str(live_apply_path.resolve()),
            "proxy_matrix": str(proxy_matrix_path.resolve()),
            "cutover": str(cutover_path.resolve()),
            "traffic_gate": str(traffic_gate_path.resolve()),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# KR Live Operator Checklist",
        "",
        f"- checklist_ready: {summary.get('checklist_ready')}",
        f"- platform_host: {summary.get('platform_host') or '(none)'}",
        f"- listing_host: {summary.get('listing_host') or '(none)'}",
        f"- public_mount_path: {summary.get('public_mount_path') or '(none)'}",
        f"- blockers: {', '.join(summary.get('blockers') or []) or '(none)'}",
        "",
        "## Preflight",
    ]
    for row in payload.get("preflight", []):
        lines.append(f"- [{row.get('step')}] {row.get('label')}: {row.get('description')}")
    lines.extend(["", "## Validation"])
    for row in payload.get("validation", []):
        lines.append(f"- [{row.get('step')}] {row.get('description')}")
    lines.extend(["", "## Operator Inputs"])
    for item in payload.get("operator_inputs", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the operator-facing live checklist for the .kr WordPress platform cutover.")
    parser.add_argument("--live-apply", type=Path, default=DEFAULT_LIVE_APPLY)
    parser.add_argument("--proxy-matrix", type=Path, default=DEFAULT_PROXY_MATRIX)
    parser.add_argument("--cutover", type=Path, default=DEFAULT_CUTOVER)
    parser.add_argument("--traffic-gate", type=Path, default=DEFAULT_TRAFFIC_GATE)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "kr_live_operator_checklist_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "kr_live_operator_checklist_latest.md")
    args = parser.parse_args()

    payload = build_kr_live_operator_checklist(
        live_apply_path=args.live_apply,
        proxy_matrix_path=args.proxy_matrix,
        cutover_path=args.cutover,
        traffic_gate_path=args.traffic_gate,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
