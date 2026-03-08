#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "logs" / "founder_execution_chain_latest.json"
DEFAULT_MD = ROOT / "logs" / "founder_execution_chain_latest.md"

SOURCE_STEPS: List[tuple[str, str]] = [
    ("ai_platform_first_principles_review", "generate_ai_platform_first_principles_review.py"),
    ("system_split_first_principles_packet", "generate_system_split_first_principles_packet.py"),
    ("permit_review_case_presets", "generate_permit_review_case_presets.py"),
    ("permit_case_story_surface", "generate_permit_case_story_surface.py"),
    ("permit_operator_demo_packet", "generate_permit_operator_demo_packet.py"),
    ("permit_review_reason_decision_ladder", "generate_permit_review_reason_decision_ladder.py"),
    ("permit_next_action_brainstorm", "generate_permit_next_action_brainstorm.py"),
    ("yangdo_service_copy_packet", "generate_yangdo_service_copy_packet.py"),
    ("yangdo_public_language_audit", "generate_yangdo_public_language_audit.py"),
    ("yangdo_zero_display_recovery_audit", "generate_yangdo_zero_display_recovery_audit.py"),
    ("yangdo_next_action_brainstorm", "generate_yangdo_next_action_brainstorm.py"),
    ("founder_mode_prompt_bundle", "generate_founder_mode_prompt_bundle.py"),
    ("permit_prompt_case_binding_packet", "generate_permit_prompt_case_binding_packet.py"),
    ("permit_critical_prompt_surface_packet", "generate_permit_critical_prompt_surface_packet.py"),
    ("permit_partner_binding_parity_packet", "generate_permit_partner_binding_parity_packet.py"),
    ("permit_thinking_prompt_bundle_packet", "generate_permit_thinking_prompt_bundle_packet.py"),
    ("partner_input_operator_flow", "generate_partner_input_operator_flow.py"),
]

STABILIZATION_STEPS: List[tuple[str, str]] = [
    ("next_batch_focus_packet", "generate_next_batch_focus_packet.py"),
    ("next_execution_packet", "generate_next_execution_packet.py"),
    ("operations_packet", "generate_operations_packet.py"),
]


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _command_for(script_name: str) -> List[str]:
    return [sys.executable, str((ROOT / "scripts" / script_name).resolve())]


def _run_step(*, step_id: str, script_name: str) -> Dict[str, Any]:
    command = _command_for(script_name)
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = _safe_str(completed.stdout)
    stderr = _safe_str(completed.stderr)
    return {
        "step_id": step_id,
        "script": script_name,
        "command": command,
        "returncode": int(completed.returncode),
        "ok": completed.returncode == 0,
        "stdout_tail": "\n".join(stdout.splitlines()[-8:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-8:]),
    }


def build_payload(
    *,
    step_results: List[Dict[str, Any]],
    founder_bundle: Dict[str, Any],
    next_batch_focus: Dict[str, Any],
    next_execution: Dict[str, Any],
    operations: Dict[str, Any],
    stabilization_passes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    founder_summary = _safe_dict(founder_bundle.get("summary"))
    focus_summary = _safe_dict(next_batch_focus.get("summary"))
    execution_summary = _safe_dict(next_execution.get("summary"))
    operations_decisions = _safe_dict(operations.get("decisions"))

    founder_primary_system = _safe_str(founder_summary.get("primary_system"))
    founder_primary_lane_id = _safe_str(founder_summary.get("primary_lane_id"))
    focus_selected_track = _safe_str(focus_summary.get("selected_track"))
    focus_selected_lane_id = _safe_str(focus_summary.get("selected_lane_id"))
    execution_selected_track = _safe_str(execution_summary.get("selected_track"))
    execution_selected_lane_id = _safe_str(execution_summary.get("selected_lane_id"))

    chain_converged = bool(
        focus_selected_track
        and focus_selected_lane_id
        and focus_selected_track == execution_selected_track
        and focus_selected_lane_id == execution_selected_lane_id
    )
    founder_successor_transition = bool(
        founder_primary_system
        and founder_primary_lane_id
        and founder_primary_system == focus_selected_track
        and focus_selected_track == execution_selected_track
        and founder_primary_lane_id != focus_selected_lane_id
        and focus_selected_lane_id == execution_selected_lane_id
    )
    failed_steps = [row for row in step_results if not bool(row.get("ok"))]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "founder_execution_chain_latest",
        "summary": {
            "overall_ok": not failed_steps,
            "steps_total": len(step_results),
            "failed_step_total": len(failed_steps),
            "stabilization_pass_total": len(stabilization_passes),
            "founder_primary_system": founder_primary_system,
            "founder_primary_lane_id": founder_primary_lane_id,
            "focus_selected_track": focus_selected_track,
            "focus_selected_lane_id": focus_selected_lane_id,
            "execution_selected_track": execution_selected_track,
            "execution_selected_lane_id": execution_selected_lane_id,
            "selection_policy": _safe_str(focus_summary.get("selection_policy")),
            "focus_matches_execution": chain_converged,
            "founder_successor_transition": founder_successor_transition,
            "permit_prompt_case_binding_ready": bool(operations_decisions.get("permit_prompt_case_binding_ready")),
            "permit_partner_binding_parity_ready": bool(operations_decisions.get("permit_partner_binding_parity_ready")),
            "next_execution_ready": bool(operations_decisions.get("next_execution_ready")),
        },
        "step_results": step_results,
        "stabilization_passes": stabilization_passes,
        "founder_alignment": {
            "primary_system": founder_primary_system,
            "primary_lane_id": founder_primary_lane_id,
            "selection_policy": _safe_str(focus_summary.get("selection_policy")),
            "founder_primary_ready": bool(focus_summary.get("founder_primary_ready")),
            "founder_successor_selected": bool(focus_summary.get("founder_successor_selected")),
            "selected_matches_founder": bool(focus_summary.get("selected_matches_founder")),
            "execution_matches_primary": bool(execution_summary.get("founder_selected_matches_primary")),
        },
        "artifacts": {
            "founder_mode_prompt_bundle": str((ROOT / "logs" / "founder_mode_prompt_bundle_latest.json").resolve()),
            "next_batch_focus_packet": str((ROOT / "logs" / "next_batch_focus_packet_latest.json").resolve()),
            "next_execution_packet": str((ROOT / "logs" / "next_execution_packet_latest.json").resolve()),
            "operations_packet": str((ROOT / "logs" / "operations_packet_latest.json").resolve()),
        },
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    founder_alignment = _safe_dict(payload.get("founder_alignment"))
    lines = [
        "# Founder Execution Chain",
        "",
        "## Summary",
        f"- overall_ok: `{summary.get('overall_ok')}`",
        f"- steps_total: `{summary.get('steps_total')}`",
        f"- failed_step_total: `{summary.get('failed_step_total')}`",
        f"- stabilization_pass_total: `{summary.get('stabilization_pass_total')}`",
        f"- founder_primary: `{summary.get('founder_primary_system')}/{summary.get('founder_primary_lane_id')}`",
        f"- focus_selected: `{summary.get('focus_selected_track')}/{summary.get('focus_selected_lane_id')}`",
        f"- execution_selected: `{summary.get('execution_selected_track')}/{summary.get('execution_selected_lane_id')}`",
        f"- selection_policy: `{summary.get('selection_policy')}`",
        f"- focus_matches_execution: `{summary.get('focus_matches_execution')}`",
        f"- founder_successor_transition: `{summary.get('founder_successor_transition')}`",
        f"- post_write_operations_refresh_ok: `{summary.get('post_write_operations_refresh_ok')}`",
        f"- permit_prompt_case_binding_ready: `{summary.get('permit_prompt_case_binding_ready')}`",
        f"- permit_partner_binding_parity_ready: `{summary.get('permit_partner_binding_parity_ready')}`",
        f"- next_execution_ready: `{summary.get('next_execution_ready')}`",
        "",
        "## Founder Alignment",
        f"- founder_primary_ready: `{founder_alignment.get('founder_primary_ready')}`",
        f"- founder_successor_selected: `{founder_alignment.get('founder_successor_selected')}`",
        f"- selected_matches_founder: `{founder_alignment.get('selected_matches_founder')}`",
        f"- execution_matches_primary: `{founder_alignment.get('execution_matches_primary')}`",
        "",
        "## Stabilization Passes",
    ]
    for item in _safe_list(payload.get("stabilization_passes")):
        row = _safe_dict(item)
        lines.append(
            f"- pass {row.get('pass_index')}: `{row.get('focus_track')}/{row.get('focus_lane_id')}` -> `{row.get('execution_track')}/{row.get('execution_lane_id')}` / converged `{row.get('converged')}`"
        )
    lines.extend(["", "## Step Results"])
    for item in _safe_list(payload.get("step_results")):
        row = _safe_dict(item)
        lines.append(
            f"- `{row.get('step_id')}` ok=`{row.get('ok')}` rc=`{row.get('returncode')}` script=`{row.get('script')}`"
        )
    return "\n".join(lines).strip() + "\n"


def _record_stabilization_pass(pass_index: int) -> Dict[str, Any]:
    focus = _load_json(ROOT / "logs" / "next_batch_focus_packet_latest.json")
    execution = _load_json(ROOT / "logs" / "next_execution_packet_latest.json")
    focus_summary = _safe_dict(focus.get("summary"))
    execution_summary = _safe_dict(execution.get("summary"))
    focus_track = _safe_str(focus_summary.get("selected_track"))
    focus_lane_id = _safe_str(focus_summary.get("selected_lane_id"))
    execution_track = _safe_str(execution_summary.get("selected_track"))
    execution_lane_id = _safe_str(execution_summary.get("selected_lane_id"))
    return {
        "pass_index": pass_index,
        "focus_track": focus_track,
        "focus_lane_id": focus_lane_id,
        "execution_track": execution_track,
        "execution_lane_id": execution_lane_id,
        "converged": bool(
            focus_track
            and focus_lane_id
            and focus_track == execution_track
            and focus_lane_id == execution_lane_id
        ),
    }


def _refresh_operations_after_chain() -> Dict[str, Any]:
    return _run_step(
        step_id="post_write:operations_packet",
        script_name="generate_operations_packet.py",
    )


def run_chain(*, stabilization_pass_total: int) -> Dict[str, Any]:
    step_results: List[Dict[str, Any]] = []
    for step_id, script_name in SOURCE_STEPS:
        result = _run_step(step_id=step_id, script_name=script_name)
        step_results.append(result)
        if not result["ok"]:
            break

    stabilization_passes: List[Dict[str, Any]] = []
    if all(bool(row.get("ok")) for row in step_results):
        for pass_index in range(1, stabilization_pass_total + 1):
            pass_failed = False
            for step_id, script_name in STABILIZATION_STEPS:
                result = _run_step(step_id=f"pass_{pass_index}:{step_id}", script_name=script_name)
                step_results.append(result)
                if not result["ok"]:
                    pass_failed = True
                    break
            stabilization_passes.append(_record_stabilization_pass(pass_index))
            if pass_failed:
                break

    founder_bundle = _load_json(ROOT / "logs" / "founder_mode_prompt_bundle_latest.json")
    next_batch_focus = _load_json(ROOT / "logs" / "next_batch_focus_packet_latest.json")
    next_execution = _load_json(ROOT / "logs" / "next_execution_packet_latest.json")
    operations = _load_json(ROOT / "logs" / "operations_packet_latest.json")
    return build_payload(
        step_results=step_results,
        founder_bundle=founder_bundle,
        next_batch_focus=next_batch_focus,
        next_execution=next_execution,
        operations=operations,
        stabilization_passes=stabilization_passes,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the founder/next-focus/operations chain sequentially.")
    parser.add_argument("--stabilization-passes", type=int, default=2)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = run_chain(stabilization_pass_total=max(1, int(args.stabilization_passes)))
    refresh_result: Dict[str, Any] = {}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    refresh_result = _refresh_operations_after_chain() if bool(_safe_dict(payload.get("summary")).get("overall_ok")) else {}
    if refresh_result:
        summary = _safe_dict(payload.get("summary"))
        summary["post_write_operations_refresh_ok"] = bool(refresh_result.get("ok"))
        summary["post_write_operations_refresh_returncode"] = int(refresh_result.get("returncode") or 0)
        payload["post_write_refresh"] = refresh_result
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": bool(_safe_dict(payload.get("summary")).get("overall_ok")) and (not refresh_result or bool(refresh_result.get("ok"))),
                "json": str(args.json),
                "md": str(args.md),
                "post_write_operations_refresh_ok": bool(refresh_result.get("ok")) if refresh_result else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if bool(_safe_dict(payload.get("summary")).get("overall_ok")) and (not refresh_result or bool(refresh_result.get("ok"))) else 1


if __name__ == "__main__":
    raise SystemExit(main())
