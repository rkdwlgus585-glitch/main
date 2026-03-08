#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRAINSTORM = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_FOUNDER = ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"
DEFAULT_COPY = ROOT / "logs" / "permit_service_copy_packet_latest.json"
DEFAULT_UX = ROOT / "logs" / "permit_service_ux_packet_latest.json"
DEFAULT_ALIGNMENT = ROOT / "logs" / "permit_service_alignment_audit_latest.json"
DEFAULT_CASE_BINDING = ROOT / "logs" / "permit_prompt_case_binding_packet_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.md"


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


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> List[str]:
    out: List[str] = []
    for item in _safe_list(value):
        text = _safe_str(item)
        if text and text not in out:
            out.append(text)
    return out


def _non_empty_unique(items: List[str]) -> List[str]:
    out: List[str] = []
    for item in items:
        text = _safe_str(item)
        if text and text not in out:
            out.append(text)
    return out


def _compact_decision_lens(
    *,
    lane_id: str,
    lane_title: str,
    canonical_lane: Dict[str, Any],
    founder_primary: Dict[str, Any],
    critical_prompts: Dict[str, Any],
    operator_surface_ready: bool,
    release_surface_ready: bool,
    alignment_ok: bool,
    prompt_case_binding_ready: bool,
    operator_jump_table_ready: bool,
) -> Dict[str, Any]:
    founder_questions = _string_list(critical_prompts.get("founder_mode_questions"))
    bottleneck_statement = _safe_str(canonical_lane.get("current_gap"))
    why_now = _safe_str(canonical_lane.get("why_now") or canonical_lane.get("evidence"))
    next_action = _safe_str(canonical_lane.get("proposed_next_step") or founder_primary.get("proposed_next_step"))
    success_metric = _safe_str(canonical_lane.get("success_metric") or founder_primary.get("success_metric"))

    if not prompt_case_binding_ready:
        inspect_first = "Prompt-to-case jump targets and representative preset bindings"
        evidence_first = [
            "permit_prompt_case_binding_packet.question_bindings",
            "permit_prompt_case_binding_packet.operator_jump_table",
            "runtime prompt preset buttons",
        ]
    elif not operator_surface_ready:
        inspect_first = "Operator-facing next action block and prompt jump surface"
        evidence_first = [
            "permit_service_copy_packet.next_actions",
            "operator demo packet",
            "runtime operator demo surface",
        ]
    elif not release_surface_ready or not alignment_ok:
        inspect_first = "Release summary experience and permit service alignment audit"
        evidence_first = [
            "permit_service_ux_packet.public_summary_experience",
            "permit_service_ux_packet.manual_review_assist_experience",
            "permit_service_alignment_audit.summary",
        ]
    else:
        inspect_first = "Runtime critical-thinking lens, reasoning card, and operator jump button"
        evidence_first = [
            "runtime critical prompt lens",
            "runtime reasoning card",
            "runtime prompt preset jump",
        ]

    falsification_test = (
        "If operator, runtime, and release surfaces expose the same active lane, "
        "inspect-first focus, and preset jump without opening raw markdown, this lane closes."
    )
    anti_patterns = _non_empty_unique(
        [
            "Do not summarize the bottleneck as generic UX polish.",
            "Do not expose raw markdown only; compress it into a reusable action lens.",
            "Do not mark the lane green if prompt-to-case jumps disappear from runtime.",
        ]
    )
    lens = {
        "lane_id": lane_id,
        "lane_title": lane_title,
        "bottleneck_statement": bottleneck_statement,
        "why_now": why_now,
        "inspect_first": inspect_first,
        "evidence_first": evidence_first,
        "next_action": next_action,
        "success_metric": success_metric,
        "falsification_test": falsification_test,
        "founder_questions": founder_questions[:3],
        "anti_patterns": anti_patterns[:3],
        "operator_contract_targets": [
            "operations_packet.next_execution",
            "partner_input_operator_flow",
            "permit_service_copy_packet.next_actions",
        ],
        "release_contract_targets": [
            "permit_service_ux_packet.public_summary_experience",
            "permit_service_ux_packet.detail_checklist_experience",
            "permit_service_ux_packet.manual_review_assist_experience",
        ],
        "runtime_contract_targets": [
            "runtime critical prompt lens",
            "runtime reasoning card",
            "runtime prompt preset jump",
        ],
        "operator_jump_table_ready": operator_jump_table_ready,
    }
    lens["lens_ready"] = all(
        [
            bool(lens["bottleneck_statement"]),
            bool(lens["inspect_first"]),
            bool(lens["next_action"]),
            bool(lens["falsification_test"]),
            bool(lens["founder_questions"]),
        ]
    )
    return lens


def build_packet(
    *,
    brainstorm_path: Path,
    founder_path: Path,
    copy_path: Path,
    ux_path: Path,
    alignment_path: Path,
    case_binding_path: Path,
) -> Dict[str, Any]:
    brainstorm = _load_json(brainstorm_path)
    founder = _load_json(founder_path)
    copy_packet = _load_json(copy_path)
    ux_packet = _load_json(ux_path)
    alignment = _load_json(alignment_path)
    case_binding = _load_json(case_binding_path)

    brainstorm_summary = _safe_dict(brainstorm.get("summary"))
    current_lane = _safe_dict(brainstorm.get("current_execution_lane"))
    critical_prompts = _safe_dict(brainstorm.get("critical_prompts"))
    founder_summary = _safe_dict(founder.get("summary"))
    founder_primary = _safe_dict(founder.get("primary_execution"))
    copy_summary = _safe_dict(copy_packet.get("summary"))
    ux_summary = _safe_dict(ux_packet.get("summary"))
    alignment_summary = _safe_dict(alignment.get("summary"))
    case_binding_summary = _safe_dict(case_binding.get("summary"))

    founder_primary_system = _safe_str(founder_summary.get("primary_system"))
    founder_primary_lane_id = _safe_str(founder_summary.get("primary_lane_id"))
    current_execution_lane_id = _safe_str(current_lane.get("id"))
    current_execution_lane_title = _safe_str(current_lane.get("title"))
    founder_is_permit = founder_primary_system == "permit"
    canonical_lane = founder_primary if founder_is_permit and founder_primary_lane_id else current_lane
    lane_id = _safe_str(
        canonical_lane.get("id")
        or (founder_primary_lane_id if founder_is_permit else "")
        or current_execution_lane_id
        or "critical_prompt_surface_lock"
    )
    lane_title = _safe_str(canonical_lane.get("title") or current_execution_lane_title or "critical prompt surface lock")
    founder_lane_match = (
        founder_primary_lane_id == lane_id
        if founder_is_permit and founder_primary_lane_id
        else True
    )

    operator_surface_ready = bool(brainstorm_summary.get("prompt_doc_ready")) and bool(copy_summary.get("service_copy_ready"))
    release_surface_ready = bool(ux_summary.get("packet_ready")) and bool(alignment_summary.get("alignment_ok"))
    prompt_case_binding_ready = bool(case_binding_summary.get("packet_ready")) and bool(case_binding_summary.get("operator_jump_table_ready"))
    compact_decision_lens = _compact_decision_lens(
        lane_id=lane_id,
        lane_title=lane_title,
        canonical_lane=canonical_lane,
        founder_primary=founder_primary,
        critical_prompts=critical_prompts,
        operator_surface_ready=operator_surface_ready,
        release_surface_ready=release_surface_ready,
        alignment_ok=bool(alignment_summary.get("alignment_ok")),
        prompt_case_binding_ready=prompt_case_binding_ready,
        operator_jump_table_ready=bool(case_binding_summary.get("operator_jump_table_ready")),
    )
    runtime_surface_contract_ready = bool(compact_decision_lens.get("lens_ready")) and prompt_case_binding_ready
    release_surface_contract_ready = bool(compact_decision_lens.get("lens_ready")) and release_surface_ready
    operator_surface_contract_ready = bool(compact_decision_lens.get("lens_ready")) and operator_surface_ready
    packet_ready = (
        operator_surface_ready
        and release_surface_ready
        and founder_lane_match
        and prompt_case_binding_ready
        and bool(compact_decision_lens.get("lens_ready"))
    )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_critical_prompt_surface_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "lane_id": lane_id,
            "lane_title": lane_title,
            "founder_primary_system": founder_primary_system,
            "founder_primary_lane_id": founder_primary_lane_id,
            "current_execution_lane_id": current_execution_lane_id,
            "current_execution_lane_title": current_execution_lane_title,
            "current_execution_lane_matches_packet": current_execution_lane_id == lane_id,
            "operator_surface_ready": operator_surface_ready,
            "release_surface_ready": release_surface_ready,
            "founder_lane_match": founder_lane_match,
            "alignment_ok": bool(alignment_summary.get("alignment_ok")),
            "service_copy_ready": bool(copy_summary.get("service_copy_ready")),
            "service_ux_ready": bool(ux_summary.get("packet_ready")),
            "prompt_case_binding_ready": prompt_case_binding_ready,
            "operator_jump_table_ready": bool(case_binding_summary.get("operator_jump_table_ready")),
            "compact_lens_ready": bool(compact_decision_lens.get("lens_ready")),
            "runtime_surface_contract_ready": runtime_surface_contract_ready,
            "release_surface_contract_ready": release_surface_contract_ready,
            "operator_surface_contract_ready": operator_surface_contract_ready,
            "founder_question_total": len(_string_list(critical_prompts.get("founder_mode_questions"))),
        },
        "critical_prompt_block": {
            "title": lane_title,
            "current_gap": _safe_str(canonical_lane.get("current_gap")),
            "evidence": _safe_str(canonical_lane.get("evidence")),
            "proposed_next_step": _safe_str(canonical_lane.get("proposed_next_step")),
            "success_metric": _safe_str(canonical_lane.get("success_metric") or founder_primary.get("success_metric")),
            "execution_prompt": _safe_str(critical_prompts.get("execution_prompt") or brainstorm.get("execution_prompt")),
            "brainstorm_prompt": _safe_str(critical_prompts.get("brainstorm_prompt") or brainstorm.get("brainstorm_prompt")),
            "first_principles_prompt": _safe_str(critical_prompts.get("first_principles_prompt") or brainstorm.get("first_principles_prompt")),
            "founder_questions": _string_list(critical_prompts.get("founder_mode_questions")),
        },
        "compact_decision_lens": compact_decision_lens,
        "surface_targets": {
            "operator_surface": [
                "operations_packet.next_execution",
                "partner_input_operator_flow",
                "permit_service_copy_packet.next_actions",
            ],
            "release_surface": [
                "permit_service_ux_packet.public_summary_experience",
                "permit_service_ux_packet.detail_checklist_experience",
                "permit_service_ux_packet.manual_review_assist_experience",
            ],
        },
        "verification_targets": [
            "permit_service_copy_ready == true",
            "permit_service_ux_ready == true",
            "permit_service_alignment_ok == true",
            "permit_prompt_case_binding_ready == true",
            "permit_critical_prompt_compact_lens_ready == true",
            "permit_critical_prompt_runtime_surface_contract_ready == true",
            (
                f"founder primary lane == permit/{lane_id}"
                if founder_is_permit
                else f"current permit execution lane == {lane_id}"
            ),
        ],
        "next_actions": [
            "Keep the critical prompt block visible in operator-facing permit packets.",
            "Keep the compact decision lens reusable across runtime, release, and operator surfaces.",
            "Do not collapse checklist detail and manual-review assist into one generic CTA.",
            "Treat this packet as the canonical proof that the current founder primary lane is embedded in runtime-facing artifacts.",
            "Do not mark the lane green unless prompt-to-case jump targets remain available to operators.",
        ],
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    block = _safe_dict(payload.get("critical_prompt_block"))
    lines = [
        "# Permit Critical Prompt Surface Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- lane_id: {summary.get('lane_id')}",
        f"- lane_title: {summary.get('lane_title')}",
        f"- founder_primary_lane_id: {summary.get('founder_primary_lane_id')}",
        f"- current_execution_lane_id: {summary.get('current_execution_lane_id')}",
        f"- current_execution_lane_matches_packet: {summary.get('current_execution_lane_matches_packet')}",
        f"- operator_surface_ready: {summary.get('operator_surface_ready')}",
        f"- release_surface_ready: {summary.get('release_surface_ready')}",
        f"- founder_lane_match: {summary.get('founder_lane_match')}",
        f"- prompt_case_binding_ready: {summary.get('prompt_case_binding_ready')}",
        f"- operator_jump_table_ready: {summary.get('operator_jump_table_ready')}",
        f"- compact_lens_ready: {summary.get('compact_lens_ready')}",
        f"- runtime_surface_contract_ready: {summary.get('runtime_surface_contract_ready')}",
        f"- release_surface_contract_ready: {summary.get('release_surface_contract_ready')}",
        f"- operator_surface_contract_ready: {summary.get('operator_surface_contract_ready')}",
        "",
        "## Critical Prompt Block",
        f"- current_gap: {block.get('current_gap')}",
        f"- evidence: {block.get('evidence')}",
        f"- proposed_next_step: {block.get('proposed_next_step')}",
        f"- success_metric: {block.get('success_metric')}",
        "",
        "## Compact Decision Lens",
        f"- bottleneck_statement: {_safe_dict(payload.get('compact_decision_lens')).get('bottleneck_statement')}",
        f"- why_now: {_safe_dict(payload.get('compact_decision_lens')).get('why_now')}",
        f"- inspect_first: {_safe_dict(payload.get('compact_decision_lens')).get('inspect_first')}",
        f"- next_action: {_safe_dict(payload.get('compact_decision_lens')).get('next_action')}",
        f"- falsification_test: {_safe_dict(payload.get('compact_decision_lens')).get('falsification_test')}",
        "",
        "## Surface Targets",
    ]
    for key, rows in (_safe_dict(payload.get("surface_targets"))).items():
        lines.append(f"- {key}: {', '.join(_string_list(rows))}")
    lines.extend(["", "## Verification Targets"])
    for item in _string_list(payload.get("verification_targets")):
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the canonical permit critical prompt surface packet.")
    parser.add_argument("--brainstorm", type=Path, default=DEFAULT_BRAINSTORM)
    parser.add_argument("--founder", type=Path, default=DEFAULT_FOUNDER)
    parser.add_argument("--copy", type=Path, default=DEFAULT_COPY)
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--alignment", type=Path, default=DEFAULT_ALIGNMENT)
    parser.add_argument("--case-binding", type=Path, default=DEFAULT_CASE_BINDING)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        brainstorm_path=args.brainstorm,
        founder_path=args.founder,
        copy_path=args.copy,
        ux_path=args.ux,
        alignment_path=args.alignment,
        case_binding_path=args.case_binding,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool(_safe_dict(payload.get("summary")).get("packet_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
