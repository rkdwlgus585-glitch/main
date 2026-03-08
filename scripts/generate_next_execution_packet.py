#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOCUS = ROOT / "logs" / "next_batch_focus_packet_latest.json"
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_SYSTEM_SPLIT = ROOT / "logs" / "system_split_first_principles_packet_latest.json"
DEFAULT_YANGDO_ZERO = ROOT / "logs" / "yangdo_zero_display_recovery_audit_latest.json"
DEFAULT_YANGDO_COPY = ROOT / "logs" / "yangdo_service_copy_packet_latest.json"
DEFAULT_YANGDO_SPECIAL_SECTOR = ROOT / "logs" / "yangdo_special_sector_packet_latest.json"
DEFAULT_PERMIT_ALIGNMENT = ROOT / "logs" / "permit_service_alignment_audit_latest.json"
DEFAULT_PERMIT_CRITICAL_PROMPT = ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.json"
DEFAULT_PERMIT_PARTNER_BINDING = ROOT / "logs" / "permit_partner_binding_parity_packet_latest.json"
DEFAULT_PERMIT_PARTNER_BINDING_OBSERVABILITY = ROOT / "logs" / "permit_partner_binding_observability_latest.json"
DEFAULT_PERMIT_THINKING_PROMPT_BUNDLE = ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.json"
DEFAULT_PARTNER_FLOW = ROOT / "logs" / "partner_input_operator_flow_latest.json"
DEFAULT_PLATFORM = ROOT / "logs" / "ai_platform_first_principles_review_latest.json"
DEFAULT_FOUNDER_BUNDLE = ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"
DEFAULT_JSON = ROOT / "logs" / "next_execution_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "next_execution_packet_latest.md"


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


def _artifact(path: Path) -> Dict[str, str]:
    return {"path": str(path.resolve()), "name": path.name}


def _clean_string_list(value: Any) -> List[str]:
    out: List[str] = []
    for item in _safe_list(value):
        text = _safe_str(item)
        if text and text not in out:
            out.append(text)
    return out


def _build_founder_contract(
    *,
    founder_bundle: Dict[str, Any],
    selected_track: str,
    selected_lane_id: str,
) -> Dict[str, Any]:
    summary = _safe_dict(founder_bundle.get("summary"))
    primary_system = _safe_str(summary.get("primary_system"))
    primary_lane_id = _safe_str(summary.get("primary_lane_id"))
    parallel_system = _safe_str(summary.get("parallel_system"))
    parallel_lane_id = _safe_str(summary.get("parallel_lane_id"))
    return {
        "primary_system": primary_system,
        "primary_lane_id": primary_lane_id,
        "parallel_system": parallel_system,
        "parallel_lane_id": parallel_lane_id,
        "selected_matches_primary": bool(
            primary_system
            and primary_lane_id
            and selected_track == primary_system
            and selected_lane_id == primary_lane_id
        ),
        "execution_checklist": _clean_string_list(founder_bundle.get("execution_checklist")),
        "shipping_gates": _clean_string_list(founder_bundle.get("shipping_gates")),
    }


def _build_parallel_execution(
    *,
    focus: Dict[str, Any],
    founder_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    parallel_candidates = _safe_list(focus.get("parallel_candidates"))
    selected_parallel = _safe_dict(parallel_candidates[0]) if parallel_candidates else {}
    founder_summary = _safe_dict(founder_bundle.get("summary"))
    founder_parallel_track = _safe_str(founder_summary.get("parallel_system"))
    founder_parallel_lane_id = _safe_str(founder_summary.get("parallel_lane_id"))
    track = _safe_str(selected_parallel.get("track"))
    lane_id = _safe_str(selected_parallel.get("lane_id"))
    return {
        "track": track,
        "lane_id": lane_id,
        "title": _safe_str(selected_parallel.get("title")),
        "actionability": _safe_str(selected_parallel.get("actionability")),
        "reason": _safe_str(selected_parallel.get("reason")),
        "next_move": _safe_str(selected_parallel.get("next_move")),
        "matches_founder_parallel": bool(
            track
            and lane_id
            and track == founder_parallel_track
            and lane_id == founder_parallel_lane_id
        ),
    }


def _build_yangdo_zero_display_plan(
    *,
    selected: Dict[str, Any],
    zero_audit: Dict[str, Any],
    yangdo_copy: Dict[str, Any],
    focus_path: Path,
    zero_audit_path: Path,
    yangdo_copy_path: Path,
) -> Dict[str, Any]:
    zero_summary = _safe_dict(zero_audit.get("summary"))
    copy_summary = _safe_dict(yangdo_copy.get("summary"))
    ready = bool(zero_summary.get("zero_display_guard_ok")) and bool(copy_summary.get("packet_ready"))
    return {
        "execution_ready": ready,
        "bottleneck": "추천 0건 fallback 계약을 공개/상담/시장 브리지 순서로 고정",
        "evidence_points": [
            f"selected_lane_ok={zero_summary.get('selected_lane_ok')}",
            f"zero_display_total={zero_summary.get('zero_display_total')}",
            f"market_bridge_route_ok={zero_summary.get('market_bridge_route_ok')}",
            f"consult_first_ready={zero_summary.get('consult_first_ready')}",
            f"zero_policy_ready={zero_summary.get('zero_policy_ready')}",
        ],
        "success_criteria": [
            "yangdo_zero_display_guard_ok == true",
            "selected lane remains zero_display_recovery_guard",
            "service copy keeps input recovery -> market bridge -> consult ordering",
            "public summary stays safe while consult lane remains available",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_yangdo_service_copy_packet.py",
            "py -3 H:\\auto\\scripts\\generate_yangdo_zero_display_recovery_audit.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(zero_audit_path),
            _artifact(yangdo_copy_path),
        ],
        "next_after_completion": [
            "detail_explainable 단독 업셀 lane의 상품/카피/운영 차등을 더 독립화",
            "추천 집중도 3차에서 top-2/3 반복도와 focus signature 편향을 강화",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_yangdo_special_sector_plan(
    *,
    selected: Dict[str, Any],
    special_sector_packet: Dict[str, Any],
    yangdo_copy: Dict[str, Any],
    focus_path: Path,
    special_sector_path: Path,
    yangdo_copy_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(special_sector_packet.get("summary"))
    sectors = _safe_list(special_sector_packet.get("sectors"))
    telecom = next(
        (
            row for row in sectors
            if isinstance(row, dict)
            and (
                _safe_str(row.get("sector")) == "정보통신"
                or "정보통신" in _clean_string_list(row.get("aliases"))
            )
        ),
        {},
    )
    telecom_publication = _safe_dict(_safe_dict(telecom).get("publication_metrics"))
    copy_summary = _safe_dict(yangdo_copy.get("summary"))
    return {
        "execution_ready": bool(summary.get("precision_green"))
        and bool(summary.get("diversity_green"))
        and bool(summary.get("contract_green"))
        and bool(copy_summary.get("packet_ready")),
        "bottleneck": "정보통신 업종군의 공개 안전도를 더 보수적으로 잠가서 sector 정밀도와 공개계약이 같은 방향을 보이게 만든다.",
        "evidence_points": [
            f"packet_ready={summary.get('packet_ready')}",
            f"publication_safety_ok={summary.get('publication_safety_ok')}",
            f"telecom_publication_safety_ok={telecom_publication.get('publication_safety_ok')}",
            f"telecom_full_count={telecom_publication.get('full_count')}",
            f"telecom_full_share={telecom_publication.get('full_share')}",
            f"precision_green={summary.get('precision_green')}",
            f"diversity_green={summary.get('diversity_green')}",
            f"contract_green={summary.get('contract_green')}",
        ],
        "success_criteria": [
            "yangdo_special_sector_publication_safe == true",
            "telecom full publication share falls below the sector threshold",
            "telecom full publication count stops increasing on the public tier",
            "service copy keeps market-fit explanation while sector 공개정책 remains conservative",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_yangdo_recommendation_contract_audit.py",
            "py -3 H:\\auto\\scripts\\generate_yangdo_special_sector_packet.py",
            "py -3 H:\\auto\\scripts\\generate_yangdo_next_action_brainstorm.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(special_sector_path),
            _artifact(yangdo_copy_path),
        ],
        "next_after_completion": [
            "Return to market-fit explainability once telecom publication safety no longer blocks public release confidence.",
            "Expand sector-specific publication policy into recommendation contract audit if telecom remains the highest-risk family.",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_permit_plan(
    *,
    selected: Dict[str, Any],
    permit_alignment: Dict[str, Any],
    permit_critical_prompt: Dict[str, Any],
    permit_partner_binding: Dict[str, Any],
    focus_path: Path,
    permit_alignment_path: Path,
    permit_critical_prompt_path: Path,
    permit_partner_binding_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(permit_alignment.get("summary"))
    critical_prompt_summary = _safe_dict(permit_critical_prompt.get("summary"))
    partner_binding_summary = _safe_dict(permit_partner_binding.get("summary"))
    selected_lane_id = _safe_str(selected.get("lane_id"))

    if selected_lane_id == "review_reason_decision_ladder":
        ready = bool(summary.get("alignment_ok")) and bool(summary.get("service_story_ok")) and bool(
            summary.get("lane_positioning_ok")
        )
        return {
            "execution_ready": ready,
            "bottleneck": "permit service copy must compress review reasons into a clearer detail-checklist versus manual-review decision ladder.",
            "evidence_points": [
                f"alignment_ok={summary.get('alignment_ok')}",
                f"service_story_ok={summary.get('service_story_ok')}",
                f"lane_positioning_ok={summary.get('lane_positioning_ok')}",
                f"permit_offering_count={summary.get('permit_offering_count')}",
            ],
            "success_criteria": [
                "permit_service_alignment_ok == true",
                "permit_service_copy_ready == true",
                "permit_service_ux_ready == true",
                "detail_checklist and manual_review_assist CTA language must diverge clearly",
            ],
            "verification_commands": [
                "py -3 H:\\auto\\scripts\\generate_permit_service_copy_packet.py",
                "py -3 H:\\auto\\scripts\\generate_permit_service_ux_packet.py",
                "py -3 H:\\auto\\scripts\\generate_permit_service_alignment_audit.py",
                "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
            ],
            "artifacts": [
                _artifact(focus_path),
                _artifact(permit_alignment_path),
            ],
            "next_after_completion": [
                "Advance permit rental packaging so checklist detail and manual-review assist become cleaner partner upsell lanes.",
            ],
            "selected_focus": {
                "track": _safe_str(selected.get("track")),
                "lane_id": selected_lane_id,
                "title": _safe_str(selected.get("title")),
                "execution_prompt": _safe_str(selected.get("execution_prompt")),
                "next_move": _safe_str(selected.get("next_move")),
            },
        }

    ready = (
        bool(summary.get("alignment_ok"))
        and bool(critical_prompt_summary.get("packet_ready"))
        and bool(partner_binding_summary.get("packet_ready"))
    )
    return {
        "execution_ready": ready,
        "bottleneck": "permit service copy and release surfaces must expose the founder primary lane without operator lookup.",
        "evidence_points": [
            f"alignment_ok={summary.get('alignment_ok')}",
            f"critical_prompt_surface_ready={critical_prompt_summary.get('packet_ready')}",
            f"prompt_case_binding_ready={critical_prompt_summary.get('prompt_case_binding_ready')}",
            f"partner_binding_parity_ready={partner_binding_summary.get('packet_ready')}",
            f"service_story_ok={summary.get('service_story_ok')}",
            f"lane_positioning_ok={summary.get('lane_positioning_ok')}",
        ],
        "success_criteria": [
            "permit_service_alignment_ok == true",
            "permit_critical_prompt_surface_ready == true",
            "permit_prompt_case_binding_ready == true",
            "permit_partner_binding_parity_ready == true",
            "summary_self_check / detail_checklist / manual_review_assist differences stay explicit",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_permit_service_copy_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_critical_prompt_surface_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_partner_binding_parity_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_service_alignment_audit.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(permit_alignment_path),
            _artifact(permit_critical_prompt_path),
            _artifact(permit_partner_binding_path),
        ],
        "next_after_completion": [
            "Split permit rental tiers into sharper partner pricing and copy ladders.",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_permit_thinking_prompt_bundle_plan(
    *,
    selected: Dict[str, Any],
    permit_thinking_prompt_bundle: Dict[str, Any],
    focus_path: Path,
    permit_thinking_prompt_bundle_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(permit_thinking_prompt_bundle.get("summary"))
    prompt_bundle = _safe_dict(permit_thinking_prompt_bundle.get("prompt_bundle"))
    return {
        "execution_ready": bool(summary.get("packet_ready")),
        "bottleneck": (
            "permit reasoning still drifts unless runtime, release, and operator surfaces share one canonical thinking bundle."
        ),
        "evidence_points": [
            f"packet_ready={summary.get('packet_ready')}",
            f"service_copy_ready={summary.get('service_copy_ready')}",
            f"service_ux_ready={summary.get('service_ux_ready')}",
            f"alignment_ok={summary.get('alignment_ok')}",
            f"public_contract_ok={summary.get('public_contract_ok')}",
            f"review_reason_ready={summary.get('review_reason_ready')}",
            f"prompt_case_binding_ready={summary.get('prompt_case_binding_ready')}",
            f"critical_prompt_ready={summary.get('critical_prompt_ready')}",
            f"partner_binding_ready={summary.get('partner_binding_ready')}",
            f"runtime_target_ready={summary.get('runtime_target_ready')}",
            f"release_target_ready={summary.get('release_target_ready')}",
            f"operator_target_ready={summary.get('operator_target_ready')}",
            f"founder_transition_context_ready={summary.get('founder_transition_context_ready')}",
        ],
        "success_criteria": _clean_string_list(permit_thinking_prompt_bundle.get("verification_targets")),
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_permit_service_copy_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_service_ux_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_service_alignment_audit.py",
            "py -3 H:\\auto\\scripts\\generate_permit_public_contract_audit.py",
            "py -3 H:\\auto\\scripts\\generate_permit_review_reason_decision_ladder.py",
            "py -3 H:\\auto\\scripts\\generate_permit_prompt_case_binding_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_critical_prompt_surface_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_partner_binding_parity_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_thinking_prompt_bundle_packet.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(permit_thinking_prompt_bundle_path),
        ],
        "next_after_completion": [
            "Use the unified permit thinking bundle as the fixed contract for runtime, release, and operator prioritization.",
            "Keep partner binding observability in parallel-brainstorm mode until the permit thinking bundle stays green without manual interpretation.",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt") or prompt_bundle.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move") or prompt_bundle.get("proposed_next_step")),
        },
    }


def _build_permit_partner_binding_observability_plan(
    *,
    selected: Dict[str, Any],
    permit_partner_binding_observability: Dict[str, Any],
    focus_path: Path,
    permit_partner_binding_observability_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(permit_partner_binding_observability.get("summary"))
    return {
        "execution_ready": bool(summary.get("observability_ready")),
        "bottleneck": (
            "partner-safe binding coverage must be readable from release and contract surfaces without opening raw widget or API JSON."
        ),
        "evidence_points": [
            f"parity_packet_ready={summary.get('parity_packet_ready')}",
            f"expected_family_total={summary.get('expected_family_total')}",
            f"operator_binding_family_total={summary.get('operator_binding_family_total')}",
            f"widget_binding_family_total={summary.get('widget_binding_family_total')}",
            f"api_binding_family_total={summary.get('api_binding_family_total')}",
            f"partner_binding_surface_ready={summary.get('partner_binding_surface_ready')}",
            f"widget_missing_family_total={summary.get('widget_missing_family_total')}",
            f"api_missing_family_total={summary.get('api_missing_family_total')}",
            f"widget_extra_family_total={summary.get('widget_extra_family_total')}",
            f"api_extra_family_total={summary.get('api_extra_family_total')}",
        ],
        "success_criteria": [
            "permit_partner_binding_observability_ready == true",
            "permit_partner_binding_surface_ready == true",
            "widget_missing_family_total == 0",
            "api_missing_family_total == 0",
            "widget_extra_family_total == 0",
            "api_extra_family_total == 0",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_permit_partner_binding_parity_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_partner_binding_observability.py",
            "py -3 H:\\auto\\scripts\\generate_permit_next_action_brainstorm.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(permit_partner_binding_observability_path),
        ],
        "next_after_completion": [
            "Promote permit reasoning into a single runtime reasoning card once partner binding coverage stays readable without operator lookup.",
            "Keep partner-safe lane distinctions explicit while tightening release and contract summaries.",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_platform_plan(
    *,
    selected: Dict[str, Any],
    platform_review: Dict[str, Any],
    focus_path: Path,
    platform_review_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(platform_review.get("summary"))
    return {
        "execution_ready": bool(summary.get("packet_ready")),
        "bottleneck": "public/private publish 분기와 post-publish verifier 단일화",
        "evidence_points": [
            f"packet_ready={summary.get('packet_ready')}",
            f"current_bottleneck={summary.get('current_bottleneck')}",
        ],
        "success_criteria": [
            "publish gate 단일화",
            "post-publish verifier를 운영 패킷에서 직접 읽을 수 있을 것",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_ai_platform_first_principles_review.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(platform_review_path),
        ],
        "next_after_completion": [
            "live 승인 이후 publish/rollback operator flow를 더 줄인다",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_partner_plan(
    *,
    selected: Dict[str, Any],
    partner_flow: Dict[str, Any],
    focus_path: Path,
    partner_flow_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(partner_flow.get("summary"))
    return {
        "execution_ready": bool(summary.get("packet_ready")),
        "bottleneck": "partner 입력 3종을 주입하고 activation까지 닫기",
        "evidence_points": [
            f"packet_ready={summary.get('packet_ready')}",
            f"copy_paste_ready={summary.get('copy_paste_ready')}",
        ],
        "success_criteria": [
            "proof_url / api_key / approval 주입 후 dry-run과 apply 흐름이 모두 통과",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_partner_input_handoff_packet.py",
            "py -3 H:\\auto\\scripts\\generate_partner_input_operator_flow.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(partner_flow_path),
        ],
        "next_after_completion": [
            "partner별 proof/source/AP key 실입력을 받아 activation을 닫는다",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def build_packet(
    *,
    focus_path: Path,
    operations_path: Path,
    system_split_path: Path,
    yangdo_zero_path: Path,
    yangdo_copy_path: Path,
    permit_alignment_path: Path,
    permit_critical_prompt_path: Path,
    permit_partner_binding_path: Path,
    permit_thinking_prompt_bundle_path: Path,
    partner_flow_path: Path,
    platform_review_path: Path,
    founder_bundle_path: Path,
    permit_partner_binding_observability_path: Path | None = None,
    yangdo_special_sector_path: Path | None = None,
) -> Dict[str, Any]:
    focus = _load_json(focus_path)
    operations = _load_json(operations_path)
    system_split = _load_json(system_split_path)
    yangdo_zero = _load_json(yangdo_zero_path)
    yangdo_copy = _load_json(yangdo_copy_path)
    yangdo_special_sector = _load_json(yangdo_special_sector_path or DEFAULT_YANGDO_SPECIAL_SECTOR)
    permit_alignment = _load_json(permit_alignment_path)
    permit_critical_prompt = _load_json(permit_critical_prompt_path)
    permit_partner_binding = _load_json(permit_partner_binding_path)
    permit_partner_binding_observability = _load_json(
        permit_partner_binding_observability_path or DEFAULT_PERMIT_PARTNER_BINDING_OBSERVABILITY
    )
    permit_thinking_prompt_bundle = _load_json(permit_thinking_prompt_bundle_path)
    partner_flow = _load_json(partner_flow_path)
    platform_review = _load_json(platform_review_path)
    founder_bundle = _load_json(founder_bundle_path)

    summary = _safe_dict(focus.get("summary"))
    selected = _safe_dict(focus.get("selected_focus"))
    selected_track = _safe_str(summary.get("selected_track") or selected.get("track"))
    selected_lane_id = _safe_str(summary.get("selected_lane_id") or selected.get("lane_id"))
    split_tracks = _safe_dict(system_split.get("tracks"))
    track_packet = _safe_dict(split_tracks.get(selected_track))
    selected_ready = bool(summary.get("packet_ready")) and bool(selected_track)

    if selected_track == "yangdo":
        if selected_lane_id == "special_sector_publication_guard":
            execution = _build_yangdo_special_sector_plan(
                selected=selected,
                special_sector_packet=yangdo_special_sector,
                yangdo_copy=yangdo_copy,
                focus_path=focus_path,
                special_sector_path=(yangdo_special_sector_path or DEFAULT_YANGDO_SPECIAL_SECTOR),
                yangdo_copy_path=yangdo_copy_path,
            )
        else:
            execution = _build_yangdo_zero_display_plan(
                selected=selected,
                zero_audit=yangdo_zero,
                yangdo_copy=yangdo_copy,
                focus_path=focus_path,
                zero_audit_path=yangdo_zero_path,
                yangdo_copy_path=yangdo_copy_path,
            )
    elif selected_track == "permit":
        if selected_lane_id == "thinking_prompt_bundle_lock":
            execution = _build_permit_thinking_prompt_bundle_plan(
                selected=selected,
                permit_thinking_prompt_bundle=permit_thinking_prompt_bundle,
                focus_path=focus_path,
                permit_thinking_prompt_bundle_path=permit_thinking_prompt_bundle_path,
            )
        elif selected_lane_id == "partner_binding_observability":
            execution = _build_permit_partner_binding_observability_plan(
                selected=selected,
                permit_partner_binding_observability=permit_partner_binding_observability,
                focus_path=focus_path,
                permit_partner_binding_observability_path=(
                    permit_partner_binding_observability_path or DEFAULT_PERMIT_PARTNER_BINDING_OBSERVABILITY
                ),
            )
        else:
            execution = _build_permit_plan(
                selected=selected,
                permit_alignment=permit_alignment,
                permit_critical_prompt=permit_critical_prompt,
                permit_partner_binding=permit_partner_binding,
                focus_path=focus_path,
                permit_alignment_path=permit_alignment_path,
                permit_critical_prompt_path=permit_critical_prompt_path,
                permit_partner_binding_path=permit_partner_binding_path,
            )
    elif selected_track == "partner":
        execution = _build_partner_plan(
            selected=selected,
            partner_flow=partner_flow,
            focus_path=focus_path,
            partner_flow_path=partner_flow_path,
        )
    else:
        execution = _build_platform_plan(
            selected=selected,
            platform_review=platform_review,
            focus_path=focus_path,
            platform_review_path=platform_review_path,
        )

    decisions = _safe_dict(operations.get("decisions"))
    founder_contract = _build_founder_contract(
        founder_bundle=founder_bundle,
        selected_track=selected_track,
        selected_lane_id=selected_lane_id,
    )
    parallel_execution = _build_parallel_execution(
        focus=focus,
        founder_bundle=founder_bundle,
    )
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "packet_ready": selected_ready,
            "selected_track": selected_track,
            "selected_lane_id": selected_lane_id,
            "execution_ready": bool(execution.get("execution_ready")),
            "deferred_candidate_count": len(_safe_list(focus.get("deferred_candidates"))),
            "founder_selected_matches_primary": bool(founder_contract.get("selected_matches_primary")),
            "parallel_track": _safe_str(parallel_execution.get("track")),
            "parallel_lane_id": _safe_str(parallel_execution.get("lane_id")),
            "parallel_matches_founder": bool(parallel_execution.get("matches_founder_parallel")),
        },
        "selected_execution": execution,
        "parallel_execution": parallel_execution,
        "founder_mode": founder_contract,
        "context": {
            "seoul_live_decision": _safe_str(decisions.get("seoul_live_decision")),
            "partner_activation_decision": _safe_str(decisions.get("partner_activation_decision")),
            "track_goal": _safe_str(track_packet.get("goal")),
            "track_current_bottleneck": _safe_str(track_packet.get("current_bottleneck")),
            "parallel_candidates": _safe_list(focus.get("parallel_candidates")),
        },
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    selected_execution = _safe_dict(payload.get("selected_execution"))
    parallel_execution = _safe_dict(payload.get("parallel_execution"))
    founder_mode = _safe_dict(payload.get("founder_mode"))
    context = _safe_dict(payload.get("context"))
    lines = [
        "# Next Execution Packet",
        "",
        f"- packet_ready: `{summary.get('packet_ready')}`",
        f"- selected_track: `{summary.get('selected_track')}`",
        f"- selected_lane_id: `{summary.get('selected_lane_id')}`",
        f"- execution_ready: `{summary.get('execution_ready')}`",
        f"- founder_selected_matches_primary: `{summary.get('founder_selected_matches_primary')}`",
        f"- parallel_track: `{summary.get('parallel_track')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id')}`",
        f"- parallel_matches_founder: `{summary.get('parallel_matches_founder')}`",
        "",
        "## Execution",
        f"- bottleneck: {selected_execution.get('bottleneck')}",
        f"- title: {(_safe_dict(selected_execution.get('selected_focus'))).get('title', '')}",
        f"- next_move: {(_safe_dict(selected_execution.get('selected_focus'))).get('next_move', '')}",
        "",
        "## Parallel Execution",
        f"- track: `{parallel_execution.get('track', '')}`",
        f"- lane_id: `{parallel_execution.get('lane_id', '')}`",
        f"- title: {parallel_execution.get('title', '')}",
        f"- actionability: `{parallel_execution.get('actionability', '')}`",
        f"- next_move: {parallel_execution.get('next_move', '')}",
        f"- matches_founder_parallel: `{parallel_execution.get('matches_founder_parallel')}`",
        "",
        "## Evidence",
    ]
    for item in _safe_list(selected_execution.get("evidence_points")):
        lines.append(f"- {item}")
    lines.extend(["", "## Success Criteria"])
    for item in _safe_list(selected_execution.get("success_criteria")):
        lines.append(f"- {item}")
    lines.extend(["", "## Founder Contract"])
    lines.append(
        f"- primary_lane: `{founder_mode.get('primary_system', '')}/{founder_mode.get('primary_lane_id', '')}`"
    )
    lines.append(
        f"- parallel_lane: `{founder_mode.get('parallel_system', '')}/{founder_mode.get('parallel_lane_id', '')}`"
    )
    lines.append(f"- selected_matches_primary: `{founder_mode.get('selected_matches_primary')}`")
    lines.extend(["", "## Founder Checklist"])
    for item in _safe_list(founder_mode.get("execution_checklist")):
        lines.append(f"- {item}")
    lines.extend(["", "## Founder Shipping Gates"])
    for item in _safe_list(founder_mode.get("shipping_gates")):
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Commands"])
    for item in _safe_list(selected_execution.get("verification_commands")):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Context"])
    lines.append(f"- seoul_live_decision: {context.get('seoul_live_decision')}")
    lines.append(f"- partner_activation_decision: {context.get('partner_activation_decision')}")
    lines.append(f"- track_goal: {context.get('track_goal')}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the concrete next execution packet from the selected batch focus.")
    parser.add_argument("--focus", type=Path, default=DEFAULT_FOCUS)
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--system-split", type=Path, default=DEFAULT_SYSTEM_SPLIT)
    parser.add_argument("--yangdo-zero", type=Path, default=DEFAULT_YANGDO_ZERO)
    parser.add_argument("--yangdo-copy", type=Path, default=DEFAULT_YANGDO_COPY)
    parser.add_argument("--yangdo-special-sector", type=Path, default=DEFAULT_YANGDO_SPECIAL_SECTOR)
    parser.add_argument("--permit-alignment", type=Path, default=DEFAULT_PERMIT_ALIGNMENT)
    parser.add_argument("--permit-critical-prompt", type=Path, default=DEFAULT_PERMIT_CRITICAL_PROMPT)
    parser.add_argument("--permit-partner-binding", type=Path, default=DEFAULT_PERMIT_PARTNER_BINDING)
    parser.add_argument(
        "--permit-partner-binding-observability",
        type=Path,
        default=DEFAULT_PERMIT_PARTNER_BINDING_OBSERVABILITY,
    )
    parser.add_argument("--permit-thinking-prompt-bundle", type=Path, default=DEFAULT_PERMIT_THINKING_PROMPT_BUNDLE)
    parser.add_argument("--partner-flow", type=Path, default=DEFAULT_PARTNER_FLOW)
    parser.add_argument("--platform-review", type=Path, default=DEFAULT_PLATFORM)
    parser.add_argument("--founder-bundle", type=Path, default=DEFAULT_FOUNDER_BUNDLE)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        focus_path=args.focus,
        operations_path=args.operations,
        system_split_path=args.system_split,
        yangdo_zero_path=args.yangdo_zero,
        yangdo_copy_path=args.yangdo_copy,
        yangdo_special_sector_path=args.yangdo_special_sector,
        permit_alignment_path=args.permit_alignment,
        permit_critical_prompt_path=args.permit_critical_prompt,
        permit_partner_binding_path=args.permit_partner_binding,
        permit_partner_binding_observability_path=args.permit_partner_binding_observability,
        permit_thinking_prompt_bundle_path=args.permit_thinking_prompt_bundle,
        partner_flow_path=args.partner_flow,
        platform_review_path=args.platform_review,
        founder_bundle_path=args.founder_bundle,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
