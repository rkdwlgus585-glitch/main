#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_FOUNDER = ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"
DEFAULT_FOCUS = ROOT / "logs" / "next_batch_focus_packet_latest.json"
DEFAULT_EXECUTION = ROOT / "logs" / "next_execution_packet_latest.json"
DEFAULT_CHAIN = ROOT / "logs" / "founder_execution_chain_latest.json"
DEFAULT_PERMIT_THINKING = ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.json"
DEFAULT_JSON = ROOT / "logs" / "founder_selection_consistency_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "founder_selection_consistency_audit_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _issue(code: str, detail: str) -> Dict[str, str]:
    return {"code": code, "detail": detail}


def build_payload(*, operations_path: Path, founder_path: Path, focus_path: Path, execution_path: Path, chain_path: Path, permit_thinking_path: Path) -> Dict[str, Any]:
    operations = _load_json(operations_path)
    founder = _load_json(founder_path)
    focus = _load_json(focus_path)
    execution = _load_json(execution_path)
    chain = _load_json(chain_path)
    permit_thinking = _load_json(permit_thinking_path)

    decisions = _safe_dict(operations.get("decisions"))
    founder_summary = _safe_dict(founder.get("summary"))
    focus_summary = _safe_dict(focus.get("summary"))
    execution_summary = _safe_dict(execution.get("summary"))
    chain_summary = _safe_dict(chain.get("summary"))
    permit_thinking_summary = _safe_dict(permit_thinking.get("summary"))

    founder_primary_system = _safe_str(founder_summary.get("primary_system"))
    founder_primary_lane_id = _safe_str(founder_summary.get("primary_lane_id"))
    focus_track = _safe_str(focus_summary.get("selected_track"))
    focus_lane = _safe_str(focus_summary.get("selected_lane_id"))
    execution_track = _safe_str(execution_summary.get("selected_track"))
    execution_lane = _safe_str(execution_summary.get("selected_lane_id"))
    selection_policy = _safe_str(focus_summary.get("selection_policy"))

    issues: List[Dict[str, str]] = []

    focus_matches_execution = bool(focus_track and focus_lane and focus_track == execution_track and focus_lane == execution_lane)
    focus_matches_founder = bool(focus_track and focus_track == founder_primary_system and focus_lane == founder_primary_lane_id)
    founder_primary_ready = bool(focus_summary.get("founder_primary_ready"))
    selected_matches_founder = bool(focus_summary.get("selected_matches_founder"))
    chain_matches = bool(chain_summary.get("focus_matches_execution"))

    if focus_matches_execution != chain_matches:
        issues.append(_issue("chain_focus_execution_mismatch", "next_batch_focus and founder_execution_chain disagree on focus/execution convergence."))

    if focus_matches_founder != selected_matches_founder:
        issues.append(_issue("founder_selection_flag_mismatch", "selected_matches_founder does not match the actual selected track/lane."))

    if selection_policy == "founder_primary_ready_now" and not founder_primary_ready:
        issues.append(_issue("selection_policy_ready_mismatch", "selection_policy claims founder primary is ready, but founder_primary_ready is false."))

    if founder_primary_system == "permit" and founder_primary_lane_id == "thinking_prompt_bundle_lock":
        expected_ready = bool(decisions.get("permit_thinking_prompt_bundle_ready")) and bool(permit_thinking_summary.get("packet_ready"))
        if founder_primary_ready != expected_ready:
            issues.append(_issue("permit_thinking_ready_mismatch", "founder_primary_ready does not match permit_thinking_prompt_bundle readiness."))

    if bool(decisions.get("next_execution_ready")) and not focus_matches_execution:
        issues.append(_issue("next_execution_without_focus_convergence", "operations say next execution is ready, but focus and execution lane do not converge."))

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "audit_ok": not issues,
            "issue_count": len(issues),
            "founder_primary_system": founder_primary_system,
            "founder_primary_lane_id": founder_primary_lane_id,
            "focus_track": focus_track,
            "focus_lane_id": focus_lane,
            "execution_track": execution_track,
            "execution_lane_id": execution_lane,
            "founder_primary_ready": founder_primary_ready,
            "selected_matches_founder": selected_matches_founder,
            "focus_matches_execution": focus_matches_execution,
            "selection_policy": selection_policy,
        },
        "issues": issues,
        "artifacts": {
            "operations": str(operations_path.resolve()),
            "founder": str(founder_path.resolve()),
            "focus": str(focus_path.resolve()),
            "execution": str(execution_path.resolve()),
            "chain": str(chain_path.resolve()),
            "permit_thinking": str(permit_thinking_path.resolve()),
        },
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    lines = [
        "# Founder Selection Consistency Audit",
        "",
        f"- audit_ok: `{summary.get('audit_ok')}`",
        f"- issue_count: `{summary.get('issue_count')}`",
        f"- founder_primary: `{summary.get('founder_primary_system')}/{summary.get('founder_primary_lane_id')}`",
        f"- focus_selected: `{summary.get('focus_track')}/{summary.get('focus_lane_id')}`",
        f"- execution_selected: `{summary.get('execution_track')}/{summary.get('execution_lane_id')}`",
        f"- founder_primary_ready: `{summary.get('founder_primary_ready')}`",
        f"- selected_matches_founder: `{summary.get('selected_matches_founder')}`",
        f"- focus_matches_execution: `{summary.get('focus_matches_execution')}`",
        f"- selection_policy: `{summary.get('selection_policy')}`",
        "",
        "## Issues",
    ]
    for item in payload.get("issues") or []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('code')}`: {item.get('detail')}")
    if not payload.get("issues"):
        lines.append("- none")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit founder/next-focus/next-execution consistency.")
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--founder", type=Path, default=DEFAULT_FOUNDER)
    parser.add_argument("--focus", type=Path, default=DEFAULT_FOCUS)
    parser.add_argument("--execution", type=Path, default=DEFAULT_EXECUTION)
    parser.add_argument("--chain", type=Path, default=DEFAULT_CHAIN)
    parser.add_argument("--permit-thinking", type=Path, default=DEFAULT_PERMIT_THINKING)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_payload(
        operations_path=args.operations,
        founder_path=args.founder,
        focus_path=args.focus,
        execution_path=args.execution,
        chain_path=args.chain,
        permit_thinking_path=args.permit_thinking,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "audit_ok": _safe_dict(payload.get("summary")).get("audit_ok"), "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0 if bool(_safe_dict(payload.get("summary")).get("audit_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
