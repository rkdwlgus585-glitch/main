#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRAINSTORM = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_FOUNDER = ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"
DEFAULT_COPY = ROOT / "logs" / "permit_service_copy_packet_latest.json"
DEFAULT_UX = ROOT / "logs" / "permit_service_ux_packet_latest.json"
DEFAULT_ALIGNMENT = ROOT / "logs" / "permit_service_alignment_audit_latest.json"
DEFAULT_PUBLIC_CONTRACT = ROOT / "logs" / "permit_public_contract_audit_latest.json"
DEFAULT_CASE_BINDING = ROOT / "logs" / "permit_prompt_case_binding_packet_latest.json"
DEFAULT_CRITICAL_PROMPT = ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.json"
DEFAULT_PARTNER_BINDING = ROOT / "logs" / "permit_partner_binding_parity_packet_latest.json"
DEFAULT_REVIEW_REASON = ROOT / "logs" / "permit_review_reason_decision_ladder_latest.json"
DEFAULT_SYSTEM_SPLIT = ROOT / "logs" / "system_split_first_principles_packet_latest.json"
DEFAULT_PROMPT_DOC = ROOT / "docs" / "permit_critical_thinking_prompt.md"
DEFAULT_JSON = ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


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


def _doc_sections(text: str) -> List[str]:
    sections: List[str] = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            title = stripped.lstrip("#").strip()
            if title and title not in sections:
                sections.append(title)
    return sections


def _excerpt(text: str, limit: int = 6) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def _normalize_heading(value: Any) -> str:
    return re.sub(r"[\W_]+", "", _safe_str(value).lower())


def _doc_section_map(text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current_key = ""
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("##"):
            current_key = stripped.lstrip("#").strip()
            if current_key and current_key not in sections:
                sections[current_key] = []
            continue
        if current_key and stripped:
            sections.setdefault(current_key, []).append(stripped)
    return sections


def _section_lines(section_map: Dict[str, List[str]], *aliases: str) -> List[str]:
    if not aliases:
        return []
    normalized_aliases = {_normalize_heading(alias) for alias in aliases if _safe_str(alias)}
    out: List[str] = []
    for heading, lines in section_map.items():
        if _normalize_heading(heading) not in normalized_aliases:
            continue
        for line in lines:
            text = re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", _safe_str(line))
            if text and text not in out:
                out.append(text)
    return out


def _decision_ladder_preview(rows: List[Any], limit: int = 6) -> List[Dict[str, Any]]:
    preview: List[Dict[str, Any]] = []
    for row in rows:
        item = _safe_dict(row)
        if not item:
            continue
        preview.append(
            {
                "review_reason": _safe_str(item.get("review_reason")),
                "inspect_first": _safe_str(item.get("inspect_first")),
                "next_action": _safe_str(item.get("next_action")),
                "manual_review_gate": bool(item.get("manual_review_gate")),
            }
        )
        if len(preview) >= limit:
            break
    return preview


def _operator_jump_preview(rows: List[Any], limit: int = 6) -> List[Dict[str, Any]]:
    preview: List[Dict[str, Any]] = []
    for row in rows:
        item = _safe_dict(row)
        if not item:
            continue
        jump_targets = [_safe_dict(target) for target in _safe_list(item.get("jump_targets")) if _safe_dict(target)]
        preview.append(
            {
                "claim_id": _safe_str(item.get("claim_id")),
                "family_key": _safe_str(item.get("family_key")),
                "jump_target_total": len(jump_targets),
                "representative_preset_ids": [
                    _safe_str(target.get("preset_id"))
                    for target in jump_targets[:3]
                    if _safe_str(target.get("preset_id"))
                ],
            }
        )
        if len(preview) >= limit:
            break
    return preview


def _allow_downstream_lane_progression(
    *,
    lane_id: str,
    current_execution_lane_id: str,
    founder_lane_match: bool,
    system_bottleneck_match: bool,
    prompt_case_binding_ready: bool,
    critical_prompt_ready: bool,
    partner_binding_ready: bool,
    runtime_target_ready: bool,
    release_target_ready: bool,
    operator_target_ready: bool,
    allowed_successor_lane_ids: List[str],
) -> bool:
    if not current_execution_lane_id or current_execution_lane_id == lane_id:
        return False
    if current_execution_lane_id not in allowed_successor_lane_ids:
        return False
    return all(
        [
            founder_lane_match,
            system_bottleneck_match,
            prompt_case_binding_ready,
            critical_prompt_ready,
            partner_binding_ready,
            runtime_target_ready,
            release_target_ready,
            operator_target_ready,
        ]
    )


def build_packet(
    *,
    brainstorm_path: Path,
    founder_path: Path,
    copy_path: Path,
    ux_path: Path,
    alignment_path: Path,
    public_contract_path: Path,
    case_binding_path: Path,
    critical_prompt_path: Path,
    partner_binding_path: Path,
    review_reason_path: Path,
    system_split_path: Path,
    prompt_doc_path: Path,
) -> Dict[str, Any]:
    brainstorm = _load_json(brainstorm_path)
    founder = _load_json(founder_path)
    copy_packet = _load_json(copy_path)
    ux_packet = _load_json(ux_path)
    alignment = _load_json(alignment_path)
    public_contract = _load_json(public_contract_path)
    case_binding = _load_json(case_binding_path)
    critical_prompt = _load_json(critical_prompt_path)
    partner_binding = _load_json(partner_binding_path)
    review_reason = _load_json(review_reason_path)
    system_split = _load_json(system_split_path)
    prompt_doc_text = _load_text(prompt_doc_path)

    brainstorm_summary = _safe_dict(brainstorm.get("summary"))
    current_lane = _safe_dict(brainstorm.get("current_execution_lane"))
    critical_prompts = _safe_dict(brainstorm.get("critical_prompts"))
    founder_summary = _safe_dict(founder.get("summary"))
    founder_primary = _safe_dict(founder.get("primary_execution"))
    copy_summary = _safe_dict(copy_packet.get("summary"))
    ux_summary = _safe_dict(ux_packet.get("summary"))
    alignment_summary = _safe_dict(alignment.get("summary"))
    public_contract_summary = _safe_dict(public_contract.get("summary"))
    case_binding_summary = _safe_dict(case_binding.get("summary"))
    critical_prompt_summary = _safe_dict(critical_prompt.get("summary"))
    partner_binding_summary = _safe_dict(partner_binding.get("summary"))
    review_reason_summary = _safe_dict(review_reason.get("summary"))
    permit_track = _safe_dict(_safe_dict(system_split.get("tracks")).get("permit"))

    founder_primary_system = _safe_str(founder_summary.get("primary_system"))
    founder_primary_lane_id = _safe_str(founder_summary.get("primary_lane_id"))
    founder_parallel_system = _safe_str(founder_summary.get("parallel_system"))
    founder_parallel_lane_id = _safe_str(founder_summary.get("parallel_lane_id"))
    current_execution_lane_id = _safe_str(current_lane.get("id"))
    canonical_lane = (
        founder_primary
        if founder_primary_system == "permit" and founder_primary_lane_id
        else current_lane
    )
    lane_id = _safe_str(
        canonical_lane.get("id")
        or founder_primary_lane_id
        or current_execution_lane_id
        or "thinking_prompt_bundle_lock"
    )
    lane_title = _safe_str(canonical_lane.get("title") or "thinking prompt bundle lock")

    prompt_sections = _doc_sections(prompt_doc_text)
    prompt_section_map = _doc_section_map(prompt_doc_text)
    execution_principles = _section_lines(prompt_section_map, "실행 원칙", "action frame", "execution principles")
    musk_questions = _section_lines(
        prompt_section_map,
        "머스크식 1차원 질문",
        "musk first principles",
        "first principles questions",
    )
    founder_questions_doc = _section_lines(
        prompt_section_map,
        "창업자 모드 질문",
        "founder mode questions",
        "founder questions",
    )
    anti_patterns = _section_lines(prompt_section_map, "안티패턴", "anti-patterns", "anti patterns")
    parallel_filters = _section_lines(
        prompt_section_map,
        "병렬 브레인스토밍 필터",
        "parallel brainstorming filter",
        "parallel brainstorm filter",
    )
    case_binding_question_bindings = _safe_list(case_binding.get("question_bindings"))
    operator_jump_table = _safe_list(case_binding.get("operator_jump_table"))
    decision_ladder_rows = _safe_list(review_reason.get("decision_ladder") or review_reason.get("ladders"))
    prompt_doc_ready = bool(prompt_doc_text.strip())
    prompt_sections_ready = len(prompt_sections) >= 5
    founder_lane_match = founder_primary_system == "permit" and founder_primary_lane_id == lane_id
    founder_parallel_match = founder_parallel_system == "permit" and founder_parallel_lane_id == lane_id
    founder_lane_context_ok = founder_lane_match or founder_parallel_match
    system_current_bottleneck = _safe_str(permit_track.get("current_bottleneck"))
    allowed_successor_lane_ids = [
        "partner_binding_observability",
        "runtime_reasoning_card",
        "partner_gap_preview_digest",
        "thinking_prompt_successor_alignment",
        "closed_lane_stale_audit",
        "critical_prompt_surface_lock",
        "demo_surface_observability",
        "capital_registration_logic_lock",
        "capital_registration_logic_brainstorm",
    ]
    system_bottleneck_match = system_current_bottleneck in {lane_id, *allowed_successor_lane_ids}

    service_copy_ready = bool(copy_summary.get("service_copy_ready"))
    service_ux_ready = bool(ux_summary.get("packet_ready"))
    alignment_ok = bool(alignment_summary.get("alignment_ok"))
    public_contract_ok = bool(public_contract_summary.get("contract_ok"))
    review_reason_ready = bool(review_reason_summary.get("decision_ladder_ready"))
    prompt_case_binding_ready = bool(case_binding_summary.get("packet_ready"))
    critical_prompt_ready = bool(critical_prompt_summary.get("packet_ready"))
    partner_binding_ready = bool(partner_binding_summary.get("packet_ready"))
    operator_jump_case_total = sum(
        len(_safe_list(_safe_dict(row).get("jump_targets"))) for row in operator_jump_table
    )

    runtime_target_ready = prompt_case_binding_ready and review_reason_ready
    release_target_ready = (
        bool(critical_prompt_summary.get("release_surface_ready"))
        and public_contract_ok
        and service_ux_ready
    )
    operator_target_ready = (
        bool(critical_prompt_summary.get("operator_surface_ready"))
        and bool(partner_binding_summary.get("partner_surface_ready"))
        and service_copy_ready
    )
    downstream_lane_progression_accepted = _allow_downstream_lane_progression(
        lane_id=lane_id,
        current_execution_lane_id=current_execution_lane_id,
        founder_lane_match=founder_lane_match,
        system_bottleneck_match=system_bottleneck_match,
        prompt_case_binding_ready=prompt_case_binding_ready,
        critical_prompt_ready=critical_prompt_ready,
        partner_binding_ready=partner_binding_ready,
        runtime_target_ready=runtime_target_ready,
        release_target_ready=release_target_ready,
        operator_target_ready=operator_target_ready,
        allowed_successor_lane_ids=allowed_successor_lane_ids,
    )
    current_execution_lane_matches_packet = current_execution_lane_id == lane_id or downstream_lane_progression_accepted
    founder_transition_context_ready = (
        founder_lane_context_ok
        and system_bottleneck_match
        and current_execution_lane_matches_packet
    )
    if founder_primary_system != "permit":
        founder_lane_context_ok = founder_parallel_match or current_execution_lane_matches_packet
        founder_transition_context_ready = founder_lane_context_ok and system_bottleneck_match

    packet_ready = all(
        [
            founder_lane_context_ok,
            current_execution_lane_matches_packet,
            system_bottleneck_match,
            prompt_doc_ready,
            prompt_sections_ready,
            service_copy_ready,
            service_ux_ready,
            alignment_ok,
            public_contract_ok,
            review_reason_ready,
            prompt_case_binding_ready,
            critical_prompt_ready,
            partner_binding_ready,
            runtime_target_ready,
            release_target_ready,
            operator_target_ready,
            founder_transition_context_ready,
        ]
    )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_thinking_prompt_bundle_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "lane_id": lane_id,
            "lane_title": lane_title,
            "founder_primary_system": founder_primary_system,
            "founder_primary_lane_id": founder_primary_lane_id,
            "founder_parallel_system": founder_parallel_system,
            "founder_parallel_lane_id": founder_parallel_lane_id,
            "founder_lane_match": founder_lane_match,
            "founder_parallel_match": founder_parallel_match,
            "founder_lane_context_ok": founder_lane_context_ok,
            "current_execution_lane_id": current_execution_lane_id,
            "current_execution_lane_matches_packet": current_execution_lane_matches_packet,
            "downstream_lane_progression_accepted": downstream_lane_progression_accepted,
            "system_bottleneck_match": system_bottleneck_match,
            "system_current_bottleneck": system_current_bottleneck,
            "allowed_successor_lane_ids": allowed_successor_lane_ids,
            "prompt_doc_ready": prompt_doc_ready,
            "prompt_sections_ready": prompt_sections_ready,
            "prompt_section_total": len(prompt_sections),
            "execution_principle_total": len(execution_principles),
            "musk_question_total": len(musk_questions),
            "founder_question_total": len(
                _string_list(critical_prompts.get("founder_mode_questions") or founder.get("founder_mode_questions") or founder_questions_doc)
            ),
            "anti_pattern_total": len(anti_patterns),
            "parallel_filter_total": len(parallel_filters),
            "question_binding_total": len(case_binding_question_bindings),
            "operator_jump_family_total": len(operator_jump_table),
            "operator_jump_case_total": operator_jump_case_total,
            "decision_ladder_row_total": len(decision_ladder_rows),
            "service_copy_ready": service_copy_ready,
            "service_ux_ready": service_ux_ready,
            "alignment_ok": alignment_ok,
            "public_contract_ok": public_contract_ok,
            "review_reason_ready": review_reason_ready,
            "prompt_case_binding_ready": prompt_case_binding_ready,
            "critical_prompt_ready": critical_prompt_ready,
            "partner_binding_ready": partner_binding_ready,
            "runtime_target_ready": runtime_target_ready,
            "release_target_ready": release_target_ready,
            "operator_target_ready": operator_target_ready,
            "founder_transition_context_ready": founder_transition_context_ready,
        },
        "prompt_bundle": {
            "current_gap": _safe_str(canonical_lane.get("current_gap")),
            "evidence": _safe_str(canonical_lane.get("evidence")),
            "proposed_next_step": _safe_str(canonical_lane.get("proposed_next_step")),
            "success_metric": _safe_str(canonical_lane.get("success_metric") or founder_primary.get("success_metric")),
            "execution_prompt": _safe_str(critical_prompts.get("execution_prompt") or founder.get("unified_prompts", {}).get("execution_prompt")),
            "brainstorm_prompt": _safe_str(critical_prompts.get("brainstorm_prompt") or founder.get("unified_prompts", {}).get("parallel_brainstorm_prompt")),
            "first_principles_prompt": _safe_str(critical_prompts.get("first_principles_prompt") or founder.get("unified_prompts", {}).get("first_principles_prompt")),
            "founder_questions": _string_list(
                critical_prompts.get("founder_mode_questions") or founder.get("founder_mode_questions") or founder_questions_doc
            ),
            "execution_principles": execution_principles,
            "musk_questions": musk_questions,
            "anti_patterns": anti_patterns,
            "parallel_brainstorm_filters": parallel_filters,
            "decision_ladder_preview": _decision_ladder_preview(decision_ladder_rows),
            "operator_jump_preview": _operator_jump_preview(operator_jump_table),
            "prompt_doc_excerpt": _excerpt(prompt_doc_text),
            "prompt_sections": prompt_sections,
        },
        "surface_contract": {
            "runtime_targets": [
                "permit_review_reason_decision_ladder",
                "permit_prompt_case_binding_packet",
            ],
            "release_targets": [
                "permit_service_ux_packet",
                "permit_public_contract_audit",
                "permit_critical_prompt_surface_packet.release_surface",
            ],
            "operator_targets": [
                "permit_service_copy_packet",
                "permit_partner_binding_parity_packet",
                "permit_critical_prompt_surface_packet.operator_surface",
            ],
        },
        "verification_targets": [
            "permit_service_copy_ready == true",
            "permit_service_ux_ready == true",
            "permit_service_alignment_ok == true",
            "permit_public_contract_ok == true",
            "permit_review_reason_decision_ladder_ready == true",
            "permit_prompt_case_binding_ready == true",
            "permit_critical_prompt_surface_ready == true",
            "permit_partner_binding_parity_ready == true",
            "permit_thinking_prompt_bundle_runtime_target_ready == true",
            "permit_thinking_prompt_bundle_release_target_ready == true",
            "permit_thinking_prompt_bundle_operator_target_ready == true",
            "permit_thinking_prompt_bundle_decision_ladder_row_total > 0",
            "permit_thinking_prompt_bundle_operator_jump_case_total > 0",
        ],
        "next_actions": [
            "Keep the permit critical thinking prompt, decision ladder, and partner-safe binding surface in one execution contract.",
            "Do not mark the lane green if runtime, release, and operator surfaces point to different permit next moves.",
            "Treat this packet as the canonical proof that permit reasoning now survives runtime, release, and operator handoff without manual interpretation.",
        ],
        "artifacts": {
            "brainstorm": str(brainstorm_path.resolve()),
            "founder_bundle": str(founder_path.resolve()),
            "copy_packet": str(copy_path.resolve()),
            "ux_packet": str(ux_path.resolve()),
            "alignment_audit": str(alignment_path.resolve()),
            "public_contract_audit": str(public_contract_path.resolve()),
            "prompt_case_binding": str(case_binding_path.resolve()),
            "critical_prompt_surface": str(critical_prompt_path.resolve()),
            "partner_binding_parity": str(partner_binding_path.resolve()),
            "review_reason_decision_ladder": str(review_reason_path.resolve()),
            "system_split_first_principles": str(system_split_path.resolve()),
            "prompt_doc": str(prompt_doc_path.resolve()),
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    prompt_bundle = _safe_dict(payload.get("prompt_bundle"))
    lines = [
        "# Permit Thinking Prompt Bundle Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- lane_id: {summary.get('lane_id')}",
        f"- lane_title: {summary.get('lane_title')}",
        f"- founder_primary_lane_id: {summary.get('founder_primary_lane_id')}",
        f"- founder_parallel_lane_id: {summary.get('founder_parallel_lane_id')}",
        f"- founder_lane_match: {summary.get('founder_lane_match')}",
        f"- founder_parallel_match: {summary.get('founder_parallel_match')}",
        f"- founder_lane_context_ok: {summary.get('founder_lane_context_ok')}",
        f"- current_execution_lane_id: {summary.get('current_execution_lane_id')}",
        f"- current_execution_lane_matches_packet: {summary.get('current_execution_lane_matches_packet')}",
        f"- downstream_lane_progression_accepted: {summary.get('downstream_lane_progression_accepted')}",
        f"- system_bottleneck_match: {summary.get('system_bottleneck_match')}",
        f"- system_current_bottleneck: {summary.get('system_current_bottleneck')}",
        f"- allowed_successor_lane_ids: {', '.join(_string_list(summary.get('allowed_successor_lane_ids')))}",
        f"- prompt_doc_ready: {summary.get('prompt_doc_ready')}",
        f"- prompt_sections_ready: {summary.get('prompt_sections_ready')}",
        f"- execution_principle_total: {summary.get('execution_principle_total')}",
        f"- musk_question_total: {summary.get('musk_question_total')}",
        f"- founder_question_total: {summary.get('founder_question_total')}",
        f"- anti_pattern_total: {summary.get('anti_pattern_total')}",
        f"- parallel_filter_total: {summary.get('parallel_filter_total')}",
        f"- question_binding_total: {summary.get('question_binding_total')}",
        f"- operator_jump_family_total: {summary.get('operator_jump_family_total')}",
        f"- operator_jump_case_total: {summary.get('operator_jump_case_total')}",
        f"- decision_ladder_row_total: {summary.get('decision_ladder_row_total')}",
        f"- service_copy_ready: {summary.get('service_copy_ready')}",
        f"- service_ux_ready: {summary.get('service_ux_ready')}",
        f"- alignment_ok: {summary.get('alignment_ok')}",
        f"- public_contract_ok: {summary.get('public_contract_ok')}",
        f"- review_reason_ready: {summary.get('review_reason_ready')}",
        f"- prompt_case_binding_ready: {summary.get('prompt_case_binding_ready')}",
        f"- critical_prompt_ready: {summary.get('critical_prompt_ready')}",
        f"- partner_binding_ready: {summary.get('partner_binding_ready')}",
        f"- runtime_target_ready: {summary.get('runtime_target_ready')}",
        f"- release_target_ready: {summary.get('release_target_ready')}",
        f"- operator_target_ready: {summary.get('operator_target_ready')}",
        f"- founder_transition_context_ready: {summary.get('founder_transition_context_ready')}",
        "",
        "## Prompt Bundle",
        f"- current_gap: {prompt_bundle.get('current_gap')}",
        f"- evidence: {prompt_bundle.get('evidence')}",
        f"- proposed_next_step: {prompt_bundle.get('proposed_next_step')}",
        f"- success_metric: {prompt_bundle.get('success_metric')}",
        "",
        "## Execution Principles",
    ]
    for item in _string_list(prompt_bundle.get("execution_principles")):
        lines.append(f"- {item}")
    lines.extend(["", "## Musk Questions"])
    for item in _string_list(prompt_bundle.get("musk_questions")):
        lines.append(f"- {item}")
    lines.extend(["", "## Founder Questions"])
    for item in _string_list(prompt_bundle.get("founder_questions")):
        lines.append(f"- {item}")
    lines.extend(["", "## Anti Patterns"])
    for item in _string_list(prompt_bundle.get("anti_patterns")):
        lines.append(f"- {item}")
    lines.extend(["", "## Parallel Brainstorm Filters"])
    for item in _string_list(prompt_bundle.get("parallel_brainstorm_filters")):
        lines.append(f"- {item}")
    lines.extend(["", "## Decision Ladder Preview"])
    for row in _safe_list(prompt_bundle.get("decision_ladder_preview")):
        item = _safe_dict(row)
        lines.append(
            f"- {item.get('review_reason')} / inspect_first={item.get('inspect_first')} / next_action={item.get('next_action')} / manual_review_gate={item.get('manual_review_gate')}"
        )
    lines.extend(["", "## Operator Jump Preview"])
    for row in _safe_list(prompt_bundle.get("operator_jump_preview")):
        item = _safe_dict(row)
        preset_ids = ", ".join(_string_list(item.get("representative_preset_ids")))
        lines.append(
            f"- {item.get('claim_id')} / {item.get('family_key')} / jump_target_total={item.get('jump_target_total')} / presets={preset_ids}"
        )
    lines.extend([
        "",
        "## Prompt Sections",
    ])
    for item in _string_list(prompt_bundle.get("prompt_sections")):
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Targets"])
    for item in _string_list(payload.get("verification_targets")):
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the canonical permit thinking prompt bundle packet.")
    parser.add_argument("--brainstorm", type=Path, default=DEFAULT_BRAINSTORM)
    parser.add_argument("--founder", type=Path, default=DEFAULT_FOUNDER)
    parser.add_argument("--copy", type=Path, default=DEFAULT_COPY)
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--alignment", type=Path, default=DEFAULT_ALIGNMENT)
    parser.add_argument("--public-contract", type=Path, default=DEFAULT_PUBLIC_CONTRACT)
    parser.add_argument("--case-binding", type=Path, default=DEFAULT_CASE_BINDING)
    parser.add_argument("--critical-prompt", type=Path, default=DEFAULT_CRITICAL_PROMPT)
    parser.add_argument("--partner-binding", type=Path, default=DEFAULT_PARTNER_BINDING)
    parser.add_argument("--review-reason", type=Path, default=DEFAULT_REVIEW_REASON)
    parser.add_argument("--system-split", type=Path, default=DEFAULT_SYSTEM_SPLIT)
    parser.add_argument("--prompt-doc", type=Path, default=DEFAULT_PROMPT_DOC)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        brainstorm_path=args.brainstorm,
        founder_path=args.founder,
        copy_path=args.copy,
        ux_path=args.ux,
        alignment_path=args.alignment,
        public_contract_path=args.public_contract,
        case_binding_path=args.case_binding,
        critical_prompt_path=args.critical_prompt,
        partner_binding_path=args.partner_binding,
        review_reason_path=args.review_reason,
        system_split_path=args.system_split,
        prompt_doc_path=args.prompt_doc,
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
