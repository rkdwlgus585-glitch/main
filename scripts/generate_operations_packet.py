#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_INPUT_METADATA: Dict[str, Dict[str, str]] = {
    "confirm_live_yes": {
        "label": "Live release confirmation",
        "description": "Run deploy_seoul_widget_embed_release.py with --confirm-live YES.",
        "owner": "operator",
    },
    "partner_proof_url": {
        "label": "Partner contract proof URL",
        "description": "Populate proof_url on the partner_contract data source.",
        "owner": "business",
    },
    "partner_api_key": {
        "label": "Partner API key",
        "description": "Issue the TENANT_API_KEY_* secret and inject it into the environment.",
        "owner": "operator",
    },
    "partner_data_source_approval": {
        "label": "Partner data source approval",
        "description": "Mark the partner data source as approved and allowed for commercial use.",
        "owner": "business",
    },
    "partner_live_smoke_retry": {
        "label": "Partner live smoke retry",
        "description": "Retry live smoke against the verified engine/base URL.",
        "owner": "operator",
    },
}

MOJIBAKE_HINTS = (
    "\ufffd",
    "\\ufffd",
    "???",
    "?",
    "??",
    "??",
    "??",
    "???",
    "??????",
)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _looks_mojibake(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    return any(token in value for token in MOJIBAKE_HINTS)


def _sanitize_action(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    lower = value.lower()
    if "confirm_live" in lower or "--confirm-live" in lower:
        return "Run deploy_seoul_widget_embed_release.py with --confirm-live YES"
    if lower.startswith("release orchestration"):
        return "Release orchestration is ready to run"
    if _looks_mojibake(value):
        return "Review release orchestration output and rerun if needed"
    return value


def _normalize_blocker(text: str) -> str:
    src = str(text or "").strip()
    lower = src.lower()
    if not src:
        return ""
    if "confirm_live_missing" in lower:
        return "release_confirmation_required"
    if "missing_source_proof_url" in lower:
        return "partner_proof_url_missing"
    if "missing_api_key" in lower or "disabled_missing_api_key" in lower:
        return "partner_api_key_missing"
    if "commercial_use_not_allowed" in lower:
        return "partner_commercial_use_not_allowed"
    if "missing_approved_data_source" in lower or "non_approved_source_in_enabled_tenant" in lower:
        return "partner_data_source_not_approved"
    if "smoke_failed" in lower:
        return "partner_smoke_failed"
    return src


def _required_inputs_from_blockers(blockers: List[str]) -> List[str]:
    out: List[str] = []
    for item in blockers or []:
        key = _normalize_blocker(item)
        if key == "release_confirmation_required":
            label = "confirm_live_yes"
        elif key == "partner_proof_url_missing":
            label = "partner_proof_url"
        elif key == "partner_api_key_missing":
            label = "partner_api_key"
        elif key in {"partner_data_source_not_approved", "partner_commercial_use_not_allowed"}:
            label = "partner_data_source_approval"
        elif key == "partner_smoke_failed":
            label = "partner_live_smoke_retry"
        else:
            continue
        if label not in out:
            out.append(label)
    return out


def _dedupe_blockers(items: List[str]) -> List[str]:
    out: List[str] = []
    for item in items or []:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _normalize_next_actions(blockers: List[str], actions: List[str]) -> List[str]:
    out: List[str] = []
    for item in actions or []:
        cleaned = _sanitize_action(item)
        if cleaned and cleaned not in out:
            out.append(cleaned)
    required_inputs = _required_inputs_from_blockers(blockers)
    if "confirm_live_yes" in required_inputs:
        action = "Run deploy_seoul_widget_embed_release.py with --confirm-live YES"
        if action not in out:
            out.insert(0, action)
    return out


def _decision_flags(*, quality_green: bool, release_ready: bool, release_report_ok: bool, blockers: List[str]) -> Dict[str, str]:
    blocker_set = set(blockers or [])
    if quality_green and release_ready and release_report_ok and not blocker_set:
        seoul = "ready"
    elif blocker_set == {"release_confirmation_required"}:
        seoul = "awaiting_live_confirmation"
    else:
        seoul = "blocked"
    return {"seoul_live_decision": seoul}


def _build_required_input_items(keys: List[str]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for key in keys or []:
        meta = REQUIRED_INPUT_METADATA.get(key, {})
        items.append(
            {
                "key": key,
                "label": str(meta.get("label") or key),
                "description": str(meta.get("description") or ""),
                "owner": str(meta.get("owner") or "operator"),
            }
        )
    return items


def _resolve_preview_alignment(*, partner_flow_path: Path | None, partner_preview_path: Path | None, partner_preview_alignment_path: Path | None) -> Dict[str, Any]:
    alignment = _load_json(partner_preview_alignment_path or Path())
    if isinstance(alignment.get("summary"), dict):
        return alignment
    if not partner_flow_path or not partner_preview_path:
        return alignment
    try:
        from scripts.verify_partner_preview_alignment import build_alignment
    except Exception:
        return alignment
    return build_alignment(partner_flow_path=partner_flow_path, partner_preview_path=partner_preview_path)


def build_operations_packet(
    *,
    readiness_path: Path,
    release_path: Path,
    risk_map_path: Path,
    attorney_path: Path,
    platform_front_audit_path: Path | None = None,
    surface_stack_audit_path: Path | None = None,
    private_engine_proxy_spec_path: Path | None = None,
    wp_surface_lab_path: Path | None = None,
    wp_surface_lab_runtime_path: Path | None = None,
    wp_surface_lab_runtime_validation_path: Path | None = None,
    wp_surface_lab_php_runtime_path: Path | None = None,
    wp_surface_lab_php_fallback_path: Path | None = None,
    wp_platform_assets_path: Path | None = None,
    wordpress_platform_ia_path: Path | None = None,
    wp_platform_blueprints_path: Path | None = None,
    wordpress_staging_apply_plan_path: Path | None = None,
    wp_surface_lab_apply_path: Path | None = None,
    wp_surface_lab_apply_verify_cycle_path: Path | None = None,
    wp_surface_lab_page_verify_path: Path | None = None,
    wordpress_platform_encoding_audit_path: Path | None = None,
    wordpress_platform_ux_audit_path: Path | None = None,
    wordpress_platform_strategy_path: Path | None = None,
    astra_design_reference_path: Path | None = None,
    kr_reverse_proxy_cutover_path: Path | None = None,
    kr_traffic_gate_audit_path: Path | None = None,
    kr_deploy_readiness_path: Path | None = None,
    kr_preview_deploy_path: Path | None = None,
    onboarding_validation_path: Path | None = None,
    partner_flow_path: Path | None = None,
    partner_preview_path: Path | None = None,
    partner_preview_alignment_path: Path | None = None,
    partner_resolution_path: Path | None = None,
    partner_input_snapshot_path: Path | None = None,
    partner_simulation_matrix_path: Path | None = None,
    yangdo_recommendation_qa_path: Path | None = None,
    yangdo_recommendation_precision_matrix_path: Path | None = None,
    yangdo_recommendation_diversity_audit_path: Path | None = None,
    yangdo_recommendation_contract_audit_path: Path | None = None,
    yangdo_recommendation_bridge_packet_path: Path | None = None,
    yangdo_recommendation_ux_packet_path: Path | None = None,
    yangdo_recommendation_alignment_audit_path: Path | None = None,
    yangdo_zero_display_recovery_audit_path: Path | None = None,
    yangdo_service_copy_packet_path: Path | None = None,
    permit_service_copy_packet_path: Path | None = None,
    permit_service_alignment_audit_path: Path | None = None,
    permit_rental_lane_packet_path: Path | None = None,
    permit_service_ux_packet_path: Path | None = None,
    permit_public_contract_audit_path: Path | None = None,
    partner_input_handoff_packet_path: Path | None = None,
    partner_input_operator_flow_path: Path | None = None,
    widget_rental_catalog_path: Path | None = None,
    program_improvement_loop_path: Path | None = None,
    ai_platform_first_principles_review_path: Path | None = None,
    system_split_first_principles_packet_path: Path | None = None,
    next_batch_focus_packet_path: Path | None = None,
    next_execution_packet_path: Path | None = None,
    listing_platform_bridge_policy_path: Path | None = None,
    co_listing_bridge_snippets_path: Path | None = None,
    co_listing_bridge_operator_checklist_path: Path | None = None,
    co_listing_live_injection_plan_path: Path | None = None,
    co_listing_injection_bundle_path: Path | None = None,
    co_listing_bridge_apply_packet_path: Path | None = None,
    kr_proxy_server_matrix_path: Path | None = None,
    kr_proxy_server_bundle_path: Path | None = None,
    kr_live_apply_packet_path: Path | None = None,
    kr_live_operator_checklist_path: Path | None = None,
) -> Dict[str, Any]:
    readiness = _load_json(readiness_path)
    release = _load_json(release_path)
    risk_map = _load_json(risk_map_path)
    attorney = _load_json(attorney_path)
    platform_front_audit = _load_json(platform_front_audit_path or Path())
    surface_stack_audit = _load_json(surface_stack_audit_path or Path())
    private_engine_proxy_spec = _load_json(private_engine_proxy_spec_path or Path())
    wp_surface_lab = _load_json(wp_surface_lab_path or Path())
    wp_surface_lab_runtime = _load_json(wp_surface_lab_runtime_path or Path())
    wp_surface_lab_runtime_validation = _load_json(wp_surface_lab_runtime_validation_path or Path())
    wp_surface_lab_php_runtime = _load_json(wp_surface_lab_php_runtime_path or Path())
    wp_surface_lab_php_fallback = _load_json(wp_surface_lab_php_fallback_path or Path())
    wp_platform_assets = _load_json(wp_platform_assets_path or Path())
    wordpress_platform_ia = _load_json(wordpress_platform_ia_path or Path())
    wp_platform_blueprints = _load_json(wp_platform_blueprints_path or Path())
    wordpress_staging_apply_plan = _load_json(wordpress_staging_apply_plan_path or Path())
    wp_surface_lab_apply = _load_json(wp_surface_lab_apply_path or Path())
    wp_surface_lab_apply_verify_cycle = _load_json(wp_surface_lab_apply_verify_cycle_path or Path())
    wp_surface_lab_page_verify = _load_json(wp_surface_lab_page_verify_path or Path())
    wordpress_platform_encoding_audit = _load_json(wordpress_platform_encoding_audit_path or Path())
    wordpress_platform_ux_audit = _load_json(wordpress_platform_ux_audit_path or Path())
    wordpress_platform_strategy = _load_json(wordpress_platform_strategy_path or Path())
    astra_design_reference = _load_json(astra_design_reference_path or Path())
    kr_reverse_proxy_cutover = _load_json(kr_reverse_proxy_cutover_path or Path())
    kr_traffic_gate_audit = _load_json(kr_traffic_gate_audit_path or Path())
    kr_deploy_readiness = _load_json(kr_deploy_readiness_path or Path())
    kr_preview_deploy = _load_json(kr_preview_deploy_path or Path())
    onboarding_validation = _load_json(onboarding_validation_path or Path())
    partner_flow = _load_json(partner_flow_path or Path())
    partner_preview = _load_json(partner_preview_path or Path())
    partner_preview_alignment = _resolve_preview_alignment(
        partner_flow_path=partner_flow_path,
        partner_preview_path=partner_preview_path,
        partner_preview_alignment_path=partner_preview_alignment_path,
    )
    partner_resolution = _load_json(partner_resolution_path or Path())
    partner_input_snapshot = _load_json(partner_input_snapshot_path or Path())
    partner_simulation_matrix = _load_json(partner_simulation_matrix_path or Path())
    yangdo_recommendation_qa = _load_json(yangdo_recommendation_qa_path or Path())
    yangdo_recommendation_precision_matrix = _load_json(yangdo_recommendation_precision_matrix_path or Path())
    yangdo_recommendation_contract_audit = _load_json(yangdo_recommendation_contract_audit_path or Path())
    yangdo_recommendation_bridge_packet = _load_json(yangdo_recommendation_bridge_packet_path or Path())
    widget_rental_catalog = _load_json(widget_rental_catalog_path or Path())
    program_improvement_loop = _load_json(program_improvement_loop_path or Path())
    listing_platform_bridge_policy = _load_json(listing_platform_bridge_policy_path or Path())
    co_listing_bridge_snippets = _load_json(co_listing_bridge_snippets_path or Path())
    co_listing_bridge_operator_checklist = _load_json(co_listing_bridge_operator_checklist_path or Path())
    co_listing_live_injection_plan = _load_json(co_listing_live_injection_plan_path or Path())
    co_listing_injection_bundle = _load_json(co_listing_injection_bundle_path or Path())
    co_listing_bridge_apply_packet = _load_json(co_listing_bridge_apply_packet_path or Path())
    kr_proxy_server_matrix = _load_json(kr_proxy_server_matrix_path or Path())
    kr_proxy_server_bundle = _load_json(kr_proxy_server_bundle_path or Path())
    kr_live_apply_packet = _load_json(kr_live_apply_packet_path or Path())
    kr_live_operator_checklist = _load_json(kr_live_operator_checklist_path or Path())

    readiness_handoff = readiness.get("handoff") if isinstance(readiness.get("handoff"), dict) else {}
    release_handoff = release.get("handoff") if isinstance(release.get("handoff"), dict) else {}
    risk_summary = risk_map.get("run_summary") if isinstance(risk_map.get("run_summary"), dict) else {}
    exec_summary = attorney.get("executive_summary") if isinstance(attorney.get("executive_summary"), dict) else {}
    front_summary = (
        platform_front_audit.get("completion_summary")
        if isinstance(platform_front_audit.get("completion_summary"), dict)
        else {}
    )
    front_topology = platform_front_audit.get("front") if isinstance(platform_front_audit.get("front"), dict) else {}
    private_engine_proxy_topology = private_engine_proxy_spec.get("topology") if isinstance(private_engine_proxy_spec.get("topology"), dict) else {}
    private_engine_proxy_decision = private_engine_proxy_spec.get("decision") if isinstance(private_engine_proxy_spec.get("decision"), dict) else {}
    surface_decisions = surface_stack_audit.get("decisions") if isinstance(surface_stack_audit.get("decisions"), dict) else {}
    surface_wordpress = surface_stack_audit.get("wordpress") if isinstance(surface_stack_audit.get("wordpress"), dict) else {}
    wp_lab_summary = wp_surface_lab.get("summary") if isinstance(wp_surface_lab.get("summary"), dict) else {}
    wp_lab_runtime = wp_surface_lab.get("runtime") if isinstance(wp_surface_lab.get("runtime"), dict) else {}
    wp_runtime_summary = wp_surface_lab_runtime.get("summary") if isinstance(wp_surface_lab_runtime.get("summary"), dict) else {}
    wp_runtime_policy = wp_surface_lab_runtime.get("policy") if isinstance(wp_surface_lab_runtime.get("policy"), dict) else {}
    wp_runtime_validation_summary = wp_surface_lab_runtime_validation.get("summary") if isinstance(wp_surface_lab_runtime_validation.get("summary"), dict) else {}
    wp_runtime_validation_handoff = wp_surface_lab_runtime_validation.get("handoff") if isinstance(wp_surface_lab_runtime_validation.get("handoff"), dict) else {}
    wp_php_runtime_summary = wp_surface_lab_php_runtime.get("summary") if isinstance(wp_surface_lab_php_runtime.get("summary"), dict) else {}
    wp_php_runtime_runtime = wp_surface_lab_php_runtime.get("runtime") if isinstance(wp_surface_lab_php_runtime.get("runtime"), dict) else {}
    wp_php_runtime_package = wp_surface_lab_php_runtime.get("package") if isinstance(wp_surface_lab_php_runtime.get("package"), dict) else {}
    wp_php_fallback_summary = wp_surface_lab_php_fallback.get("summary") if isinstance(wp_surface_lab_php_fallback.get("summary"), dict) else {}
    wp_php_fallback_commands = wp_surface_lab_php_fallback.get("commands") if isinstance(wp_surface_lab_php_fallback.get("commands"), dict) else {}
    wp_platform_assets_summary = wp_platform_assets.get("summary") if isinstance(wp_platform_assets.get("summary"), dict) else {}
    wp_platform_assets_theme = wp_platform_assets.get("theme") if isinstance(wp_platform_assets.get("theme"), dict) else {}
    wp_platform_assets_plugin = wp_platform_assets.get("plugin") if isinstance(wp_platform_assets.get("plugin"), dict) else {}
    wordpress_platform_ia_summary = wordpress_platform_ia.get("summary") if isinstance(wordpress_platform_ia.get("summary"), dict) else {}
    wordpress_platform_ia_topology = wordpress_platform_ia.get("topology") if isinstance(wordpress_platform_ia.get("topology"), dict) else {}
    wp_platform_blueprints_summary = wp_platform_blueprints.get("summary") if isinstance(wp_platform_blueprints.get("summary"), dict) else {}
    wordpress_staging_apply_plan_summary = wordpress_staging_apply_plan.get("summary") if isinstance(wordpress_staging_apply_plan.get("summary"), dict) else {}
    wp_surface_lab_apply_summary = wp_surface_lab_apply.get("summary") if isinstance(wp_surface_lab_apply.get("summary"), dict) else {}
    wp_surface_lab_apply_artifacts = wp_surface_lab_apply.get("artifacts") if isinstance(wp_surface_lab_apply.get("artifacts"), dict) else {}
    wp_surface_lab_apply_result = wp_surface_lab_apply.get("apply_result") if isinstance(wp_surface_lab_apply.get("apply_result"), dict) else {}
    wp_surface_lab_apply_verify_cycle_summary = wp_surface_lab_apply_verify_cycle.get("summary") if isinstance(wp_surface_lab_apply_verify_cycle.get("summary"), dict) else {}
    wp_surface_lab_page_verify_summary = wp_surface_lab_page_verify.get("summary") if isinstance(wp_surface_lab_page_verify.get("summary"), dict) else {}
    wp_surface_lab_page_verify_runtime = wp_surface_lab_page_verify.get("runtime") if isinstance(wp_surface_lab_page_verify.get("runtime"), dict) else {}
    wordpress_platform_encoding_audit_summary = wordpress_platform_encoding_audit.get("summary") if isinstance(wordpress_platform_encoding_audit.get("summary"), dict) else {}
    wordpress_platform_ux_audit_summary = wordpress_platform_ux_audit.get("summary") if isinstance(wordpress_platform_ux_audit.get("summary"), dict) else {}
    wordpress_strategy_runtime = wordpress_platform_strategy.get("runtime_decision") if isinstance(wordpress_platform_strategy.get("runtime_decision"), dict) else {}
    wordpress_strategy_calc = wordpress_platform_strategy.get("calculator_mount_decision") if isinstance(wordpress_platform_strategy.get("calculator_mount_decision"), dict) else {}
    wordpress_strategy_plugin_stack = wordpress_platform_strategy.get("plugin_stack") if isinstance(wordpress_platform_strategy.get("plugin_stack"), dict) else {}
    wordpress_strategy_current = wordpress_platform_strategy.get("current_live_stack") if isinstance(wordpress_platform_strategy.get("current_live_stack"), dict) else {}
    astra_decision = astra_design_reference.get("decision") if isinstance(astra_design_reference.get("decision"), dict) else {}
    astra_theme = astra_design_reference.get("astra") if isinstance(astra_design_reference.get("astra"), dict) else {}
    kr_reverse_proxy_cutover_summary = kr_reverse_proxy_cutover.get("summary") if isinstance(kr_reverse_proxy_cutover.get("summary"), dict) else {}
    kr_reverse_proxy_cutover_topology = kr_reverse_proxy_cutover.get("topology") if isinstance(kr_reverse_proxy_cutover.get("topology"), dict) else {}
    kr_traffic_decision = kr_traffic_gate_audit.get("decision") if isinstance(kr_traffic_gate_audit.get("decision"), dict) else {}
    kr_traffic_live_probe = kr_traffic_gate_audit.get("live_probe") if isinstance(kr_traffic_gate_audit.get("live_probe"), dict) else {}
    kr_readiness_handoff = (
        kr_deploy_readiness.get("handoff")
        if isinstance(kr_deploy_readiness.get("handoff"), dict)
        else {}
    )
    kr_preview_handoff = (
        kr_preview_deploy.get("handoff")
        if isinstance(kr_preview_deploy.get("handoff"), dict)
        else {}
    )
    alignment_summary = partner_preview_alignment.get("summary") if isinstance(partner_preview_alignment.get("summary"), dict) else {}
    resolution_summary = partner_resolution.get("summary") if isinstance(partner_resolution.get("summary"), dict) else {}
    input_snapshot_summary = partner_input_snapshot.get("summary") if isinstance(partner_input_snapshot.get("summary"), dict) else {}
    input_snapshot_rows = partner_input_snapshot.get("partners") if isinstance(partner_input_snapshot.get("partners"), list) else []
    simulation_summary = partner_simulation_matrix.get("summary") if isinstance(partner_simulation_matrix.get("summary"), dict) else {}
    recommendation_qa_summary = yangdo_recommendation_qa.get("summary") if isinstance(yangdo_recommendation_qa.get("summary"), dict) else {}
    recommendation_precision_summary = yangdo_recommendation_precision_matrix.get("summary") if isinstance(yangdo_recommendation_precision_matrix.get("summary"), dict) else {}
    recommendation_diversity_audit = _load_json(yangdo_recommendation_diversity_audit_path or Path())
    recommendation_diversity_summary = recommendation_diversity_audit.get("summary") if isinstance(recommendation_diversity_audit.get("summary"), dict) else {}
    recommendation_contract_summary = yangdo_recommendation_contract_audit.get("summary") if isinstance(yangdo_recommendation_contract_audit.get("summary"), dict) else {}
    recommendation_bridge_summary = yangdo_recommendation_bridge_packet.get("summary") if isinstance(yangdo_recommendation_bridge_packet.get("summary"), dict) else {}
    recommendation_bridge_public = yangdo_recommendation_bridge_packet.get("public_summary_contract") if isinstance(yangdo_recommendation_bridge_packet.get("public_summary_contract"), dict) else {}
    recommendation_bridge_rental = yangdo_recommendation_bridge_packet.get("rental_packaging") if isinstance(yangdo_recommendation_bridge_packet.get("rental_packaging"), dict) else {}
    recommendation_ux_packet = _load_json(yangdo_recommendation_ux_packet_path or Path())
    recommendation_ux_summary = recommendation_ux_packet.get("summary") if isinstance(recommendation_ux_packet.get("summary"), dict) else {}
    recommendation_ux_public = recommendation_ux_packet.get("public_summary_experience") if isinstance(recommendation_ux_packet.get("public_summary_experience"), dict) else {}
    recommendation_ux_detail_explainable = recommendation_ux_packet.get("detail_explainable_experience") if isinstance(recommendation_ux_packet.get("detail_explainable_experience"), dict) else {}
    recommendation_ux_detail = recommendation_ux_packet.get("consult_detail_experience") if isinstance(recommendation_ux_packet.get("consult_detail_experience"), dict) else {}
    recommendation_ux_matrix = recommendation_ux_packet.get("rental_exposure_matrix") if isinstance(recommendation_ux_packet.get("rental_exposure_matrix"), dict) else {}
    recommendation_alignment_audit = _load_json(yangdo_recommendation_alignment_audit_path or Path())
    recommendation_alignment_summary = recommendation_alignment_audit.get("summary") if isinstance(recommendation_alignment_audit.get("summary"), dict) else {}
    zero_display_recovery_audit = _load_json(yangdo_zero_display_recovery_audit_path or Path())
    zero_display_recovery_summary = zero_display_recovery_audit.get("summary") if isinstance(zero_display_recovery_audit.get("summary"), dict) else {}
    yangdo_service_copy_packet = _load_json(yangdo_service_copy_packet_path or Path())
    yangdo_service_copy_summary = yangdo_service_copy_packet.get("summary") if isinstance(yangdo_service_copy_packet.get("summary"), dict) else {}
    yangdo_service_copy_hero = yangdo_service_copy_packet.get("hero") if isinstance(yangdo_service_copy_packet.get("hero"), dict) else {}
    yangdo_service_copy_cta_ladder = yangdo_service_copy_packet.get("cta_ladder") if isinstance(yangdo_service_copy_packet.get("cta_ladder"), dict) else {}
    yangdo_service_copy_offering_matrix = yangdo_service_copy_packet.get("offering_matrix") if isinstance(yangdo_service_copy_packet.get("offering_matrix"), dict) else {}
    yangdo_service_copy_precision_sections = yangdo_service_copy_packet.get("precision_sections") if isinstance(yangdo_service_copy_packet.get("precision_sections"), list) else []
    yangdo_service_copy_packet = _load_json(yangdo_service_copy_packet_path or Path())
    yangdo_service_copy_summary = yangdo_service_copy_packet.get("summary") if isinstance(yangdo_service_copy_packet.get("summary"), dict) else {}
    permit_service_copy_packet = _load_json(permit_service_copy_packet_path or Path())
    permit_service_copy_summary = permit_service_copy_packet.get("summary") if isinstance(permit_service_copy_packet.get("summary"), dict) else {}
    permit_service_copy_hero = permit_service_copy_packet.get("hero") if isinstance(permit_service_copy_packet.get("hero"), dict) else {}
    permit_service_copy_cta_ladder = permit_service_copy_packet.get("cta_ladder") if isinstance(permit_service_copy_packet.get("cta_ladder"), dict) else {}
    permit_service_copy_lane_ladder = permit_service_copy_packet.get("lane_ladder") if isinstance(permit_service_copy_packet.get("lane_ladder"), dict) else {}
    permit_service_copy_offering_matrix = permit_service_copy_packet.get("offering_matrix") if isinstance(permit_service_copy_packet.get("offering_matrix"), dict) else {}
    permit_service_alignment_audit = _load_json(permit_service_alignment_audit_path or Path())
    permit_service_alignment_summary = permit_service_alignment_audit.get("summary") if isinstance(permit_service_alignment_audit.get("summary"), dict) else {}
    permit_rental_lane_packet = _load_json(permit_rental_lane_packet_path or Path())
    permit_rental_lane_summary = permit_rental_lane_packet.get("summary") if isinstance(permit_rental_lane_packet.get("summary"), dict) else {}
    permit_rental_lane_matrix = permit_rental_lane_packet.get("lane_matrix") if isinstance(permit_rental_lane_packet.get("lane_matrix"), dict) else {}
    permit_service_ux_packet = _load_json(permit_service_ux_packet_path or Path())
    permit_service_ux_summary = permit_service_ux_packet.get("summary") if isinstance(permit_service_ux_packet.get("summary"), dict) else {}
    permit_service_ux_public = permit_service_ux_packet.get("public_summary_experience") if isinstance(permit_service_ux_packet.get("public_summary_experience"), dict) else {}
    permit_service_ux_detail = permit_service_ux_packet.get("detail_checklist_experience") if isinstance(permit_service_ux_packet.get("detail_checklist_experience"), dict) else {}
    permit_service_ux_assist = permit_service_ux_packet.get("manual_review_assist_experience") if isinstance(permit_service_ux_packet.get("manual_review_assist_experience"), dict) else {}
    permit_public_contract_audit = _load_json(permit_public_contract_audit_path or Path())
    permit_public_contract_summary = permit_public_contract_audit.get("summary") if isinstance(permit_public_contract_audit.get("summary"), dict) else {}
    partner_input_handoff_packet = _load_json(partner_input_handoff_packet_path or Path())
    partner_input_handoff_summary = partner_input_handoff_packet.get("summary") if isinstance(partner_input_handoff_packet.get("summary"), dict) else {}
    partner_input_operator_flow = _load_json(partner_input_operator_flow_path or Path())
    partner_input_operator_flow_summary = partner_input_operator_flow.get("summary") if isinstance(partner_input_operator_flow.get("summary"), dict) else {}
    widget_rental_summary = widget_rental_catalog.get("summary") if isinstance(widget_rental_catalog.get("summary"), dict) else {}
    widget_rental_packaging = widget_rental_catalog.get("packaging") if isinstance(widget_rental_catalog.get("packaging"), dict) else {}
    yangdo_recommendation_rental = (
        (((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation") or {}))
        if isinstance((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation"), dict)
        else {}
    )
    yangdo_recommendation_lane_positioning = (
        yangdo_recommendation_rental.get("lane_positioning")
        if isinstance(yangdo_recommendation_rental.get("lane_positioning"), dict)
        else {}
    )
    improvement_summary = program_improvement_loop.get("summary") if isinstance(program_improvement_loop.get("summary"), dict) else {}
    improvement_top_actions = program_improvement_loop.get("top_next_actions") if isinstance(program_improvement_loop.get("top_next_actions"), list) else []
    ai_platform_first_principles_review = _load_json(ai_platform_first_principles_review_path or Path())
    ai_platform_first_principles_summary = ai_platform_first_principles_review.get("summary") if isinstance(ai_platform_first_principles_review.get("summary"), dict) else {}
    system_split_first_principles_packet = _load_json(system_split_first_principles_packet_path or Path())
    system_split_first_principles_summary = system_split_first_principles_packet.get("summary") if isinstance(system_split_first_principles_packet.get("summary"), dict) else {}
    next_batch_focus_packet = _load_json(next_batch_focus_packet_path or Path())
    next_batch_focus_summary = next_batch_focus_packet.get("summary") if isinstance(next_batch_focus_packet.get("summary"), dict) else {}
    next_batch_focus_selected = next_batch_focus_packet.get("selected_focus") if isinstance(next_batch_focus_packet.get("selected_focus"), dict) else {}
    next_execution_packet = _load_json(next_execution_packet_path or Path())
    next_execution_summary = next_execution_packet.get("summary") if isinstance(next_execution_packet.get("summary"), dict) else {}
    next_execution_selected = next_execution_packet.get("selected_execution") if isinstance(next_execution_packet.get("selected_execution"), dict) else {}
    listing_bridge_summary = listing_platform_bridge_policy.get("summary") if isinstance(listing_platform_bridge_policy.get("summary"), dict) else {}
    listing_bridge_policy_section = listing_platform_bridge_policy.get("policy") if isinstance(listing_platform_bridge_policy.get("policy"), dict) else {}
    listing_bridge_ctas = listing_platform_bridge_policy.get("ctas") if isinstance(listing_platform_bridge_policy.get("ctas"), list) else []
    co_listing_bridge_snippets_summary = co_listing_bridge_snippets.get("summary") if isinstance(co_listing_bridge_snippets.get("summary"), dict) else {}
    co_listing_bridge_operator_checklist_summary = co_listing_bridge_operator_checklist.get("summary") if isinstance(co_listing_bridge_operator_checklist.get("summary"), dict) else {}
    co_listing_live_injection_plan_summary = co_listing_live_injection_plan.get("summary") if isinstance(co_listing_live_injection_plan.get("summary"), dict) else {}
    co_listing_injection_bundle_summary = co_listing_injection_bundle.get("summary") if isinstance(co_listing_injection_bundle.get("summary"), dict) else {}
    co_listing_bridge_apply_packet_summary = co_listing_bridge_apply_packet.get("summary") if isinstance(co_listing_bridge_apply_packet.get("summary"), dict) else {}

    detail_explainable_lane_ready = bool(yangdo_service_copy_offering_matrix.get("detail_explainable")) and bool(
        yangdo_recommendation_lane_positioning.get("detail_explainable")
    )
    consult_assist_lane_ready = bool(yangdo_service_copy_offering_matrix.get("consult_assist")) and bool(
        yangdo_recommendation_lane_positioning.get("consult_assist")
    )
    precision_lane_contract_ready = (
        len(yangdo_service_copy_precision_sections) >= 3
        and str((yangdo_service_copy_precision_sections[0] or {}).get("preferred_lane") or "") == "summary_market_bridge"
        and str((yangdo_service_copy_precision_sections[1] or {}).get("preferred_lane") or "") == "detail_explainable"
        and str((yangdo_service_copy_precision_sections[2] or {}).get("preferred_lane") or "") == "consult_assist"
    )
    yangdo_recommendation_lane_ladder_ready = detail_explainable_lane_ready and consult_assist_lane_ready and precision_lane_contract_ready
    permit_detail_checklist_lane_ready = bool(permit_service_copy_offering_matrix.get("detail_checklist")) and bool(permit_service_copy_lane_ladder.get("detail_checklist"))
    permit_manual_review_assist_lane_ready = bool(permit_service_copy_offering_matrix.get("manual_review_assist")) and bool(permit_service_copy_lane_ladder.get("manual_review_assist"))
    permit_lane_ladder_ready = bool(permit_service_copy_summary.get("lane_ladder_ready")) and permit_detail_checklist_lane_ready and permit_manual_review_assist_lane_ready
    kr_proxy_server_summary = kr_proxy_server_matrix.get("summary") if isinstance(kr_proxy_server_matrix.get("summary"), dict) else {}
    kr_proxy_nginx = kr_proxy_server_matrix.get("nginx") if isinstance(kr_proxy_server_matrix.get("nginx"), dict) else {}
    kr_proxy_server_bundle_summary = kr_proxy_server_bundle.get("summary") if isinstance(kr_proxy_server_bundle.get("summary"), dict) else {}
    kr_live_apply_summary = kr_live_apply_packet.get("summary") if isinstance(kr_live_apply_packet.get("summary"), dict) else {}
    kr_live_operator_summary = kr_live_operator_checklist.get("summary") if isinstance(kr_live_operator_checklist.get("summary"), dict) else {}

    blockers: List[str] = []
    for group in (
        readiness.get("blocking_issues") or [],
        release.get("blocking_issues") or [],
        (release.get("artifact_summary") or {}).get("runtime", {}).get("blocking_issues", []),
    ):
        for item in group:
            text = str(item or "").strip()
            if text and text not in blockers:
                blockers.append(text)
    normalized_blockers = []
    for item in blockers:
        normalized = _normalize_blocker(item)
        if normalized and normalized not in normalized_blockers:
            normalized_blockers.append(normalized)

    next_actions: List[str] = []
    for group in (
        readiness_handoff.get("next_actions") or [],
        release_handoff.get("next_actions") or [],
    ):
        for item in group:
            text = str(item or "").strip()
            if text:
                next_actions.append(text)
    partner_handoff = partner_flow.get("handoff") if isinstance(partner_flow.get("handoff"), dict) else {}
    for item in (partner_handoff.get("next_actions") or []):
        text = str(item or "").strip()
        if text:
            next_actions.append(text)
    next_actions = _normalize_next_actions(normalized_blockers, next_actions)

    quality_green = str(risk_map.get("business_core_status") or "").strip().lower() == "green"
    release_ready = bool(readiness_handoff.get("release_ready"))
    release_report_ok = bool(release.get("ok"))
    decisions = _decision_flags(
        quality_green=quality_green,
        release_ready=release_ready,
        release_report_ok=release_report_ok,
        blockers=normalized_blockers,
    )

    tenant_rows = onboarding_validation.get("tenants") if isinstance(onboarding_validation.get("tenants"), list) else []
    channel_rows = onboarding_validation.get("channels") if isinstance(onboarding_validation.get("channels"), list) else []
    partner_tenants = [row for row in tenant_rows if isinstance(row, dict) and str(row.get("tenant_id") or "").startswith("partner_")]
    partner_channels = [row for row in channel_rows if isinstance(row, dict) and str(row.get("channel_id") or "").startswith("partner_")]
    partner_blockers = [
        str(item)
        for item in (partner_flow.get("activation_blockers") or [])
        if str(item or "").strip()
    ]
    partner_flow_required_inputs = _required_inputs_from_blockers(partner_blockers)
    partner_flow_tenant_id = str(partner_flow.get("tenant_id") or "").strip()
    if not partner_flow_tenant_id and len(partner_tenants) == 1:
        partner_flow_tenant_id = str(partner_tenants[0].get("tenant_id") or "").strip()
    partner_activation_decision = "ready" if bool(partner_handoff.get("activation_ready")) else ("awaiting_partner_inputs" if partner_blockers else "unknown")
    latest_flow_resolved_inputs = list(partner_handoff.get("resolved_inputs") or [])
    latest_flow_remaining_required_inputs = list(partner_handoff.get("remaining_required_inputs") or partner_flow_required_inputs)
    partner_flow_scope_registered = any(str(row.get("tenant_id") or "").strip() == partner_flow_tenant_id for row in partner_tenants) if partner_flow_tenant_id else False
    partner_channels_by_tenant = {
        str(row.get("default_tenant_id") or "").strip(): row
        for row in partner_channels
        if isinstance(row, dict)
    }
    snapshot_by_tenant = {
        str(row.get("tenant_id") or "").strip(): row
        for row in input_snapshot_rows
        if isinstance(row, dict) and str(row.get("tenant_id") or "").strip()
    }
    for row in partner_channels:
        if not isinstance(row, dict):
            continue
        default_tenant_id = str(row.get("default_tenant_id") or "").strip()
        channel_id = str(row.get("channel_id") or "").strip()
        if channel_id and channel_id not in partner_channels_by_tenant:
            partner_channels_by_tenant[channel_id] = row
        if default_tenant_id and default_tenant_id not in partner_channels_by_tenant:
            partner_channels_by_tenant[default_tenant_id] = row

    partner_checklists = []
    required_input_counter: Dict[str, int] = {}
    partner_flow_consumed = False
    for row in partner_tenants:
        tenant_id = str(row.get("tenant_id") or "").strip()
        channel = partner_channels_by_tenant.get(tenant_id, {})
        tenant_blockers = [str(x) for x in (row.get("activation_blockers") or []) if str(x).strip()]
        if partner_flow_tenant_id and tenant_id == partner_flow_tenant_id:
            tenant_blockers = _dedupe_blockers(tenant_blockers + partner_blockers)
            partner_flow_consumed = True
        normalized_tenant_blockers = _dedupe_blockers([_normalize_blocker(x) for x in tenant_blockers if _normalize_blocker(x)])
        snapshot_row = snapshot_by_tenant.get(tenant_id, {})
        required_inputs = _as_list(
            snapshot_row.get("resolution_remaining_required_inputs")
            or snapshot_row.get("missing_required_inputs")
        )
        if not required_inputs:
            required_inputs = _required_inputs_from_blockers(tenant_blockers)
        for req in required_inputs:
            required_input_counter[req] = int(required_input_counter.get(req, 0) or 0) + 1
        partner_checklists.append(
            {
                "tenant_id": tenant_id,
                "channel_id": str(channel.get("channel_id") or "").strip(),
                "systems": list(row.get("allowed_systems") or []),
                "activation_ready": bool(row.get("activation_ready")),
                "normalized_blockers": normalized_tenant_blockers,
                "required_inputs": required_inputs,
                "input_source": "snapshot" if snapshot_row else "activation_blockers",
            }
        )
    if partner_flow_tenant_id and not any(str(row.get("tenant_id") or "").strip() == partner_flow_tenant_id for row in partner_tenants):
        required_inputs = _required_inputs_from_blockers(partner_blockers)
        for req in required_inputs:
            required_input_counter[req] = int(required_input_counter.get(req, 0) or 0) + 1
        fallback_channel = partner_channels_by_tenant.get(partner_flow_tenant_id, {})
        partner_flow_consumed = True
        partner_checklists.append(
            {
                "tenant_id": partner_flow_tenant_id,
                "channel_id": str(fallback_channel.get("channel_id") or "").strip(),
                "systems": list((partner_flow.get("offering_allowed_systems") or [])),
                "activation_ready": bool(partner_handoff.get("activation_ready")),
                "normalized_blockers": _dedupe_blockers([_normalize_blocker(x) for x in partner_blockers if _normalize_blocker(x)]),
                "required_inputs": required_inputs,
            }
        )
    if partner_flow_required_inputs and not partner_flow_consumed:
        for req in partner_flow_required_inputs:
            required_input_counter[req] = int(required_input_counter.get(req, 0) or 0) + 1

    seoul_required_inputs = _required_inputs_from_blockers(normalized_blockers)
    partner_required_input_items = {
        key: {
            **REQUIRED_INPUT_METADATA.get(key, {"label": key, "description": "", "owner": "operator"}),
            "count": value,
        }
        for key, value in required_input_counter.items()
    }
    preview_recommended = partner_preview.get("recommended_path") if isinstance(partner_preview.get("recommended_path"), dict) else {}
    preview_recommended_scenario = str(preview_recommended.get("scenario") or "")
    preview_remaining_required_inputs = list(preview_recommended.get("remaining_required_inputs") or [])
    preview_next_actions = _normalize_next_actions(preview_remaining_required_inputs, list(preview_recommended.get("next_actions") or []))
    preview_removed_inputs = [
        item for item in latest_flow_remaining_required_inputs
        if item not in preview_remaining_required_inputs
    ]

    partner_handoff_checklists = []
    for row in partner_checklists:
        partner_handoff_checklists.append(
            {
                "tenant_id": row.get("tenant_id"),
                "channel_id": row.get("channel_id"),
                "systems": row.get("systems") or [],
                "activation_ready": bool(row.get("activation_ready")),
                "items": _build_required_input_items(list(row.get("required_inputs") or [])),
            }
        )
    required_input_sets = [
        tuple(item for item in (row.get("required_inputs") or []) if str(item or "").strip())
        for row in partner_checklists
        if isinstance(row, dict)
    ]
    common_required_inputs = list(required_input_sets[0]) if required_input_sets else []
    for row_inputs in required_input_sets[1:]:
        common_required_inputs = [item for item in common_required_inputs if item in row_inputs]
    uniform_required_inputs = bool(required_input_sets) and len({tuple(row_inputs) for row_inputs in required_input_sets}) == 1

    kr_blockers = [str(x) for x in (kr_deploy_readiness.get("blocking_issues") or []) if str(x).strip()]
    kr_deploy_ready = bool(kr_readiness_handoff.get("preview_deploy_ready"))
    kr_preview_deployed = bool(kr_preview_handoff.get("preview_deployed"))
    if kr_preview_deployed:
        kr_next_lane_decision = "preview_deployed"
    elif kr_deploy_ready:
        kr_next_lane_decision = "ready_for_preview_deploy"
    elif "vercel_auth_missing" in kr_blockers:
        kr_next_lane_decision = "awaiting_vercel_auth"
    elif "vercel_cli_missing" in kr_blockers:
        kr_next_lane_decision = "awaiting_vercel_cli"
    else:
        kr_next_lane_decision = str(front_summary.get("front_platform_status") or "transition_pending")

    wp_plugin_decision = "unknown"
    if str(surface_wordpress.get("live_applicability", {}).get("decision") or "") == "sandbox_only":
        if bool(wp_lab_summary.get("downloaded_count")):
            wp_plugin_decision = "sandbox_ready_runtime_missing" if not bool(wp_runtime_validation_summary.get("runtime_ready")) else "sandbox_runtime_ready"
        else:
            wp_plugin_decision = "sandbox_planned_assets_missing"
    wp_runtime_decision = "runtime_scaffold_missing"
    if bool(wp_runtime_validation_summary.get("runtime_running")):
        wp_runtime_decision = "runtime_running"
    elif bool(wp_runtime_validation_summary.get("runtime_ready")):
        wp_runtime_decision = "runtime_launch_ready"
    elif bool(wp_runtime_validation_summary.get("runtime_scaffold_ready")):
        wp_runtime_decision = "scaffold_ready_runtime_missing"
    wp_surface_apply_decision = "apply_bundle_missing"
    if bool(wp_surface_lab_page_verify_summary.get("verification_ok")):
        wp_surface_apply_decision = "verified"
    elif bool(wp_surface_lab_apply_summary.get("bundle_ready")):
        wp_surface_apply_decision = "apply_bundle_ready_runtime_missing" if not bool(wp_surface_lab_page_verify_summary.get("verification_ready")) else "apply_bundle_ready_verify_pending"
    wordpress_encoding_decision = "clean" if bool(wordpress_platform_encoding_audit_summary.get("encoding_ok")) else "investigate_encoding"
    wordpress_ux_decision = "service_flow_ready" if bool(wordpress_platform_ux_audit_summary.get("ux_ok")) else "fix_platform_ux"
    wordpress_ia_decision = "missing"
    if int(wordpress_platform_ia_summary.get("page_count", 0) or 0) > 0:
        wordpress_ia_decision = "service_ia_ready"
    reverse_proxy_cutover_decision = "missing"
    if bool(kr_reverse_proxy_cutover_summary.get("cutover_ready")):
        reverse_proxy_cutover_decision = "cutover_ready"
    elif kr_reverse_proxy_cutover:
        reverse_proxy_cutover_decision = "cutover_planned"

    current_live_public_stack = str(front_topology.get("current_live_public_stack") or "")
    if current_live_public_stack.startswith("wordpress"):
        if (
            wp_surface_apply_decision == "verified"
            and wordpress_ux_decision == "service_flow_ready"
            and wordpress_ia_decision == "service_ia_ready"
            and reverse_proxy_cutover_decision == "cutover_ready"
        ):
            kr_wordpress_platform_decision = "wordpress_live_path_ready"
        else:
            kr_wordpress_platform_decision = "wordpress_live_path_in_progress"
        kr_platform_decision = kr_wordpress_platform_decision
    else:
        kr_wordpress_platform_decision = "not_primary_lane"
        kr_platform_decision = kr_next_lane_decision

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workspace": str(ROOT),
        "topology": {
            "main_platform_host": str(front_topology.get("canonical_public_host") or "seoulmna.kr"),
            "main_platform_role": str(front_topology.get("channel_role") or "platform_front"),
            "listing_market_host": str(front_topology.get("listing_market_host") or front_topology.get("current_content_host") or "seoulmna.co.kr"),
            "listing_market_role": "listing_market_site",
            "public_calculator_mount_host": str(front_topology.get("canonical_public_host") or "seoulmna.kr"),
            "private_engine_public_path": str(wordpress_strategy_calc.get("private_engine_public_mount") or "https://seoulmna.kr/_calc/<type>?embed=1").replace("https://seoulmna.kr", "").replace("<type>?embed=1", "*"),
            "engine_visibility": str(front_topology.get("private_engine_visibility") or private_engine_proxy_decision.get("engine_visibility") or "private_reverse_proxy"),
            "front_platform_status": str(front_summary.get("front_platform_status") or ""),
            "wp_theme_live_strategy": str(surface_decisions.get("plugin_theme_strategy") or ""),
        },
        "decisions": {
            **decisions,
            "kr_platform_decision": kr_platform_decision,
            "kr_wordpress_platform_decision": kr_wordpress_platform_decision,
            "kr_next_lane_decision": kr_next_lane_decision,
            "wp_plugin_decision": wp_plugin_decision,
            "wp_runtime_decision": wp_runtime_decision,
            "wp_surface_apply_decision": wp_surface_apply_decision,
            "wordpress_encoding_decision": wordpress_encoding_decision,
            "wordpress_ux_decision": wordpress_ux_decision,
            "wordpress_ia_decision": wordpress_ia_decision,
            "reverse_proxy_cutover_decision": reverse_proxy_cutover_decision,
            "kr_traffic_gate_ok": bool(kr_traffic_decision.get("traffic_leak_blocked")),
            "partner_activation_decision": partner_activation_decision,
            "partner_fastest_path_scenario": preview_recommended_scenario,
            "partner_fastest_path_ready": len(preview_remaining_required_inputs) == 0 if preview_recommended_scenario else False,
            "partner_preview_alignment_ok": bool(alignment_summary.get("ok")),
            "partner_resolution_ok": bool(resolution_summary.get("ok")),
            "partner_resolution_actionable": bool(resolution_summary.get("ok")) and partner_flow_scope_registered,
            "partner_input_snapshot_ready_count": int(input_snapshot_summary.get("ready_tenant_count", 0) or 0),
            "partner_simulation_ready_count": int(simulation_summary.get("ready_after_simulation_count", 0) or 0),
            "partner_simulation_all_ready": bool(simulation_summary.get("all_ready_after_simulation")),
            "partner_uniform_required_inputs": uniform_required_inputs,
            "partner_flow_scope_registered": partner_flow_scope_registered,
            "yangdo_recommendation_qa_ok": bool(recommendation_qa_summary.get("qa_ok")),
            "yangdo_recommendation_precision_ok": bool(recommendation_precision_summary.get("precision_ok")),
            "yangdo_recommendation_diversity_ok": bool(recommendation_diversity_summary.get("diversity_ok")),
            "yangdo_recommendation_concentration_ok": bool(recommendation_diversity_summary.get("cluster_concentration_ok")) and bool(recommendation_diversity_summary.get("top_rank_signature_concentration_ok")) and bool(recommendation_diversity_summary.get("price_band_concentration_ok")),
            "yangdo_recommendation_contract_ok": bool(recommendation_contract_summary.get("contract_ok")),
            "yangdo_recommendation_bridge_ready": bool(recommendation_bridge_summary.get("packet_ready")),
            "yangdo_recommendation_ux_ready": bool(recommendation_ux_summary.get("packet_ready")),
            "yangdo_recommendation_alignment_ok": bool(recommendation_alignment_summary.get("alignment_ok")),
            "yangdo_zero_display_guard_ok": bool(zero_display_recovery_summary.get("zero_display_guard_ok")),
            "yangdo_recommendation_lane_ladder_ready": yangdo_recommendation_lane_ladder_ready,
            "yangdo_service_copy_ready": bool(yangdo_service_copy_summary.get("packet_ready")),
            "permit_service_copy_ready": bool(permit_service_copy_summary.get("packet_ready")),
            "permit_lane_ladder_ready": permit_lane_ladder_ready,
            "permit_service_alignment_ok": bool(permit_service_alignment_summary.get("alignment_ok")),
            "permit_rental_lane_ready": bool(permit_rental_lane_summary.get("packet_ready")),
            "permit_service_ux_ready": bool(permit_service_ux_summary.get("packet_ready")),
            "permit_public_contract_ok": bool(permit_public_contract_summary.get("contract_ok")),
            "partner_input_handoff_ready": bool(partner_input_handoff_summary.get("partner_count")) and bool(partner_input_handoff_summary.get("copy_paste_ready")),
            "partner_input_operator_flow_ready": bool(partner_input_operator_flow_summary.get("packet_ready")),
            "ai_platform_first_principles_ready": bool(ai_platform_first_principles_summary.get("packet_ready")),
            "system_split_first_principles_ready": bool(system_split_first_principles_summary.get("packet_ready")),
            "next_batch_focus_ready": bool(next_batch_focus_summary.get("packet_ready")),
            "next_batch_focus_track": str(next_batch_focus_summary.get("selected_track") or next_batch_focus_selected.get("track") or ""),
            "next_batch_focus_lane_id": str(next_batch_focus_summary.get("selected_lane_id") or next_batch_focus_selected.get("lane_id") or ""),
            "next_execution_packet_ready": bool(next_execution_summary.get("packet_ready")),
            "next_execution_ready": bool(next_execution_summary.get("execution_ready")),
            "next_execution_track": str(next_execution_summary.get("selected_track") or _safe_dict(next_execution_selected.get("selected_focus")).get("track") or ""),
            "next_execution_lane_id": str(next_execution_summary.get("selected_lane_id") or _safe_dict(next_execution_selected.get("selected_focus")).get("lane_id") or ""),
        },
        "go_live": {
            "quality_green": quality_green,
            "release_ready": release_ready,
            "runtime_verified": bool(release_handoff.get("runtime_verified")) if release_handoff else False,
            "release_report_ok": release_report_ok,
        },
        "blockers": blockers,
        "normalized_blockers": normalized_blockers,
        "next_actions": next_actions,
        "required_inputs": {
            "seoul_live": seoul_required_inputs,
            "partner_aggregate": required_input_counter,
            "partner_fastest_path": preview_remaining_required_inputs,
            "partner_common": common_required_inputs,
        },
        "handoff_checklists": {
            "seoul_live": _build_required_input_items(seoul_required_inputs),
            "partner_activation": partner_handoff_checklists,
            "partner_aggregate": partner_required_input_items,
        },
        "artifacts": {
            "readiness": str(readiness_path.resolve()),
            "release": str(release_path.resolve()),
            "risk_map": str(risk_map_path.resolve()),
            "attorney_handoff": str(attorney_path.resolve()),
            "platform_front_audit": str((platform_front_audit_path or Path()).resolve()) if platform_front_audit_path else "",
            "surface_stack_audit": str((surface_stack_audit_path or Path()).resolve()) if surface_stack_audit_path else "",
            "private_engine_proxy_spec": str((private_engine_proxy_spec_path or Path()).resolve()) if private_engine_proxy_spec_path else "",
            "wp_surface_lab": str((wp_surface_lab_path or Path()).resolve()) if wp_surface_lab_path else "",
            "wp_surface_lab_runtime": str((wp_surface_lab_runtime_path or Path()).resolve()) if wp_surface_lab_runtime_path else "",
            "wp_surface_lab_runtime_validation": str((wp_surface_lab_runtime_validation_path or Path()).resolve()) if wp_surface_lab_runtime_validation_path else "",
            "wp_surface_lab_php_runtime": str((wp_surface_lab_php_runtime_path or Path()).resolve()) if wp_surface_lab_php_runtime_path else "",
            "wp_surface_lab_php_fallback": str((wp_surface_lab_php_fallback_path or Path()).resolve()) if wp_surface_lab_php_fallback_path else "",
            "wp_platform_assets": str((wp_platform_assets_path or Path()).resolve()) if wp_platform_assets_path else "",
            "wordpress_platform_ia": str((wordpress_platform_ia_path or Path()).resolve()) if wordpress_platform_ia_path else "",
            "wp_platform_blueprints": str((wp_platform_blueprints_path or Path()).resolve()) if wp_platform_blueprints_path else "",
            "wordpress_staging_apply_plan": str((wordpress_staging_apply_plan_path or Path()).resolve()) if wordpress_staging_apply_plan_path else "",
            "wp_surface_lab_apply": str((wp_surface_lab_apply_path or Path()).resolve()) if wp_surface_lab_apply_path else "",
            "wp_surface_lab_apply_verify_cycle": str((wp_surface_lab_apply_verify_cycle_path or Path()).resolve()) if wp_surface_lab_apply_verify_cycle_path else "",
            "wp_surface_lab_page_verify": str((wp_surface_lab_page_verify_path or Path()).resolve()) if wp_surface_lab_page_verify_path else "",
            "wordpress_platform_encoding_audit": str((wordpress_platform_encoding_audit_path or Path()).resolve()) if wordpress_platform_encoding_audit_path else "",
            "wordpress_platform_ux_audit": str((wordpress_platform_ux_audit_path or Path()).resolve()) if wordpress_platform_ux_audit_path else "",
            "wordpress_platform_strategy": str((wordpress_platform_strategy_path or Path()).resolve()) if wordpress_platform_strategy_path else "",
            "astra_design_reference": str((astra_design_reference_path or Path()).resolve()) if astra_design_reference_path else "",
            "kr_reverse_proxy_cutover": str((kr_reverse_proxy_cutover_path or Path()).resolve()) if kr_reverse_proxy_cutover_path else "",
            "kr_traffic_gate_audit": str((kr_traffic_gate_audit_path or Path()).resolve()) if kr_traffic_gate_audit_path else "",
            "kr_deploy_readiness": str((kr_deploy_readiness_path or Path()).resolve()) if kr_deploy_readiness_path else "",
            "kr_preview_deploy": str((kr_preview_deploy_path or Path()).resolve()) if kr_preview_deploy_path else "",
            "onboarding_validation": str((onboarding_validation_path or Path()).resolve()) if onboarding_validation_path else "",
            "partner_flow": str((partner_flow_path or Path()).resolve()) if partner_flow_path else "",
            "partner_preview": str((partner_preview_path or Path()).resolve()) if partner_preview_path else "",
            "partner_preview_alignment": str((partner_preview_alignment_path or Path()).resolve()) if partner_preview_alignment_path else "",
            "partner_resolution": str((partner_resolution_path or Path()).resolve()) if partner_resolution_path else "",
            "partner_input_snapshot": str((partner_input_snapshot_path or Path()).resolve()) if partner_input_snapshot_path else "",
            "partner_simulation_matrix": str((partner_simulation_matrix_path or Path()).resolve()) if partner_simulation_matrix_path else "",
            "yangdo_recommendation_qa": str((yangdo_recommendation_qa_path or Path()).resolve()) if yangdo_recommendation_qa_path else "",
            "yangdo_recommendation_precision_matrix": str((yangdo_recommendation_precision_matrix_path or Path()).resolve()) if yangdo_recommendation_precision_matrix_path else "",
            "yangdo_recommendation_diversity_audit": str((yangdo_recommendation_diversity_audit_path or Path()).resolve()) if yangdo_recommendation_diversity_audit_path else "",
            "yangdo_recommendation_contract_audit": str((yangdo_recommendation_contract_audit_path or Path()).resolve()) if yangdo_recommendation_contract_audit_path else "",
            "yangdo_recommendation_bridge_packet": str((yangdo_recommendation_bridge_packet_path or Path()).resolve()) if yangdo_recommendation_bridge_packet_path else "",
            "yangdo_recommendation_ux_packet": str((yangdo_recommendation_ux_packet_path or Path()).resolve()) if yangdo_recommendation_ux_packet_path else "",
            "yangdo_recommendation_alignment_audit": str((yangdo_recommendation_alignment_audit_path or Path()).resolve()) if yangdo_recommendation_alignment_audit_path else "",
            "yangdo_zero_display_recovery_audit": str((yangdo_zero_display_recovery_audit_path or Path()).resolve()) if yangdo_zero_display_recovery_audit_path else "",
            "yangdo_service_copy_packet": str((yangdo_service_copy_packet_path or Path()).resolve()) if yangdo_service_copy_packet_path else "",
            "permit_service_copy_packet": str((permit_service_copy_packet_path or Path()).resolve()) if permit_service_copy_packet_path else "",
            "permit_service_alignment_audit": str((permit_service_alignment_audit_path or Path()).resolve()) if permit_service_alignment_audit_path else "",
            "permit_service_ux_packet": str((permit_service_ux_packet_path or Path()).resolve()) if permit_service_ux_packet_path else "",
            "permit_public_contract_audit": str((permit_public_contract_audit_path or Path()).resolve()) if permit_public_contract_audit_path else "",
            "partner_input_handoff_packet": str((partner_input_handoff_packet_path or Path()).resolve()) if partner_input_handoff_packet_path else "",
            "partner_input_operator_flow": str((partner_input_operator_flow_path or Path()).resolve()) if partner_input_operator_flow_path else "",
            "widget_rental_catalog": str((widget_rental_catalog_path or Path()).resolve()) if widget_rental_catalog_path else "",
            "program_improvement_loop": str((program_improvement_loop_path or Path()).resolve()) if program_improvement_loop_path else "",
            "ai_platform_first_principles_review": str((ai_platform_first_principles_review_path or Path()).resolve()) if ai_platform_first_principles_review_path else "",
            "system_split_first_principles_packet": str((system_split_first_principles_packet_path or Path()).resolve()) if system_split_first_principles_packet_path else "",
            "next_batch_focus_packet": str((next_batch_focus_packet_path or Path()).resolve()) if next_batch_focus_packet_path else "",
            "next_execution_packet": str((next_execution_packet_path or Path()).resolve()) if next_execution_packet_path else "",
            "listing_platform_bridge_policy": str((listing_platform_bridge_policy_path or Path()).resolve()) if listing_platform_bridge_policy_path else "",
            "co_listing_bridge_snippets": str((co_listing_bridge_snippets_path or Path()).resolve()) if co_listing_bridge_snippets_path else "",
            "co_listing_bridge_operator_checklist": str((co_listing_bridge_operator_checklist_path or Path()).resolve()) if co_listing_bridge_operator_checklist_path else "",
            "co_listing_live_injection_plan": str((co_listing_live_injection_plan_path or Path()).resolve()) if co_listing_live_injection_plan_path else "",
            "co_listing_injection_bundle": str((co_listing_injection_bundle_path or Path()).resolve()) if co_listing_injection_bundle_path else "",
            "co_listing_bridge_apply_packet": str((co_listing_bridge_apply_packet_path or Path()).resolve()) if co_listing_bridge_apply_packet_path else "",
            "kr_proxy_server_matrix": str((kr_proxy_server_matrix_path or Path()).resolve()) if kr_proxy_server_matrix_path else "",
            "kr_proxy_server_bundle": str((kr_proxy_server_bundle_path or Path()).resolve()) if kr_proxy_server_bundle_path else "",
            "kr_live_apply_packet": str((kr_live_apply_packet_path or Path()).resolve()) if kr_live_apply_packet_path else "",
            "kr_live_operator_checklist": str((kr_live_operator_checklist_path or Path()).resolve()) if kr_live_operator_checklist_path else "",
        },
        "summaries": {
            "readiness": {
                "ok": bool(readiness.get("ok")),
                "blocking_issue_count": len(readiness.get("blocking_issues") or []),
                "release_ready": bool(readiness_handoff.get("release_ready")),
            },
            "release": {
                "ok": bool(release.get("ok")),
                "blocking_issue_count": len(release.get("blocking_issues") or []),
                "artifact_summary": release.get("artifact_summary") or {},
                "rollback": release.get("rollback") if isinstance(release.get("rollback"), dict) else {},
            },
            "risk_map": {
                "ok": bool(risk_map.get("ok")),
                "business_core_status": risk_map.get("business_core_status"),
                "ran_tests": int(risk_summary.get("ran_tests", 0) or 0),
                "issue_count": int(risk_summary.get("issue_count", 0) or 0),
            },
            "attorney": {
                "track_count": len(attorney.get("tracks") or []),
                "independent_systems": list(exec_summary.get("independent_systems") or []),
                "claim_strategy": list(exec_summary.get("claim_strategy") or []),
                "handoff_notes": list(exec_summary.get("attorney_handoff") or []),
            },
            "kr_platform": {
                "status": str(front_summary.get("front_platform_status") or ""),
                "primary_lane": "wordpress_live" if current_live_public_stack.startswith("wordpress") else "next_preview",
                "current_live_stack": current_live_public_stack,
                "wordpress_live_decision": kr_wordpress_platform_decision,
                "next_lane_decision": kr_next_lane_decision,
                "deploy_ready": kr_deploy_ready,
                "preview_deployed": kr_preview_deployed,
                "preview_url": str(kr_preview_handoff.get("preview_url") or ""),
                "blocking_issues": kr_blockers,
                "next_actions": list(kr_readiness_handoff.get("next_actions") or []),
            },
            "surface_stack": {
                "kr_stack": str(surface_stack_audit.get("surfaces", {}).get("kr", {}).get("stack") or ""),
                "co_stack": str(surface_stack_audit.get("surfaces", {}).get("co", {}).get("stack") or ""),
                "wordpress_live_decision": str(surface_wordpress.get("live_applicability", {}).get("decision") or ""),
                "candidate_package_slugs": list(surface_wordpress.get("candidate_package_slugs") or []),
            },
            "private_engine_proxy": {
                "main_platform_host": str(private_engine_proxy_topology.get("main_platform_host") or ""),
                "listing_market_host": str(private_engine_proxy_topology.get("listing_market_host") or ""),
                "public_mount_base": str(private_engine_proxy_topology.get("public_mount_base") or ""),
                "private_engine_origin": str(private_engine_proxy_topology.get("private_engine_origin") or ""),
                "public_contract": str(private_engine_proxy_decision.get("public_contract") or ""),
            },
            "wp_surface_lab": {
                "package_count": int(wp_lab_summary.get("package_count", 0) or 0),
                "downloaded_count": int(wp_lab_summary.get("downloaded_count", 0) or 0),
                "staging_ready_count": int(wp_lab_summary.get("staging_ready_count", 0) or 0),
                "runtime_ready": bool(wp_runtime_validation_summary.get("runtime_ready")),
                "runtime_running": bool(wp_runtime_validation_summary.get("runtime_running")),
                "runtime_mode": str(wp_runtime_validation_summary.get("runtime_mode") or ""),
                "runtime_blockers": list(wp_runtime_validation_summary.get("blockers") or []),
            },
            "wp_surface_lab_runtime": {
                "runtime_scaffold_ready": bool(wp_runtime_validation_summary.get("runtime_scaffold_ready")),
                "runtime_ready": bool(wp_runtime_validation_summary.get("runtime_ready")),
                "runtime_running": bool(wp_runtime_validation_summary.get("runtime_running")),
                "runtime_mode": str(wp_runtime_validation_summary.get("runtime_mode") or ""),
                "docker_available": bool(wp_runtime_summary.get("docker_available")),
                "local_bind_only": bool(wp_runtime_summary.get("local_bind_only")),
                "localhost_url": str(wp_runtime_validation_handoff.get("localhost_url") or wp_runtime_policy.get("localhost_url") or ""),
                "blockers": list(wp_runtime_validation_summary.get("blockers") or []),
            },
            "wp_surface_lab_php_runtime": {
                "archive_name": str(wp_php_runtime_package.get("archive_name") or ""),
                "runtime_key": str(wp_php_runtime_package.get("runtime_key") or ""),
                "package_ready": bool(wp_php_runtime_summary.get("package_ready")),
                "php_binary_ready": bool(wp_php_runtime_summary.get("php_binary_ready")),
                "php_module_ready": bool(wp_php_runtime_summary.get("php_module_ready")),
                "localhost_url": str(wp_php_runtime_runtime.get("localhost_url") or ""),
                "missing_modules": list(wp_php_runtime_runtime.get("missing_modules") or []),
            },
            "wp_surface_lab_php_fallback": {
                "site_root_ready": bool(wp_php_fallback_summary.get("site_root_ready")),
                "php_runtime_ready": bool(wp_php_fallback_summary.get("php_runtime_ready")),
                "sqlite_plugin_ready": bool(wp_php_fallback_summary.get("sqlite_plugin_ready")),
                "db_dropin_ready": bool(wp_php_fallback_summary.get("db_dropin_ready")),
                "bootstrap_ready": bool(wp_php_fallback_summary.get("bootstrap_ready")),
                "install_url": str(wp_php_fallback_commands.get("install_url") or ""),
            },
            "wp_platform_assets": {
                "theme_ready": bool(wp_platform_assets_summary.get("theme_ready")),
                "plugin_ready": bool(wp_platform_assets_summary.get("plugin_ready")),
                "theme_slug": str(wp_platform_assets_theme.get("slug") or ""),
                "plugin_slug": str(wp_platform_assets_plugin.get("slug") or ""),
                "public_mount_host": str(wp_platform_assets_plugin.get("public_mount_host") or wp_platform_assets_plugin.get("consumer_host") or ""),
                "lazy_iframe_policy": bool(wp_platform_assets_plugin.get("lazy_iframe_policy")),
            },
            "wordpress_platform_ia": {
                "page_count": int(wordpress_platform_ia_summary.get("page_count", 0) or 0),
                "service_page_count": int(wordpress_platform_ia_summary.get("service_page_count", 0) or 0),
                "lazy_gate_pages": list(wordpress_platform_ia_summary.get("lazy_gate_pages") or []),
                "cta_only_pages": list(wordpress_platform_ia_summary.get("cta_only_pages") or []),
                "platform_host": str(wordpress_platform_ia_topology.get("platform_host") or ""),
                "public_mount": str(wordpress_platform_ia_topology.get("public_mount") or ""),
            },
            "wp_platform_blueprints": {
                "blueprint_count": int(wp_platform_blueprints_summary.get("blueprint_count", 0) or 0),
                "lazy_gate_pages": list(wp_platform_blueprints_summary.get("lazy_gate_pages") or []),
                "cta_only_pages": list(wp_platform_blueprints_summary.get("cta_only_pages") or []),
                "navigation_ready": bool(wp_platform_blueprints_summary.get("navigation_ready")),
            },
            "wordpress_staging_apply_plan": {
                "page_step_count": int(wordpress_staging_apply_plan_summary.get("page_step_count", 0) or 0),
                "cutover_ready": bool(wordpress_staging_apply_plan_summary.get("cutover_ready")),
                "service_page_count": int(wordpress_staging_apply_plan_summary.get("service_page_count", 0) or 0),
            },
            "wp_surface_lab_apply": {
                "bundle_ready": bool(wp_surface_lab_apply_summary.get("bundle_ready")),
                "page_count": int(wp_surface_lab_apply_summary.get("page_count", 0) or 0),
                "service_page_count": int(wp_surface_lab_apply_summary.get("service_page_count", 0) or 0),
                "runtime_ready": bool(wp_surface_lab_apply_summary.get("runtime_ready")),
                "runtime_mode": str(wp_surface_lab_apply_summary.get("runtime_mode") or ""),
                "front_page_slug": str(wp_surface_lab_apply_summary.get("front_page_slug") or ""),
                "manifest_file": str(wp_surface_lab_apply_artifacts.get("manifest_file") or ""),
                "php_bundle_file": str(wp_surface_lab_apply_artifacts.get("php_bundle_file") or ""),
                "standalone_php_bundle_file": str(wp_surface_lab_apply_artifacts.get("standalone_php_bundle_file") or ""),
                "apply_attempted": bool(wp_surface_lab_apply_result.get("attempted")),
                "apply_ok": bool(wp_surface_lab_apply_result.get("ok")),
                "apply_blockers": list(wp_surface_lab_apply_result.get("blockers") or []),
            },
            "wp_surface_lab_apply_verify_cycle": {
                "ok": bool(wp_surface_lab_apply_verify_cycle_summary.get("ok")),
                "runtime_mode": str(wp_surface_lab_apply_verify_cycle_summary.get("runtime_mode") or ""),
                "runtime_running_before": bool(wp_surface_lab_apply_verify_cycle_summary.get("runtime_running_before")),
                "runtime_running_after": bool(wp_surface_lab_apply_verify_cycle_summary.get("runtime_running_after")),
                "apply_ok": bool(wp_surface_lab_apply_verify_cycle_summary.get("apply_ok")),
                "verification_ok": bool(wp_surface_lab_apply_verify_cycle_summary.get("verification_ok")),
                "blockers": list(wp_surface_lab_apply_verify_cycle_summary.get("blockers") or []),
                "step_count": int(wp_surface_lab_apply_verify_cycle_summary.get("step_count", 0) or 0),
            },
            "wp_surface_lab_page_verify": {
                "verification_ready": bool(wp_surface_lab_page_verify_summary.get("verification_ready")),
                "verification_ok": bool(wp_surface_lab_page_verify_summary.get("verification_ok")),
                "page_count": int(wp_surface_lab_page_verify_summary.get("page_count", 0) or 0),
                "service_page_count": int(wp_surface_lab_page_verify_summary.get("service_page_count", 0) or 0),
                "localhost_url": str(wp_surface_lab_page_verify_runtime.get("localhost_url") or ""),
                "blockers": list(wp_surface_lab_page_verify_summary.get("blockers") or []),
            },
            "wordpress_platform_encoding_audit": {
                "checked_file_count": int(wordpress_platform_encoding_audit_summary.get("checked_file_count", 0) or 0),
                "issue_file_count": int(wordpress_platform_encoding_audit_summary.get("issue_file_count", 0) or 0),
                "encoding_ok": bool(wordpress_platform_encoding_audit_summary.get("encoding_ok")),
            },
            "wordpress_platform_ux_audit": {
                "page_count": int(wordpress_platform_ux_audit_summary.get("page_count", 0) or 0),
                "issue_count": int(wordpress_platform_ux_audit_summary.get("issue_count", 0) or 0),
                "ux_ok": bool(wordpress_platform_ux_audit_summary.get("ux_ok")),
                "service_pages_ok": bool(wordpress_platform_ux_audit_summary.get("service_pages_ok")),
                "market_bridge_ok": bool(wordpress_platform_ux_audit_summary.get("market_bridge_ok")),
                "yangdo_recommendation_surface_ok": bool(wordpress_platform_ux_audit_summary.get("yangdo_recommendation_surface_ok")),
            },
            "wordpress_platform_strategy": {
                "primary_runtime": str(wordpress_strategy_runtime.get("primary_runtime") or ""),
                "support_runtime": str(wordpress_strategy_runtime.get("support_runtime") or ""),
                "recommended_pattern": str(wordpress_strategy_calc.get("recommended_pattern") or ""),
                "kr_host": str(wordpress_strategy_current.get("kr_host") or ""),
                "co_role": str(wordpress_strategy_current.get("co_role") or ""),
                "public_mount": str(wordpress_strategy_calc.get("private_engine_public_mount") or ""),
                "listing_site_policy": str((wordpress_strategy_calc.get("recommended_by_page") or {}).get("listing_site_policy") or ""),
                "keep_live": list(wordpress_strategy_plugin_stack.get("keep_live") or []),
                "stage_first": list(wordpress_strategy_plugin_stack.get("stage_first") or []),
                "avoid_live_duplication": list(wordpress_strategy_plugin_stack.get("avoid_live_duplication") or []),
            },
            "astra_design_reference": {
                "theme_name": str(astra_theme.get("theme_name") or ""),
                "theme_version": str(astra_theme.get("theme_version") or ""),
                "strategy": str(astra_decision.get("strategy") or ""),
                "usable_for_next_front": list(astra_decision.get("usable_for_next_front") or []),
            },
            "kr_reverse_proxy_cutover": {
                "cutover_ready": bool(kr_reverse_proxy_cutover_summary.get("cutover_ready")),
                "service_page_count": int(kr_reverse_proxy_cutover_summary.get("service_page_count", 0) or 0),
                "traffic_gate_ok": bool(kr_reverse_proxy_cutover_summary.get("traffic_gate_ok")),
                "public_mount_base": str(kr_reverse_proxy_cutover_topology.get("public_mount_base") or ""),
                "private_engine_origin": str(kr_reverse_proxy_cutover_topology.get("private_engine_origin") or ""),
            },
            "kr_traffic_gate": {
                "traffic_leak_blocked": bool(kr_traffic_decision.get("traffic_leak_blocked")),
                "remaining_risks": list(kr_traffic_decision.get("remaining_risks") or []),
                "server_started": bool(kr_traffic_live_probe.get("server_started")),
                "all_routes_no_iframe": bool(kr_traffic_live_probe.get("all_routes_no_iframe")),
            },
            "partner": {
                "tenant_count": len(partner_tenants),
                "channel_count": len(partner_channels),
                "ready_tenant_count": len([row for row in partner_tenants if bool(row.get("activation_ready"))]),
                "ready_channel_count": len([row for row in partner_channels if bool(row.get("activation_ready"))]),
                "latest_flow_ok": bool(partner_flow.get("ok")),
                "latest_flow_scope_registered": partner_flow_scope_registered,
                "latest_flow_blockers": partner_blockers,
                "latest_flow_resolved_inputs": latest_flow_resolved_inputs,
                "latest_flow_remaining_required_inputs": latest_flow_remaining_required_inputs,
                "latest_flow_next_actions": _normalize_next_actions(latest_flow_remaining_required_inputs, list(partner_handoff.get("next_actions") or [])),
                "checklists": partner_checklists,
                "preview_recommended_scenario": preview_recommended_scenario,
                "preview_remaining_required_inputs": preview_remaining_required_inputs,
                "preview_removed_inputs": preview_removed_inputs,
                "preview_next_actions": preview_next_actions,
                "preview_alignment": alignment_summary,
                "resolution_summary": resolution_summary,
                "input_snapshot_summary": input_snapshot_summary,
                "simulation_matrix_summary": simulation_summary,
                "common_required_inputs": common_required_inputs,
                "uniform_required_inputs": uniform_required_inputs,
            },
            "yangdo_recommendation_qa": {
                "qa_ok": bool(recommendation_qa_summary.get("qa_ok")),
                "scenario_count": int(recommendation_qa_summary.get("scenario_count", 0) or 0),
                "passed_count": int(recommendation_qa_summary.get("passed_count", 0) or 0),
                "failed_count": int(recommendation_qa_summary.get("failed_count", 0) or 0),
                "strict_profile_regression_ok": bool(recommendation_qa_summary.get("strict_profile_regression_ok")),
                "fallback_regression_ok": bool(recommendation_qa_summary.get("fallback_regression_ok")),
                "balance_exclusion_regression_ok": bool(recommendation_qa_summary.get("balance_exclusion_regression_ok")),
                "assistive_precision_regression_ok": bool(recommendation_qa_summary.get("assistive_precision_regression_ok")),
                "summary_projection_regression_ok": bool(recommendation_qa_summary.get("summary_projection_regression_ok")),
                "precision_counts": recommendation_qa_summary.get("precision_counts") if isinstance(recommendation_qa_summary.get("precision_counts"), dict) else {},
            },
            "yangdo_recommendation_precision_matrix": {
                "precision_ok": bool(recommendation_precision_summary.get("precision_ok")),
                "scenario_count": int(recommendation_precision_summary.get("scenario_count", 0) or 0),
                "passed_count": int(recommendation_precision_summary.get("passed_count", 0) or 0),
                "failed_count": int(recommendation_precision_summary.get("failed_count", 0) or 0),
                "high_precision_ok": bool(recommendation_precision_summary.get("high_precision_ok")),
                "fallback_precision_ok": bool(recommendation_precision_summary.get("fallback_precision_ok")),
                "balance_excluded_precision_ok": bool(recommendation_precision_summary.get("balance_excluded_precision_ok")),
                "assist_precision_ok": bool(recommendation_precision_summary.get("assist_precision_ok")),
                "summary_publication_ok": bool(recommendation_precision_summary.get("summary_publication_ok")),
                "detail_explainability_ok": bool(recommendation_precision_summary.get("detail_explainability_ok")),
                "sector_groups": recommendation_precision_summary.get("sector_groups") if isinstance(recommendation_precision_summary.get("sector_groups"), dict) else {},
                "price_bands": recommendation_precision_summary.get("price_bands") if isinstance(recommendation_precision_summary.get("price_bands"), dict) else {},
                "response_tiers": recommendation_precision_summary.get("response_tiers") if isinstance(recommendation_precision_summary.get("response_tiers"), dict) else {},
                "precision_counts": recommendation_precision_summary.get("precision_counts") if isinstance(recommendation_precision_summary.get("precision_counts"), dict) else {},
            },
            "yangdo_recommendation_diversity_audit": {
                "diversity_ok": bool(recommendation_diversity_summary.get("diversity_ok")),
                "scenario_count": int(recommendation_diversity_summary.get("scenario_count", 0) or 0),
                "passed_count": int(recommendation_diversity_summary.get("passed_count", 0) or 0),
                "failed_count": int(recommendation_diversity_summary.get("failed_count", 0) or 0),
                "top1_stability_ok": bool(recommendation_diversity_summary.get("top1_stability_ok")),
                "price_band_spread_ok": bool(recommendation_diversity_summary.get("price_band_spread_ok")),
                "focus_signature_spread_ok": bool(recommendation_diversity_summary.get("focus_signature_spread_ok")),
                "detail_projection_contract_ok": bool(recommendation_diversity_summary.get("detail_projection_contract_ok")),
                "precision_tier_spread_ok": bool(recommendation_diversity_summary.get("precision_tier_spread_ok")),
                "unique_listing_ok": bool(recommendation_diversity_summary.get("unique_listing_ok")),
                "listing_bridge_ok": bool(recommendation_diversity_summary.get("listing_bridge_ok")),
                "listing_band_spread_ok": bool(recommendation_diversity_summary.get("listing_band_spread_ok")),
                "cluster_concentration_ok": bool(recommendation_diversity_summary.get("cluster_concentration_ok")),
                "top_rank_signature_concentration_ok": bool(recommendation_diversity_summary.get("top_rank_signature_concentration_ok")),
                "price_band_concentration_ok": bool(recommendation_diversity_summary.get("price_band_concentration_ok")),
            },
            "yangdo_recommendation_contract_audit": {
                "contract_ok": bool(recommendation_contract_summary.get("contract_ok")),
                "summary_safe": bool(recommendation_contract_summary.get("summary_safe")),
                "detail_explainable": bool(recommendation_contract_summary.get("detail_explainable")),
                "internal_debug_visible": bool(recommendation_contract_summary.get("internal_debug_visible")),
            },
            "yangdo_recommendation_bridge": {
                "packet_ready": bool(recommendation_bridge_summary.get("packet_ready")),
                "service_slug": str(recommendation_bridge_summary.get("service_slug") or ""),
                "platform_host": str(recommendation_bridge_summary.get("platform_host") or ""),
                "listing_host": str(recommendation_bridge_summary.get("listing_host") or ""),
                "market_bridge_ready": bool(recommendation_bridge_summary.get("market_bridge_ready")),
                "rental_ready": bool(recommendation_bridge_summary.get("rental_ready")),
                "supported_precision_labels": list(recommendation_bridge_summary.get("supported_precision_labels") or []),
                "public_summary_fields": list(recommendation_bridge_public.get("fields") or []),
                "detail_fields": list(((yangdo_recommendation_bridge_packet.get("detail_contract") or {}).get("fields") or [])),
                "summary_offerings": list(recommendation_bridge_rental.get("summary_offerings") or []),
                "detail_offerings": list(recommendation_bridge_rental.get("detail_offerings") or []),
                "internal_offerings": list(recommendation_bridge_rental.get("internal_offerings") or []),
                "summary_policy": str(recommendation_bridge_rental.get("summary_policy") or ""),
                "detail_policy": str(recommendation_bridge_rental.get("detail_policy") or ""),
                "internal_policy": str(recommendation_bridge_rental.get("internal_policy") or ""),
            },
            "yangdo_recommendation_ux": {
                "packet_ready": bool(recommendation_ux_summary.get("packet_ready")),
                "service_surface_ready": bool(recommendation_ux_summary.get("service_surface_ready")),
                "market_bridge_ready": bool(recommendation_ux_summary.get("market_bridge_ready")),
                "rental_exposure_ready": bool(recommendation_ux_summary.get("rental_exposure_ready")),
                "precision_ready": bool(recommendation_ux_summary.get("precision_ready")),
                "detail_explainability_ready": bool(recommendation_ux_summary.get("detail_explainability_ready")),
                "service_flow_policy": str(recommendation_ux_summary.get("service_flow_policy") or ""),
                "public_primary_cta": str(recommendation_ux_public.get("cta_primary_label") or ""),
                "public_secondary_cta": str(recommendation_ux_public.get("cta_secondary_label") or ""),
                "public_fields": list(recommendation_ux_public.get("visible_fields") or []),
                "detail_explainable_fields": list(recommendation_ux_detail_explainable.get("visible_fields") or []),
                "detail_fields": list(recommendation_ux_detail.get("visible_fields") or []),
                "standard_offerings": list(((recommendation_ux_matrix.get("standard") or {}).get("offerings") or [])),
                "pro_detail_offerings": list(((recommendation_ux_matrix.get("pro_detail") or {}).get("offerings") or [])),
                "pro_consult_offerings": list(((recommendation_ux_matrix.get("pro_consult") or {}).get("offerings") or [])),
                "internal_offerings": list(((recommendation_ux_matrix.get("internal") or {}).get("offerings") or [])),
            },
            "yangdo_recommendation_alignment": {
                "alignment_ok": bool(recommendation_alignment_summary.get("alignment_ok")),
                "issue_count": int(recommendation_alignment_summary.get("issue_count", 0) or 0),
                "service_flow_policy_ok": bool(recommendation_alignment_summary.get("service_flow_policy_ok")),
                "cta_labels_ok": bool(recommendation_alignment_summary.get("cta_labels_ok")),
                "field_contract_ok": bool(recommendation_alignment_summary.get("field_contract_ok")),
                "offering_exposure_ok": bool(recommendation_alignment_summary.get("offering_exposure_ok")),
                "patent_handoff_ok": bool(recommendation_alignment_summary.get("patent_handoff_ok")),
                "contract_story_ok": bool(recommendation_alignment_summary.get("contract_story_ok")),
                "supported_labels_ok": bool(recommendation_alignment_summary.get("supported_labels_ok")),
            },
            "yangdo_zero_display_recovery_audit": {
                "zero_display_guard_ok": bool(zero_display_recovery_summary.get("zero_display_guard_ok")),
                "zero_display_total": int(zero_display_recovery_summary.get("zero_display_total", 0) or 0),
                "selected_lane_ok": bool(zero_display_recovery_summary.get("selected_lane_ok")),
                "runtime_ready": bool(zero_display_recovery_summary.get("runtime_ready")),
                "contract_policy_ok": bool(zero_display_recovery_summary.get("contract_policy_ok")),
                "market_bridge_route_ok": bool(zero_display_recovery_summary.get("market_bridge_route_ok")),
                "consult_first_ready": bool(zero_display_recovery_summary.get("consult_first_ready")),
                "zero_policy_ready": bool(zero_display_recovery_summary.get("zero_policy_ready")),
                "market_cta_ready": bool(zero_display_recovery_summary.get("market_cta_ready")),
                "consult_lane_ready": bool(zero_display_recovery_summary.get("consult_lane_ready")),
                "patent_hook_ready": bool(zero_display_recovery_summary.get("patent_hook_ready")),
            },
            "yangdo_service_copy": {
                "packet_ready": bool(yangdo_service_copy_summary.get("packet_ready")),
                "service_copy_ready": bool(yangdo_service_copy_summary.get("service_copy_ready")),
                "low_precision_consult_first_ready": bool(yangdo_service_copy_summary.get("low_precision_consult_first_ready")),
                "market_bridge_story_ready": bool(yangdo_service_copy_summary.get("market_bridge_story_ready")),
                "market_fit_interpretation_ready": bool(yangdo_service_copy_summary.get("market_fit_interpretation_ready")),
                "lane_stories_ready": bool(yangdo_service_copy_summary.get("lane_stories_ready")),
                "lane_ladder_ready": yangdo_recommendation_lane_ladder_ready,
                "detail_explainable_lane_ready": detail_explainable_lane_ready,
                "consult_assist_lane_ready": consult_assist_lane_ready,
                "precision_lane_contract_ready": precision_lane_contract_ready,
                "service_slug": str(yangdo_service_copy_summary.get("service_slug") or ""),
                "platform_host": str(yangdo_service_copy_summary.get("platform_host") or ""),
                "listing_host": str(yangdo_service_copy_summary.get("listing_host") or ""),
                "precision_label_count": int(yangdo_service_copy_summary.get("precision_label_count", 0) or 0),
                "hero_title": str(yangdo_service_copy_hero.get("title") or ""),
                "primary_market_bridge_cta": str(((yangdo_service_copy_cta_ladder.get("primary_market_bridge") or {}).get("label")) or ""),
                "secondary_consult_cta": str(((yangdo_service_copy_cta_ladder.get("secondary_consult") or {}).get("label")) or ""),
                "summary_market_bridge_offerings": list(yangdo_service_copy_offering_matrix.get("summary_market_bridge") or []),
                "detail_explainable_offerings": list(yangdo_service_copy_offering_matrix.get("detail_explainable") or []),
                "consult_assist_offerings": list(yangdo_service_copy_offering_matrix.get("consult_assist") or []),
                "internal_full_offerings": list(yangdo_service_copy_offering_matrix.get("internal_full") or []),
            },
            "permit_service_copy": {
                "packet_ready": bool(permit_service_copy_summary.get("packet_ready")),
                "service_copy_ready": bool(permit_service_copy_summary.get("service_copy_ready")),
                "checklist_story_ready": bool(permit_service_copy_summary.get("checklist_story_ready")),
                "manual_review_story_ready": bool(permit_service_copy_summary.get("manual_review_story_ready")),
                "document_story_ready": bool(permit_service_copy_summary.get("document_story_ready")),
                "lane_ladder_ready": bool(permit_service_copy_summary.get("lane_ladder_ready")),
                "service_flow_ready": bool(permit_service_copy_summary.get("service_flow_ready")),
                "service_slug": str(permit_service_copy_summary.get("service_slug") or ""),
                "platform_host": str(permit_service_copy_summary.get("platform_host") or ""),
                "hero_title": str(permit_service_copy_hero.get("title") or ""),
                "primary_self_check_cta": str(((permit_service_copy_cta_ladder.get("primary_self_check") or {}).get("label")) or ""),
                "secondary_consult_cta": str(((permit_service_copy_cta_ladder.get("secondary_consult") or {}).get("label")) or ""),
                "knowledge_cta": str(((permit_service_copy_cta_ladder.get("supporting_knowledge") or {}).get("label")) or ""),
                "detail_checklist_upgrade_target": str(((permit_service_copy_lane_ladder.get("detail_checklist") or {}).get("upgrade_target")) or ""),
                "manual_review_assist_upgrade_target": str(((permit_service_copy_lane_ladder.get("manual_review_assist") or {}).get("upgrade_target")) or ""),
                "summary_self_check_offerings": list(permit_service_copy_offering_matrix.get("summary_self_check") or []),
                "detail_checklist_offerings": list(permit_service_copy_offering_matrix.get("detail_checklist") or []),
                "manual_review_assist_offerings": list(permit_service_copy_offering_matrix.get("manual_review_assist") or []),
            },
            "permit_service_alignment": {
                "alignment_ok": bool(permit_service_alignment_summary.get("alignment_ok")),
                "issue_count": int(permit_service_alignment_summary.get("issue_count", 0) or 0),
                "cta_contract_ok": bool(permit_service_alignment_summary.get("cta_contract_ok")),
                "proof_point_contract_ok": bool(permit_service_alignment_summary.get("proof_point_contract_ok")),
                "service_story_ok": bool(permit_service_alignment_summary.get("service_story_ok")),
                "lane_positioning_ok": bool(permit_service_alignment_summary.get("lane_positioning_ok")),
                "rental_positioning_ok": bool(permit_service_alignment_summary.get("rental_positioning_ok")),
                "patent_handoff_ok": bool(permit_service_alignment_summary.get("patent_handoff_ok")),
                "permit_offering_count": int(permit_service_alignment_summary.get("permit_offering_count", 0) or 0),
            },
            "permit_rental_lane": {
                "packet_ready": bool(permit_rental_lane_summary.get("packet_ready")),
                "commercial_story_ready": bool(permit_rental_lane_summary.get("commercial_story_ready")),
                "detail_checklist_lane_ready": bool(permit_rental_lane_summary.get("detail_checklist_lane_ready")),
                "manual_review_assist_lane_ready": bool(permit_rental_lane_summary.get("manual_review_assist_lane_ready")),
                "summary_self_check_offerings": list(((permit_rental_lane_matrix.get("summary_self_check") or {}).get("offerings") or [])),
                "detail_checklist_offerings": list(((permit_rental_lane_matrix.get("detail_checklist") or {}).get("offerings") or [])),
                "manual_review_assist_offerings": list(((permit_rental_lane_matrix.get("manual_review_assist") or {}).get("offerings") or [])),
            },
            "permit_service_ux": {
                "packet_ready": bool(permit_service_ux_summary.get("packet_ready")),
                "service_surface_ready": bool(permit_service_ux_summary.get("service_surface_ready")),
                "lane_exposure_ready": bool(permit_service_ux_summary.get("lane_exposure_ready")),
                "alignment_ready": bool(permit_service_ux_summary.get("alignment_ready")),
                "service_flow_policy": str(permit_service_ux_summary.get("service_flow_policy") or ""),
                "public_allowed_offerings": list(permit_service_ux_public.get("allowed_offerings") or []),
                "detail_allowed_offerings": list(permit_service_ux_detail.get("allowed_offerings") or []),
                "assist_allowed_offerings": list(permit_service_ux_assist.get("allowed_offerings") or []),
                "primary_self_check_cta": str(permit_service_ux_public.get("cta_primary_label") or ""),
                "detail_cta": str(permit_service_ux_detail.get("cta_primary_label") or ""),
                "assist_cta": str(permit_service_ux_assist.get("cta_primary_label") or ""),
            },
            "permit_public_contract": {
                "contract_ok": bool(permit_public_contract_summary.get("contract_ok")),
                "issue_count": int(permit_public_contract_summary.get("issue_count", 0) or 0),
                "public_summary_only_ok": bool(permit_public_contract_summary.get("public_summary_only_ok")),
                "detail_checklist_contract_ok": bool(permit_public_contract_summary.get("detail_checklist_contract_ok")),
                "assist_contract_ok": bool(permit_public_contract_summary.get("assist_contract_ok")),
                "internal_visibility_ok": bool(permit_public_contract_summary.get("internal_visibility_ok")),
                "offering_exposure_ok": bool(permit_public_contract_summary.get("offering_exposure_ok")),
                "patent_handoff_ok": bool(permit_public_contract_summary.get("patent_handoff_ok")),
            },
            "partner_input_handoff": {
                "partner_count": int(partner_input_handoff_summary.get("partner_count", 0) or 0),
                "uniform_required_inputs": bool(partner_input_handoff_summary.get("uniform_required_inputs")),
                "common_required_inputs": list(partner_input_handoff_summary.get("common_required_inputs") or []),
                "ready_after_recommended_injection": bool(partner_input_handoff_summary.get("ready_after_recommended_injection")),
                "ready_after_recommended_injection_count": int(partner_input_handoff_summary.get("ready_after_recommended_injection_count", 0) or 0),
                "copy_paste_ready": bool(partner_input_handoff_summary.get("copy_paste_ready")),
            },
            "partner_input_operator_flow": {
                "packet_ready": bool(partner_input_operator_flow_summary.get("packet_ready")),
                "partner_count": int(partner_input_operator_flow_summary.get("partner_count", 0) or 0),
                "copy_paste_ready": bool(partner_input_operator_flow_summary.get("copy_paste_ready")),
                "common_required_inputs": list(partner_input_operator_flow_summary.get("common_required_inputs") or []),
                "ready_after_recommended_injection": bool(partner_input_operator_flow_summary.get("ready_after_recommended_injection")),
                "recommended_sequence": list(partner_input_operator_flow_summary.get("recommended_sequence") or []),
            },
            "ai_platform_first_principles_review": {
                "packet_ready": bool(ai_platform_first_principles_summary.get("packet_ready")),
                "blocking_issue_count": int(ai_platform_first_principles_summary.get("blocking_issue_count", 0) or 0),
                "current_bottleneck": str(ai_platform_first_principles_summary.get("current_bottleneck") or ""),
                "next_experiment_count": int(ai_platform_first_principles_summary.get("next_experiment_count", 0) or 0),
            },
            "system_split_first_principles": {
                "packet_ready": bool(system_split_first_principles_summary.get("packet_ready")),
                "platform_ready": bool(system_split_first_principles_summary.get("platform_ready")),
                "yangdo_ready": bool(system_split_first_principles_summary.get("yangdo_ready")),
                "permit_ready": bool(system_split_first_principles_summary.get("permit_ready")),
                "prompt_count": int(system_split_first_principles_summary.get("prompt_count", 0) or 0),
            },
            "widget_rental_catalog": {
                "offering_count": int(widget_rental_summary.get("offering_count", 0) or 0),
                "standard_offering_count": int(widget_rental_summary.get("standard_offering_count", 0) or 0),
                "pro_offering_count": int(widget_rental_summary.get("pro_offering_count", 0) or 0),
                "combo_offering_count": int(widget_rental_summary.get("combo_offering_count", 0) or 0),
                "yangdo_recommendation_offering_count": int(widget_rental_summary.get("yangdo_recommendation_offering_count", 0) or 0),
                "yangdo_recommendation_standard_count": int(widget_rental_summary.get("yangdo_recommendation_standard_count", 0) or 0),
                "yangdo_recommendation_detail_count": int(widget_rental_summary.get("yangdo_recommendation_detail_count", 0) or 0),
                "yangdo_recommendation_summary_bridge_count": int(widget_rental_summary.get("yangdo_recommendation_summary_bridge_count", 0) or 0),
                "yangdo_recommendation_detail_lane_count": int(widget_rental_summary.get("yangdo_recommendation_detail_lane_count", 0) or 0),
                "yangdo_recommendation_consult_assist_count": int(widget_rental_summary.get("yangdo_recommendation_consult_assist_count", 0) or 0),
                "internal_tenant_count": int(widget_rental_summary.get("internal_tenant_count", 0) or 0),
                "public_platform_host": str(widget_rental_summary.get("public_platform_host") or ""),
                "listing_market_host": str(widget_rental_summary.get("listing_market_host") or ""),
                "widget_standard": list((widget_rental_packaging.get("partner_rental") or {}).get("widget_standard") or []),
                "api_or_detail_pro": list((widget_rental_packaging.get("partner_rental") or {}).get("api_or_detail_pro") or []),
                "yangdo_recommendation_summary": list((((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation") or {}).get("summary_offerings") or [])),
                "yangdo_recommendation_detail": list((((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation") or {}).get("detail_offerings") or [])),
                "yangdo_recommendation_package_matrix": (
                    (((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation") or {}).get("package_matrix"))
                    if isinstance((((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation") or {}).get("package_matrix")), dict)
                    else {}
                ),
                "yangdo_recommendation_lane_positioning": yangdo_recommendation_lane_positioning,
                "yangdo_recommendation_summary_policy": str((((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation") or {}).get("summary_policy") or "")),
                "yangdo_recommendation_detail_policy": str((((widget_rental_packaging.get("partner_rental") or {}).get("yangdo_recommendation") or {}).get("detail_policy") or "")),
            },
            "listing_platform_bridge_policy": {
                "platform_host": str(listing_bridge_summary.get("platform_host") or ""),
                "listing_host": str(listing_bridge_summary.get("listing_host") or ""),
                "cta_count": int(listing_bridge_summary.get("cta_count", 0) or 0),
                "routing_rule_count": int(listing_bridge_summary.get("routing_rule_count", 0) or 0),
                "listing_runtime_policy": str(listing_bridge_summary.get("listing_runtime_policy") or ""),
                "calculator_runtime_policy": str(listing_bridge_policy_section.get("calculator_runtime_policy") or ""),
                "sample_target": str((listing_bridge_ctas[0] if listing_bridge_ctas else {}).get("target_url") or ""),
            },
            "co_listing_bridge_snippets": {
                "listing_host": str(co_listing_bridge_snippets_summary.get("listing_host") or ""),
                "platform_host": str(co_listing_bridge_snippets_summary.get("platform_host") or ""),
                "placement_count": int(co_listing_bridge_snippets_summary.get("placement_count", 0) or 0),
                "snippet_file_count": int(co_listing_bridge_snippets_summary.get("snippet_file_count", 0) or 0),
                "output_dir": str(co_listing_bridge_snippets_summary.get("output_dir") or ""),
                "combined_file": str(co_listing_bridge_snippets_summary.get("combined_file") or ""),
            },
            "co_listing_bridge_operator_checklist": {
                "listing_host": str(co_listing_bridge_operator_checklist_summary.get("listing_host") or ""),
                "platform_host": str(co_listing_bridge_operator_checklist_summary.get("platform_host") or ""),
                "placement_count": int(co_listing_bridge_operator_checklist_summary.get("placement_count", 0) or 0),
                "checklist_ready": bool(co_listing_bridge_operator_checklist_summary.get("checklist_ready")),
                "css_file": str(co_listing_bridge_operator_checklist_summary.get("css_file") or ""),
                "combined_file": str(co_listing_bridge_operator_checklist_summary.get("combined_file") or ""),
            },
            "co_listing_live_injection_plan": {
                "listing_host": str(co_listing_live_injection_plan_summary.get("listing_host") or ""),
                "platform_host": str(co_listing_live_injection_plan_summary.get("platform_host") or ""),
                "placement_count": int(co_listing_live_injection_plan_summary.get("placement_count", 0) or 0),
                "selector_verified_count": int(co_listing_live_injection_plan_summary.get("selector_verified_count", 0) or 0),
                "plan_ready": bool(co_listing_live_injection_plan_summary.get("plan_ready")),
                "detail_sample_url": str(co_listing_live_injection_plan_summary.get("detail_sample_url") or ""),
            },
            "co_listing_injection_bundle": {
                "bundle_ready": bool(co_listing_injection_bundle_summary.get("bundle_ready")),
                "placement_count": int(co_listing_injection_bundle_summary.get("placement_count", 0) or 0),
                "output_dir": str(co_listing_injection_bundle_summary.get("output_dir") or ""),
            },
            "co_listing_bridge_apply_packet": {
                "apply_ready": bool(co_listing_bridge_apply_packet_summary.get("apply_ready")),
                "placement_count": int(co_listing_bridge_apply_packet_summary.get("placement_count", 0) or 0),
                "placement_ready_count": int(co_listing_bridge_apply_packet_summary.get("placement_ready_count", 0) or 0),
                "css_file": str(co_listing_bridge_apply_packet_summary.get("css_file") or ""),
                "bundle_script": str(co_listing_bridge_apply_packet_summary.get("bundle_script") or ""),
            },
            "kr_proxy_server_matrix": {
                "matrix_ready": bool(kr_proxy_server_summary.get("matrix_ready")),
                "traffic_gate_ok": bool(kr_proxy_server_summary.get("traffic_gate_ok")),
                "cutover_ready": bool(kr_proxy_server_summary.get("cutover_ready")),
                "public_mount_path": str(kr_proxy_server_summary.get("public_mount_path") or ""),
                "upstream_origin": str(kr_proxy_server_summary.get("upstream_origin") or ""),
                "nginx_snippet": str(kr_proxy_nginx.get("snippet") or ""),
            },
            "kr_proxy_server_bundle": {
                "bundle_ready": bool(kr_proxy_server_bundle_summary.get("bundle_ready")),
                "public_mount_path": str(kr_proxy_server_bundle_summary.get("public_mount_path") or ""),
                "upstream_origin": str(kr_proxy_server_bundle_summary.get("upstream_origin") or ""),
                "output_dir": str(kr_proxy_server_bundle_summary.get("output_dir") or ""),
                "file_count": int(kr_proxy_server_bundle_summary.get("file_count", 0) or 0),
            },
            "kr_live_apply_packet": {
                "apply_packet_ready": bool(kr_live_apply_summary.get("apply_packet_ready")),
                "page_count": int(kr_live_apply_summary.get("page_count", 0) or 0),
                "service_page_count": int(kr_live_apply_summary.get("service_page_count", 0) or 0),
                "front_page_slug": str(kr_live_apply_summary.get("front_page_slug") or ""),
                "menu_name": str(kr_live_apply_summary.get("menu_name") or ""),
                "bridge_cta_count": int(kr_live_apply_summary.get("bridge_cta_count", 0) or 0),
            },
            "kr_live_operator_checklist": {
                "checklist_ready": bool(kr_live_operator_summary.get("checklist_ready")),
                "platform_host": str(kr_live_operator_summary.get("platform_host") or ""),
                "listing_host": str(kr_live_operator_summary.get("listing_host") or ""),
                "public_mount_path": str(kr_live_operator_summary.get("public_mount_path") or ""),
                "preflight_item_count": int(kr_live_operator_summary.get("preflight_item_count", 0) or 0),
                "validation_step_count": int(kr_live_operator_summary.get("validation_step_count", 0) or 0),
                "operator_input_count": int(kr_live_operator_summary.get("operator_input_count", 0) or 0),
            },
            "program_improvement_loop": {
                "immediate_blocker_count": int(improvement_summary.get("immediate_blocker_count", 0) or 0),
                "structural_improvement_count": int(improvement_summary.get("structural_improvement_count", 0) or 0),
                "patent_hardening_count": int(improvement_summary.get("patent_hardening_count", 0) or 0),
                "commercialization_gap_count": int(improvement_summary.get("commercialization_gap_count", 0) or 0),
                "top_action_count": int(improvement_summary.get("top_action_count", 0) or 0),
                "top_next_actions": improvement_top_actions[:5],
            },
        },
    }


def _to_markdown(packet: Dict[str, Any]) -> str:
    lines: List[str] = []
    go_live = packet.get("go_live") if isinstance(packet.get("go_live"), dict) else {}
    decisions = packet.get("decisions") if isinstance(packet.get("decisions"), dict) else {}
    topology = packet.get("topology") if isinstance(packet.get("topology"), dict) else {}
    kr_platform = (packet.get("summaries") or {}).get("kr_platform") if isinstance((packet.get("summaries") or {}).get("kr_platform"), dict) else {}
    partner_summary = (packet.get("summaries") or {}).get("partner") if isinstance((packet.get("summaries") or {}).get("partner"), dict) else {}
    required = packet.get("required_inputs") if isinstance(packet.get("required_inputs"), dict) else {}
    preview_alignment = partner_summary.get("preview_alignment") if isinstance(partner_summary.get("preview_alignment"), dict) else {}

    lines.append("# Operations Packet")
    lines.append("")
    lines.append("## Topology")
    lines.append(f"- main_platform_host: {topology.get('main_platform_host')}")
    lines.append(f"- main_platform_role: {topology.get('main_platform_role')}")
    lines.append(f"- listing_market_host: {topology.get('listing_market_host')}")
    lines.append(f"- listing_market_role: {topology.get('listing_market_role')}")
    lines.append(f"- public_calculator_mount_host: {topology.get('public_calculator_mount_host')}")
    lines.append(f"- private_engine_public_path: {topology.get('private_engine_public_path')}")
    lines.append(f"- engine_visibility: {topology.get('engine_visibility')}")
    lines.append(f"- front_platform_status: {topology.get('front_platform_status')}")
    lines.append("")
    lines.append("## Go Live")
    lines.append(f"- quality_green: {go_live.get('quality_green')}")
    lines.append(f"- release_ready: {go_live.get('release_ready')}")
    lines.append(f"- runtime_verified: {go_live.get('runtime_verified')}")
    lines.append(f"- release_report_ok: {go_live.get('release_report_ok')}")
    lines.append(f"- seoul_live_decision: {decisions.get('seoul_live_decision')}")
    lines.append(f"- kr_platform_decision: {decisions.get('kr_platform_decision')}")
    lines.append(f"- kr_wordpress_platform_decision: {decisions.get('kr_wordpress_platform_decision')}")
    lines.append(f"- kr_next_lane_decision: {decisions.get('kr_next_lane_decision')}")
    lines.append(f"- wp_runtime_decision: {decisions.get('wp_runtime_decision')}")
    lines.append(f"- wp_surface_apply_decision: {decisions.get('wp_surface_apply_decision')}")
    lines.append(f"- wordpress_encoding_decision: {decisions.get('wordpress_encoding_decision')}")
    lines.append(f"- wordpress_ux_decision: {decisions.get('wordpress_ux_decision')}")
    lines.append(f"- wordpress_ia_decision: {decisions.get('wordpress_ia_decision')}")
    lines.append(f"- reverse_proxy_cutover_decision: {decisions.get('reverse_proxy_cutover_decision')}")
    lines.append(f"- partner_activation_decision: {decisions.get('partner_activation_decision')}")
    lines.append(f"- yangdo_recommendation_qa_ok: {decisions.get('yangdo_recommendation_qa_ok')}")
    lines.append(f"- yangdo_recommendation_precision_ok: {decisions.get('yangdo_recommendation_precision_ok')}")
    lines.append(f"- yangdo_recommendation_diversity_ok: {decisions.get('yangdo_recommendation_diversity_ok')}")
    lines.append(f"- yangdo_recommendation_concentration_ok: {decisions.get('yangdo_recommendation_concentration_ok')}")
    lines.append(f"- yangdo_recommendation_contract_ok: {decisions.get('yangdo_recommendation_contract_ok')}")
    lines.append(f"- yangdo_recommendation_bridge_ready: {decisions.get('yangdo_recommendation_bridge_ready')}")
    lines.append(f"- yangdo_recommendation_ux_ready: {decisions.get('yangdo_recommendation_ux_ready')}")
    lines.append(f"- yangdo_recommendation_lane_ladder_ready: {decisions.get('yangdo_recommendation_lane_ladder_ready')}")
    lines.append(f"- yangdo_zero_display_guard_ok: {decisions.get('yangdo_zero_display_guard_ok')}")
    lines.append(f"- yangdo_service_copy_ready: {decisions.get('yangdo_service_copy_ready')}")
    lines.append(f"- permit_service_copy_ready: {decisions.get('permit_service_copy_ready')}")
    lines.append(f"- permit_lane_ladder_ready: {decisions.get('permit_lane_ladder_ready')}")
    lines.append(f"- permit_service_alignment_ok: {decisions.get('permit_service_alignment_ok')}")
    lines.append(f"- permit_service_ux_ready: {decisions.get('permit_service_ux_ready')}")
    lines.append(f"- permit_public_contract_ok: {decisions.get('permit_public_contract_ok')}")
    lines.append(f"- partner_input_handoff_ready: {decisions.get('partner_input_handoff_ready')}")
    lines.append(f"- partner_input_operator_flow_ready: {decisions.get('partner_input_operator_flow_ready')}")
    lines.append(f"- ai_platform_first_principles_ready: {decisions.get('ai_platform_first_principles_ready')}")
    lines.append(f"- system_split_first_principles_ready: {decisions.get('system_split_first_principles_ready')}")
    lines.append(f"- next_batch_focus_ready: {decisions.get('next_batch_focus_ready')}")
    if decisions.get("next_batch_focus_track"):
        lines.append(f"- next_batch_focus_track: {decisions.get('next_batch_focus_track')}")
        lines.append(f"- next_batch_focus_lane_id: {decisions.get('next_batch_focus_lane_id')}")
    if decisions.get("partner_fastest_path_scenario"):
        lines.append(f"- partner_fastest_path_scenario: {decisions.get('partner_fastest_path_scenario')}")
        lines.append(f"- partner_fastest_path_ready: {decisions.get('partner_fastest_path_ready')}")
        lines.append(f"- partner_preview_alignment_ok: {decisions.get('partner_preview_alignment_ok')}")
        lines.append(f"- partner_resolution_ok: {decisions.get('partner_resolution_ok')}")
        lines.append(f"- partner_resolution_actionable: {decisions.get('partner_resolution_actionable')}")
        lines.append(f"- partner_input_snapshot_ready_count: {decisions.get('partner_input_snapshot_ready_count')}")
        lines.append(f"- partner_simulation_ready_count: {decisions.get('partner_simulation_ready_count')}")
        lines.append(f"- partner_simulation_all_ready: {decisions.get('partner_simulation_all_ready')}")
        lines.append(f"- partner_uniform_required_inputs: {decisions.get('partner_uniform_required_inputs')}")
        lines.append(f"- partner_flow_scope_registered: {decisions.get('partner_flow_scope_registered')}")

    lines.append("")
    release_summary = (packet.get("summaries") or {}).get("release") if isinstance((packet.get("summaries") or {}).get("release"), dict) else {}
    rollback_summary = release_summary.get("rollback") if isinstance(release_summary.get("rollback"), dict) else {}
    if rollback_summary:
        lines.append("## Rollback")
        lines.append(f"- rollback_required: {rollback_summary.get('rollback_required')}")
        lines.append(f"- rollback_reason: {rollback_summary.get('rollback_reason')}")
        lines.append(f"- backup_available: {rollback_summary.get('backup_available')}")
        if rollback_summary.get("backup_manifest"):
            lines.append(f"- backup_manifest: {rollback_summary.get('backup_manifest')}")
        if rollback_summary.get("rollback_command"):
            lines.append(f"- rollback_command: {rollback_summary.get('rollback_command')}")
        for item in rollback_summary.get("recommended_actions") or []:
            lines.append(f"- rollback_next_action: {item}")
        lines.append("")

    if kr_platform:
        lines.append("## KR Platform")
        lines.append(f"- status: {kr_platform.get('status')}")
        lines.append(f"- primary_lane: {kr_platform.get('primary_lane')}")
        lines.append(f"- current_live_stack: {kr_platform.get('current_live_stack')}")
        lines.append(f"- wordpress_live_decision: {kr_platform.get('wordpress_live_decision')}")
        lines.append(f"- next_lane_decision: {kr_platform.get('next_lane_decision')}")
        lines.append(f"- deploy_ready: {kr_platform.get('deploy_ready')}")
        lines.append(f"- preview_deployed: {kr_platform.get('preview_deployed')}")
        lines.append(f"- preview_url: {kr_platform.get('preview_url') or '(none)'}")
        lines.append(f"- blocking_issues: {', '.join(kr_platform.get('blocking_issues') or []) or '(none)'}")
        for item in kr_platform.get("next_actions") or []:
            lines.append(f"- kr_next_action: {item}")
        lines.append("")

    surface_stack = (packet.get("summaries") or {}).get("surface_stack") if isinstance((packet.get("summaries") or {}).get("surface_stack"), dict) else {}
    if surface_stack:
        lines.append("## Surface Stack")
        lines.append(f"- kr_stack: {surface_stack.get('kr_stack') or '(none)'}")
        lines.append(f"- co_stack: {surface_stack.get('co_stack') or '(none)'}")
        lines.append(f"- wordpress_live_decision: {surface_stack.get('wordpress_live_decision') or '(none)'}")
        lines.append(f"- candidate_package_slugs: {', '.join(surface_stack.get('candidate_package_slugs') or []) or '(none)'}")
        lines.append("")

    private_proxy = (packet.get("summaries") or {}).get("private_engine_proxy") if isinstance((packet.get("summaries") or {}).get("private_engine_proxy"), dict) else {}
    if private_proxy:
        lines.append("## Private Engine Proxy")
        lines.append(f"- main_platform_host: {private_proxy.get('main_platform_host') or '(none)'}")
        lines.append(f"- listing_market_host: {private_proxy.get('listing_market_host') or '(none)'}")
        lines.append(f"- public_mount_base: {private_proxy.get('public_mount_base') or '(none)'}")
        lines.append(f"- private_engine_origin: {private_proxy.get('private_engine_origin') or '(none)'}")
        lines.append(f"- public_contract: {private_proxy.get('public_contract') or '(none)'}")
        lines.append("")

    wp_lab = (packet.get("summaries") or {}).get("wp_surface_lab") if isinstance((packet.get("summaries") or {}).get("wp_surface_lab"), dict) else {}
    if wp_lab:
        lines.append("## WordPress Lab")
        lines.append(f"- package_count: {wp_lab.get('package_count')}")
        lines.append(f"- downloaded_count: {wp_lab.get('downloaded_count')}")
        lines.append(f"- staging_ready_count: {wp_lab.get('staging_ready_count')}")
        lines.append(f"- runtime_ready: {wp_lab.get('runtime_ready')}")
        lines.append(f"- runtime_blockers: {', '.join(wp_lab.get('runtime_blockers') or []) or '(none)'}")
        lines.append("")

    wp_runtime = (packet.get("summaries") or {}).get("wp_surface_lab_runtime") if isinstance((packet.get("summaries") or {}).get("wp_surface_lab_runtime"), dict) else {}
    if wp_runtime:
        lines.append("## WordPress Lab Runtime")
        lines.append(f"- runtime_scaffold_ready: {wp_runtime.get('runtime_scaffold_ready')}")
        lines.append(f"- runtime_ready: {wp_runtime.get('runtime_ready')}")
        lines.append(f"- runtime_running: {wp_runtime.get('runtime_running')}")
        lines.append(f"- runtime_mode: {wp_runtime.get('runtime_mode') or '(none)'}")
        lines.append(f"- docker_available: {wp_runtime.get('docker_available')}")
        lines.append(f"- local_bind_only: {wp_runtime.get('local_bind_only')}")
        lines.append(f"- localhost_url: {wp_runtime.get('localhost_url') or '(none)'}")
        lines.append(f"- blockers: {', '.join(wp_runtime.get('blockers') or []) or '(none)'}")
        lines.append("")

    wp_php_runtime = (packet.get("summaries") or {}).get("wp_surface_lab_php_runtime") if isinstance((packet.get("summaries") or {}).get("wp_surface_lab_php_runtime"), dict) else {}
    if wp_php_runtime:
        lines.append("## WordPress PHP Runtime")
        lines.append(f"- archive_name: {wp_php_runtime.get('archive_name') or '(none)'}")
        lines.append(f"- runtime_key: {wp_php_runtime.get('runtime_key') or '(none)'}")
        lines.append(f"- package_ready: {wp_php_runtime.get('package_ready')}")
        lines.append(f"- php_binary_ready: {wp_php_runtime.get('php_binary_ready')}")
        lines.append(f"- php_module_ready: {wp_php_runtime.get('php_module_ready')}")
        lines.append(f"- localhost_url: {wp_php_runtime.get('localhost_url') or '(none)'}")
        lines.append(f"- missing_modules: {', '.join(wp_php_runtime.get('missing_modules') or []) or '(none)'}")
        lines.append("")

    wp_php_fallback = (packet.get("summaries") or {}).get("wp_surface_lab_php_fallback") if isinstance((packet.get("summaries") or {}).get("wp_surface_lab_php_fallback"), dict) else {}
    if wp_php_fallback:
        lines.append("## WordPress PHP Fallback")
        lines.append(f"- site_root_ready: {wp_php_fallback.get('site_root_ready')}")
        lines.append(f"- php_runtime_ready: {wp_php_fallback.get('php_runtime_ready')}")
        lines.append(f"- sqlite_plugin_ready: {wp_php_fallback.get('sqlite_plugin_ready')}")
        lines.append(f"- db_dropin_ready: {wp_php_fallback.get('db_dropin_ready')}")
        lines.append(f"- bootstrap_ready: {wp_php_fallback.get('bootstrap_ready')}")
        lines.append(f"- install_url: {wp_php_fallback.get('install_url') or '(none)'}")
        lines.append("")

    wp_assets = (packet.get("summaries") or {}).get("wp_platform_assets") if isinstance((packet.get("summaries") or {}).get("wp_platform_assets"), dict) else {}
    if wp_assets:
        lines.append("## WordPress Platform Assets")
        lines.append(f"- theme_ready: {wp_assets.get('theme_ready')}")
        lines.append(f"- plugin_ready: {wp_assets.get('plugin_ready')}")
        lines.append(f"- theme_slug: {wp_assets.get('theme_slug') or '(none)'}")
        lines.append(f"- plugin_slug: {wp_assets.get('plugin_slug') or '(none)'}")
        lines.append(f"- public_mount_host: {wp_assets.get('public_mount_host') or '(none)'}")
        lines.append(f"- lazy_iframe_policy: {wp_assets.get('lazy_iframe_policy')}")
        lines.append("")

    wp_ia = (packet.get("summaries") or {}).get("wordpress_platform_ia") if isinstance((packet.get("summaries") or {}).get("wordpress_platform_ia"), dict) else {}
    if wp_ia:
        lines.append("## WordPress Platform IA")
        lines.append(f"- page_count: {wp_ia.get('page_count')}")
        lines.append(f"- service_page_count: {wp_ia.get('service_page_count')}")
        lines.append(f"- lazy_gate_pages: {', '.join(wp_ia.get('lazy_gate_pages') or []) or '(none)'}")
        lines.append(f"- cta_only_pages: {', '.join(wp_ia.get('cta_only_pages') or []) or '(none)'}")
        lines.append(f"- platform_host: {wp_ia.get('platform_host') or '(none)'}")
        lines.append(f"- public_mount: {wp_ia.get('public_mount') or '(none)'}")
        lines.append("")

    wp_blueprints = (packet.get("summaries") or {}).get("wp_platform_blueprints") if isinstance((packet.get("summaries") or {}).get("wp_platform_blueprints"), dict) else {}
    if wp_blueprints:
        lines.append("## WordPress Blueprints")
        lines.append(f"- blueprint_count: {wp_blueprints.get('blueprint_count')}")
        lines.append(f"- lazy_gate_pages: {', '.join(wp_blueprints.get('lazy_gate_pages') or []) or '(none)'}")
        lines.append(f"- cta_only_pages: {', '.join(wp_blueprints.get('cta_only_pages') or []) or '(none)'}")
        lines.append(f"- navigation_ready: {wp_blueprints.get('navigation_ready')}")
        lines.append("")

    wp_apply = (packet.get("summaries") or {}).get("wordpress_staging_apply_plan") if isinstance((packet.get("summaries") or {}).get("wordpress_staging_apply_plan"), dict) else {}
    if wp_apply:
        lines.append("## WordPress Staging Apply Plan")
        lines.append(f"- page_step_count: {wp_apply.get('page_step_count')}")
        lines.append(f"- cutover_ready: {wp_apply.get('cutover_ready')}")
        lines.append(f"- service_page_count: {wp_apply.get('service_page_count')}")
        lines.append("")

    wp_surface_apply = (packet.get("summaries") or {}).get("wp_surface_lab_apply") if isinstance((packet.get("summaries") or {}).get("wp_surface_lab_apply"), dict) else {}
    if wp_surface_apply:
        lines.append("## WordPress Apply Bundle")
        lines.append(f"- bundle_ready: {wp_surface_apply.get('bundle_ready')}")
        lines.append(f"- page_count: {wp_surface_apply.get('page_count')}")
        lines.append(f"- service_page_count: {wp_surface_apply.get('service_page_count')}")
        lines.append(f"- runtime_ready: {wp_surface_apply.get('runtime_ready')}")
        lines.append(f"- runtime_mode: {wp_surface_apply.get('runtime_mode') or '(none)'}")
        lines.append(f"- front_page_slug: {wp_surface_apply.get('front_page_slug') or '(none)'}")
        lines.append(f"- manifest_file: {wp_surface_apply.get('manifest_file') or '(none)'}")
        lines.append(f"- php_bundle_file: {wp_surface_apply.get('php_bundle_file') or '(none)'}")
        lines.append(f"- standalone_php_bundle_file: {wp_surface_apply.get('standalone_php_bundle_file') or '(none)'}")
        lines.append(f"- apply_attempted: {wp_surface_apply.get('apply_attempted')}")
        lines.append(f"- apply_ok: {wp_surface_apply.get('apply_ok')}")
        lines.append(f"- apply_blockers: {', '.join(wp_surface_apply.get('apply_blockers') or []) or '(none)'}")
        lines.append("")

    wp_surface_cycle = (packet.get("summaries") or {}).get("wp_surface_lab_apply_verify_cycle") if isinstance((packet.get("summaries") or {}).get("wp_surface_lab_apply_verify_cycle"), dict) else {}
    if wp_surface_cycle:
        lines.append("## WordPress Apply Verify Cycle")
        lines.append(f"- ok: {wp_surface_cycle.get('ok')}")
        lines.append(f"- runtime_mode: {wp_surface_cycle.get('runtime_mode') or '(none)'}")
        lines.append(f"- runtime_running_before: {wp_surface_cycle.get('runtime_running_before')}")
        lines.append(f"- runtime_running_after: {wp_surface_cycle.get('runtime_running_after')}")
        lines.append(f"- apply_ok: {wp_surface_cycle.get('apply_ok')}")
        lines.append(f"- verification_ok: {wp_surface_cycle.get('verification_ok')}")
        lines.append(f"- step_count: {wp_surface_cycle.get('step_count')}")
        lines.append(f"- blockers: {', '.join(wp_surface_cycle.get('blockers') or []) or '(none)'}")
        lines.append("")

    wp_surface_verify = (packet.get("summaries") or {}).get("wp_surface_lab_page_verify") if isinstance((packet.get("summaries") or {}).get("wp_surface_lab_page_verify"), dict) else {}
    if wp_surface_verify:
        lines.append("## WordPress Page Verification")
        lines.append(f"- verification_ready: {wp_surface_verify.get('verification_ready')}")
        lines.append(f"- verification_ok: {wp_surface_verify.get('verification_ok')}")
        lines.append(f"- page_count: {wp_surface_verify.get('page_count')}")
        lines.append(f"- service_page_count: {wp_surface_verify.get('service_page_count')}")
        lines.append(f"- localhost_url: {wp_surface_verify.get('localhost_url') or '(none)'}")
        lines.append(f"- blockers: {', '.join(wp_surface_verify.get('blockers') or []) or '(none)'}")
        lines.append("")

    wp_encoding = (packet.get("summaries") or {}).get("wordpress_platform_encoding_audit") if isinstance((packet.get("summaries") or {}).get("wordpress_platform_encoding_audit"), dict) else {}
    if wp_encoding:
        lines.append("## WordPress Encoding Audit")
        lines.append(f"- encoding_ok: {wp_encoding.get('encoding_ok')}")
        lines.append(f"- checked_file_count: {wp_encoding.get('checked_file_count')}")
        lines.append(f"- issue_file_count: {wp_encoding.get('issue_file_count')}")
        lines.append("")

    wp_ux = (packet.get("summaries") or {}).get("wordpress_platform_ux_audit") if isinstance((packet.get("summaries") or {}).get("wordpress_platform_ux_audit"), dict) else {}
    if wp_ux:
        lines.append("## WordPress UX Audit")
        lines.append(f"- ux_ok: {wp_ux.get('ux_ok')}")
        lines.append(f"- page_count: {wp_ux.get('page_count')}")
        lines.append(f"- issue_count: {wp_ux.get('issue_count')}")
        lines.append(f"- service_pages_ok: {wp_ux.get('service_pages_ok')}")
        lines.append(f"- market_bridge_ok: {wp_ux.get('market_bridge_ok')}")
        lines.append(f"- yangdo_recommendation_surface_ok: {wp_ux.get('yangdo_recommendation_surface_ok')}")
        lines.append("")

    recommendation_qa = (packet.get("summaries") or {}).get("yangdo_recommendation_qa") if isinstance((packet.get("summaries") or {}).get("yangdo_recommendation_qa"), dict) else {}
    if recommendation_qa:
        lines.append("## Yangdo Recommendation QA")
        lines.append(f"- qa_ok: {recommendation_qa.get('qa_ok')}")
        lines.append(f"- scenario_count: {recommendation_qa.get('scenario_count')}")
        lines.append(f"- passed_count: {recommendation_qa.get('passed_count')}")
        lines.append(f"- failed_count: {recommendation_qa.get('failed_count')}")
        lines.append(f"- strict_profile_regression_ok: {recommendation_qa.get('strict_profile_regression_ok')}")
        lines.append(f"- fallback_regression_ok: {recommendation_qa.get('fallback_regression_ok')}")
        lines.append(f"- balance_exclusion_regression_ok: {recommendation_qa.get('balance_exclusion_regression_ok')}")
        lines.append(f"- assistive_precision_regression_ok: {recommendation_qa.get('assistive_precision_regression_ok')}")
        lines.append(f"- summary_projection_regression_ok: {recommendation_qa.get('summary_projection_regression_ok')}")
        precision_counts = recommendation_qa.get("precision_counts") if isinstance(recommendation_qa.get("precision_counts"), dict) else {}
        if precision_counts:
            lines.append(f"- precision_counts: {json.dumps(precision_counts, ensure_ascii=False)}")
        lines.append("")

    recommendation_precision = (packet.get("summaries") or {}).get("yangdo_recommendation_precision_matrix") if isinstance((packet.get("summaries") or {}).get("yangdo_recommendation_precision_matrix"), dict) else {}
    if recommendation_precision:
        lines.append("## Yangdo Recommendation Precision")
        lines.append(f"- precision_ok: {recommendation_precision.get('precision_ok')}")
        lines.append(f"- scenario_count: {recommendation_precision.get('scenario_count')}")
        lines.append(f"- passed_count: {recommendation_precision.get('passed_count')}")
        lines.append(f"- failed_count: {recommendation_precision.get('failed_count')}")
        lines.append(f"- high_precision_ok: {recommendation_precision.get('high_precision_ok')}")
        lines.append(f"- fallback_precision_ok: {recommendation_precision.get('fallback_precision_ok')}")
        lines.append(f"- balance_excluded_precision_ok: {recommendation_precision.get('balance_excluded_precision_ok')}")
        lines.append(f"- assist_precision_ok: {recommendation_precision.get('assist_precision_ok')}")
        lines.append(f"- summary_publication_ok: {recommendation_precision.get('summary_publication_ok')}")
        lines.append(f"- detail_explainability_ok: {recommendation_precision.get('detail_explainability_ok')}")
        lines.append(f"- precision_counts: {json.dumps(recommendation_precision.get('precision_counts') or {}, ensure_ascii=False)}")
        lines.append("")

    recommendation_diversity = (packet.get("summaries") or {}).get("yangdo_recommendation_diversity_audit") if isinstance((packet.get("summaries") or {}).get("yangdo_recommendation_diversity_audit"), dict) else {}
    if recommendation_diversity:
        lines.append("## Yangdo Recommendation Diversity")
        lines.append(f"- diversity_ok: {recommendation_diversity.get('diversity_ok')}")
        lines.append(f"- scenario_count: {recommendation_diversity.get('scenario_count')}")
        lines.append(f"- passed_count: {recommendation_diversity.get('passed_count')}")
        lines.append(f"- failed_count: {recommendation_diversity.get('failed_count')}")
        lines.append(f"- top1_stability_ok: {recommendation_diversity.get('top1_stability_ok')}")
        lines.append(f"- price_band_spread_ok: {recommendation_diversity.get('price_band_spread_ok')}")
        lines.append(f"- focus_signature_spread_ok: {recommendation_diversity.get('focus_signature_spread_ok')}")
        lines.append(f"- detail_projection_contract_ok: {recommendation_diversity.get('detail_projection_contract_ok')}")
        lines.append(f"- precision_tier_spread_ok: {recommendation_diversity.get('precision_tier_spread_ok')}")
        lines.append(f"- unique_listing_ok: {recommendation_diversity.get('unique_listing_ok')}")
        lines.append(f"- listing_bridge_ok: {recommendation_diversity.get('listing_bridge_ok')}")
        lines.append(f"- listing_band_spread_ok: {recommendation_diversity.get('listing_band_spread_ok')}")
        lines.append(f"- cluster_concentration_ok: {recommendation_diversity.get('cluster_concentration_ok')}")
        lines.append(f"- top_rank_signature_concentration_ok: {recommendation_diversity.get('top_rank_signature_concentration_ok')}")
        lines.append(f"- price_band_concentration_ok: {recommendation_diversity.get('price_band_concentration_ok')}")
        lines.append("")

    recommendation_contract = (packet.get("summaries") or {}).get("yangdo_recommendation_contract_audit") if isinstance((packet.get("summaries") or {}).get("yangdo_recommendation_contract_audit"), dict) else {}
    if recommendation_contract:
        lines.append("## Yangdo Recommendation Contract")
        lines.append(f"- contract_ok: {recommendation_contract.get('contract_ok')}")
        lines.append(f"- summary_safe: {recommendation_contract.get('summary_safe')}")
        lines.append(f"- detail_explainable: {recommendation_contract.get('detail_explainable')}")
        lines.append(f"- internal_debug_visible: {recommendation_contract.get('internal_debug_visible')}")
        lines.append("")

    recommendation_bridge = (packet.get("summaries") or {}).get("yangdo_recommendation_bridge") if isinstance((packet.get("summaries") or {}).get("yangdo_recommendation_bridge"), dict) else {}
    if recommendation_bridge:
        lines.append("## Yangdo Recommendation Bridge")
        lines.append(f"- packet_ready: {recommendation_bridge.get('packet_ready')}")
        lines.append(f"- service_slug: {recommendation_bridge.get('service_slug') or '(none)'}")
        lines.append(f"- platform_host: {recommendation_bridge.get('platform_host') or '(none)'}")
        lines.append(f"- listing_host: {recommendation_bridge.get('listing_host') or '(none)'}")
        lines.append(f"- market_bridge_ready: {recommendation_bridge.get('market_bridge_ready')}")
        lines.append(f"- rental_ready: {recommendation_bridge.get('rental_ready')}")
        lines.append(f"- supported_precision_labels: {', '.join(recommendation_bridge.get('supported_precision_labels') or []) or '(none)'}")
        lines.append(f"- public_summary_fields: {', '.join(recommendation_bridge.get('public_summary_fields') or []) or '(none)'}")
        lines.append(f"- detail_fields: {', '.join(recommendation_bridge.get('detail_fields') or []) or '(none)'}")
        lines.append(f"- summary_offerings: {', '.join(recommendation_bridge.get('summary_offerings') or []) or '(none)'}")
        lines.append(f"- detail_offerings: {', '.join(recommendation_bridge.get('detail_offerings') or []) or '(none)'}")
        lines.append(f"- internal_offerings: {', '.join(recommendation_bridge.get('internal_offerings') or []) or '(none)'}")
        lines.append(f"- summary_policy: {recommendation_bridge.get('summary_policy') or '(none)'}")
        lines.append(f"- detail_policy: {recommendation_bridge.get('detail_policy') or '(none)'}")
        lines.append(f"- internal_policy: {recommendation_bridge.get('internal_policy') or '(none)'}")
        lines.append("")

    recommendation_ux = (packet.get("summaries") or {}).get("yangdo_recommendation_ux") if isinstance((packet.get("summaries") or {}).get("yangdo_recommendation_ux"), dict) else {}
    if recommendation_ux:
        lines.append("## Yangdo Recommendation UX")
        lines.append(f"- packet_ready: {recommendation_ux.get('packet_ready')}")
        lines.append(f"- service_surface_ready: {recommendation_ux.get('service_surface_ready')}")
        lines.append(f"- market_bridge_ready: {recommendation_ux.get('market_bridge_ready')}")
        lines.append(f"- rental_exposure_ready: {recommendation_ux.get('rental_exposure_ready')}")
        lines.append(f"- precision_ready: {recommendation_ux.get('precision_ready')}")
        lines.append(f"- detail_explainability_ready: {recommendation_ux.get('detail_explainability_ready')}")
        lines.append(f"- service_flow_policy: {recommendation_ux.get('service_flow_policy') or '(none)'}")
        lines.append(f"- public_primary_cta: {recommendation_ux.get('public_primary_cta') or '(none)'}")
        lines.append(f"- public_secondary_cta: {recommendation_ux.get('public_secondary_cta') or '(none)'}")
        lines.append(f"- public_fields: {', '.join(recommendation_ux.get('public_fields') or []) or '(none)'}")
        lines.append(f"- detail_explainable_fields: {', '.join(recommendation_ux.get('detail_explainable_fields') or []) or '(none)'}")
        lines.append(f"- detail_fields: {', '.join(recommendation_ux.get('detail_fields') or []) or '(none)'}")
        lines.append(f"- standard_offerings: {', '.join(recommendation_ux.get('standard_offerings') or []) or '(none)'}")
        lines.append(f"- pro_detail_offerings: {', '.join(recommendation_ux.get('pro_detail_offerings') or []) or '(none)'}")
        lines.append(f"- pro_consult_offerings: {', '.join(recommendation_ux.get('pro_consult_offerings') or []) or '(none)'}")
        lines.append(f"- internal_offerings: {', '.join(recommendation_ux.get('internal_offerings') or []) or '(none)'}")
        lines.append("")

    wp_strategy = (packet.get("summaries") or {}).get("wordpress_platform_strategy") if isinstance((packet.get("summaries") or {}).get("wordpress_platform_strategy"), dict) else {}
    if wp_strategy:
        lines.append("## WordPress Platform Strategy")
        lines.append(f"- primary_runtime: {wp_strategy.get('primary_runtime') or '(none)'}")
        lines.append(f"- support_runtime: {wp_strategy.get('support_runtime') or '(none)'}")
        lines.append(f"- recommended_pattern: {wp_strategy.get('recommended_pattern') or '(none)'}")
        lines.append(f"- public_mount: {wp_strategy.get('public_mount') or '(none)'}")
        lines.append(f"- listing_site_policy: {wp_strategy.get('listing_site_policy') or '(none)'}")
        lines.append(f"- keep_live: {', '.join(wp_strategy.get('keep_live') or []) or '(none)'}")
        lines.append(f"- stage_first: {', '.join(wp_strategy.get('stage_first') or []) or '(none)'}")
        lines.append(f"- avoid_live_duplication: {', '.join(wp_strategy.get('avoid_live_duplication') or []) or '(none)'}")
        lines.append("")

    astra_ref = (packet.get("summaries") or {}).get("astra_design_reference") if isinstance((packet.get("summaries") or {}).get("astra_design_reference"), dict) else {}
    if astra_ref:
        lines.append("## Astra Reference")
        lines.append(f"- theme_name: {astra_ref.get('theme_name') or '(none)'}")
        lines.append(f"- theme_version: {astra_ref.get('theme_version') or '(none)'}")
        lines.append(f"- strategy: {astra_ref.get('strategy') or '(none)'}")
        lines.append(f"- usable_for_next_front: {', '.join(astra_ref.get('usable_for_next_front') or []) or '(none)'}")
        lines.append("")

    kr_cutover = (packet.get("summaries") or {}).get("kr_reverse_proxy_cutover") if isinstance((packet.get("summaries") or {}).get("kr_reverse_proxy_cutover"), dict) else {}
    if kr_cutover:
        lines.append("## KR Reverse Proxy Cutover")
        lines.append(f"- cutover_ready: {kr_cutover.get('cutover_ready')}")
        lines.append(f"- service_page_count: {kr_cutover.get('service_page_count')}")
        lines.append(f"- traffic_gate_ok: {kr_cutover.get('traffic_gate_ok')}")
        lines.append(f"- public_mount_base: {kr_cutover.get('public_mount_base') or '(none)'}")
        lines.append(f"- private_engine_origin: {kr_cutover.get('private_engine_origin') or '(none)'}")
        lines.append("")

    kr_traffic_gate = (packet.get("summaries") or {}).get("kr_traffic_gate") if isinstance((packet.get("summaries") or {}).get("kr_traffic_gate"), dict) else {}
    if kr_traffic_gate:
        lines.append("## KR Traffic Gate")
        lines.append(f"- traffic_leak_blocked: {kr_traffic_gate.get('traffic_leak_blocked')}")
        lines.append(f"- remaining_risks: {', '.join(kr_traffic_gate.get('remaining_risks') or []) or '(none)'}")
        lines.append(f"- server_started: {kr_traffic_gate.get('server_started')}")
        lines.append(f"- all_routes_no_iframe: {kr_traffic_gate.get('all_routes_no_iframe')}")
        lines.append("")

    recommendation_alignment = (packet.get("summaries") or {}).get("yangdo_recommendation_alignment") if isinstance((packet.get("summaries") or {}).get("yangdo_recommendation_alignment"), dict) else {}
    if recommendation_alignment:
        lines.append("## Yangdo Recommendation Alignment")
        lines.append(f"- alignment_ok: {recommendation_alignment.get('alignment_ok')}")
        lines.append(f"- issue_count: {recommendation_alignment.get('issue_count')}")
        lines.append(f"- service_flow_policy_ok: {recommendation_alignment.get('service_flow_policy_ok')}")
        lines.append(f"- cta_labels_ok: {recommendation_alignment.get('cta_labels_ok')}")
        lines.append(f"- field_contract_ok: {recommendation_alignment.get('field_contract_ok')}")
        lines.append(f"- offering_exposure_ok: {recommendation_alignment.get('offering_exposure_ok')}")
        lines.append(f"- patent_handoff_ok: {recommendation_alignment.get('patent_handoff_ok')}")
        lines.append(f"- contract_story_ok: {recommendation_alignment.get('contract_story_ok')}")
        lines.append(f"- supported_labels_ok: {recommendation_alignment.get('supported_labels_ok')}")
        lines.append("")

    zero_display_recovery = (packet.get("summaries") or {}).get("yangdo_zero_display_recovery_audit") if isinstance((packet.get("summaries") or {}).get("yangdo_zero_display_recovery_audit"), dict) else {}
    if zero_display_recovery:
        lines.append("## Yangdo Zero Display Recovery")
        lines.append(f"- zero_display_guard_ok: {zero_display_recovery.get('zero_display_guard_ok')}")
        lines.append(f"- zero_display_total: {zero_display_recovery.get('zero_display_total')}")
        lines.append(f"- selected_lane_ok: {zero_display_recovery.get('selected_lane_ok')}")
        lines.append(f"- runtime_ready: {zero_display_recovery.get('runtime_ready')}")
        lines.append(f"- contract_policy_ok: {zero_display_recovery.get('contract_policy_ok')}")
        lines.append(f"- market_bridge_route_ok: {zero_display_recovery.get('market_bridge_route_ok')}")
        lines.append(f"- consult_first_ready: {zero_display_recovery.get('consult_first_ready')}")
        lines.append(f"- zero_policy_ready: {zero_display_recovery.get('zero_policy_ready')}")
        lines.append(f"- market_cta_ready: {zero_display_recovery.get('market_cta_ready')}")
        lines.append(f"- consult_lane_ready: {zero_display_recovery.get('consult_lane_ready')}")
        lines.append(f"- patent_hook_ready: {zero_display_recovery.get('patent_hook_ready')}")
        lines.append("")

    service_copy = (packet.get("summaries") or {}).get("yangdo_service_copy") if isinstance((packet.get("summaries") or {}).get("yangdo_service_copy"), dict) else {}
    if service_copy:
        lines.append("## Yangdo Service Copy")
        lines.append(f"- packet_ready: {service_copy.get('packet_ready')}")
        lines.append(f"- service_copy_ready: {service_copy.get('service_copy_ready')}")
        lines.append(f"- low_precision_consult_first_ready: {service_copy.get('low_precision_consult_first_ready')}")
        lines.append(f"- market_bridge_story_ready: {service_copy.get('market_bridge_story_ready')}")
        lines.append(f"- market_fit_interpretation_ready: {service_copy.get('market_fit_interpretation_ready')}")
        lines.append(f"- lane_stories_ready: {service_copy.get('lane_stories_ready')}")
        lines.append(f"- lane_ladder_ready: {service_copy.get('lane_ladder_ready')}")
        lines.append(f"- detail_explainable_lane_ready: {service_copy.get('detail_explainable_lane_ready')}")
        lines.append(f"- consult_assist_lane_ready: {service_copy.get('consult_assist_lane_ready')}")
        lines.append(f"- precision_lane_contract_ready: {service_copy.get('precision_lane_contract_ready')}")
        lines.append(f"- service_slug: {service_copy.get('service_slug') or '(none)'}")
        lines.append(f"- platform_host: {service_copy.get('platform_host') or '(none)'}")
        lines.append(f"- listing_host: {service_copy.get('listing_host') or '(none)'}")
        lines.append(f"- precision_label_count: {service_copy.get('precision_label_count')}")
        lines.append(f"- hero_title: {service_copy.get('hero_title') or '(none)'}")
        lines.append(f"- primary_market_bridge_cta: {service_copy.get('primary_market_bridge_cta') or '(none)'}")
        lines.append(f"- secondary_consult_cta: {service_copy.get('secondary_consult_cta') or '(none)'}")
        lines.append(f"- summary_market_bridge_offerings: {', '.join(service_copy.get('summary_market_bridge_offerings') or []) or '(none)'}")
        lines.append(f"- detail_explainable_offerings: {', '.join(service_copy.get('detail_explainable_offerings') or []) or '(none)'}")
        lines.append(f"- consult_assist_offerings: {', '.join(service_copy.get('consult_assist_offerings') or []) or '(none)'}")
        lines.append(f"- internal_full_offerings: {', '.join(service_copy.get('internal_full_offerings') or []) or '(none)'}")
        lines.append("")

    permit_service_copy = (packet.get("summaries") or {}).get("permit_service_copy") if isinstance((packet.get("summaries") or {}).get("permit_service_copy"), dict) else {}
    if permit_service_copy:
        lines.append("## Permit Service Copy")
        lines.append(f"- packet_ready: {permit_service_copy.get('packet_ready')}")
        lines.append(f"- service_copy_ready: {permit_service_copy.get('service_copy_ready')}")
        lines.append(f"- checklist_story_ready: {permit_service_copy.get('checklist_story_ready')}")
        lines.append(f"- manual_review_story_ready: {permit_service_copy.get('manual_review_story_ready')}")
        lines.append(f"- document_story_ready: {permit_service_copy.get('document_story_ready')}")
        lines.append(f"- lane_ladder_ready: {permit_service_copy.get('lane_ladder_ready')}")
        lines.append(f"- service_flow_ready: {permit_service_copy.get('service_flow_ready')}")
        lines.append(f"- service_slug: {permit_service_copy.get('service_slug') or '(none)'}")
        lines.append(f"- platform_host: {permit_service_copy.get('platform_host') or '(none)'}")
        lines.append(f"- hero_title: {permit_service_copy.get('hero_title') or '(none)'}")
        lines.append(f"- primary_self_check_cta: {permit_service_copy.get('primary_self_check_cta') or '(none)'}")
        lines.append(f"- secondary_consult_cta: {permit_service_copy.get('secondary_consult_cta') or '(none)'}")
        lines.append(f"- knowledge_cta: {permit_service_copy.get('knowledge_cta') or '(none)'}")
        lines.append(f"- detail_checklist_upgrade_target: {permit_service_copy.get('detail_checklist_upgrade_target') or '(none)'}")
        lines.append(f"- manual_review_assist_upgrade_target: {permit_service_copy.get('manual_review_assist_upgrade_target') or '(none)'}")
        lines.append(f"- summary_self_check_offerings: {', '.join(permit_service_copy.get('summary_self_check_offerings') or []) or '(none)'}")
        lines.append(f"- detail_checklist_offerings: {', '.join(permit_service_copy.get('detail_checklist_offerings') or []) or '(none)'}")
        lines.append(f"- manual_review_assist_offerings: {', '.join(permit_service_copy.get('manual_review_assist_offerings') or []) or '(none)'}")
        lines.append("")

    permit_service_alignment = (packet.get("summaries") or {}).get("permit_service_alignment") if isinstance((packet.get("summaries") or {}).get("permit_service_alignment"), dict) else {}
    if permit_service_alignment:
        lines.append("## Permit Service Alignment")
        lines.append(f"- alignment_ok: {permit_service_alignment.get('alignment_ok')}")
        lines.append(f"- issue_count: {permit_service_alignment.get('issue_count')}")
        lines.append(f"- cta_contract_ok: {permit_service_alignment.get('cta_contract_ok')}")
        lines.append(f"- proof_point_contract_ok: {permit_service_alignment.get('proof_point_contract_ok')}")
        lines.append(f"- service_story_ok: {permit_service_alignment.get('service_story_ok')}")
        lines.append(f"- lane_positioning_ok: {permit_service_alignment.get('lane_positioning_ok')}")
        lines.append(f"- rental_positioning_ok: {permit_service_alignment.get('rental_positioning_ok')}")
        lines.append(f"- patent_handoff_ok: {permit_service_alignment.get('patent_handoff_ok')}")
        lines.append(f"- permit_offering_count: {permit_service_alignment.get('permit_offering_count')}")
        lines.append("")

    permit_service_ux = (packet.get("summaries") or {}).get("permit_service_ux") if isinstance((packet.get("summaries") or {}).get("permit_service_ux"), dict) else {}
    if permit_service_ux:
        lines.append("## Permit Service UX")
        lines.append(f"- packet_ready: {permit_service_ux.get('packet_ready')}")
        lines.append(f"- service_surface_ready: {permit_service_ux.get('service_surface_ready')}")
        lines.append(f"- lane_exposure_ready: {permit_service_ux.get('lane_exposure_ready')}")
        lines.append(f"- alignment_ready: {permit_service_ux.get('alignment_ready')}")
        lines.append(f"- service_flow_policy: {permit_service_ux.get('service_flow_policy') or '(none)'}")
        lines.append(f"- public_allowed_offerings: {', '.join(permit_service_ux.get('public_allowed_offerings') or []) or '(none)'}")
        lines.append(f"- detail_allowed_offerings: {', '.join(permit_service_ux.get('detail_allowed_offerings') or []) or '(none)'}")
        lines.append(f"- assist_allowed_offerings: {', '.join(permit_service_ux.get('assist_allowed_offerings') or []) or '(none)'}")
        lines.append(f"- primary_self_check_cta: {permit_service_ux.get('primary_self_check_cta') or '(none)'}")
        lines.append(f"- detail_cta: {permit_service_ux.get('detail_cta') or '(none)'}")
        lines.append(f"- assist_cta: {permit_service_ux.get('assist_cta') or '(none)'}")
        lines.append("")

    permit_public_contract = (packet.get("summaries") or {}).get("permit_public_contract") if isinstance((packet.get("summaries") or {}).get("permit_public_contract"), dict) else {}
    if permit_public_contract:
        lines.append("## Permit Public Contract")
        lines.append(f"- contract_ok: {permit_public_contract.get('contract_ok')}")
        lines.append(f"- issue_count: {permit_public_contract.get('issue_count')}")
        lines.append(f"- public_summary_only_ok: {permit_public_contract.get('public_summary_only_ok')}")
        lines.append(f"- detail_checklist_contract_ok: {permit_public_contract.get('detail_checklist_contract_ok')}")
        lines.append(f"- assist_contract_ok: {permit_public_contract.get('assist_contract_ok')}")
        lines.append(f"- internal_visibility_ok: {permit_public_contract.get('internal_visibility_ok')}")
        lines.append(f"- offering_exposure_ok: {permit_public_contract.get('offering_exposure_ok')}")
        lines.append(f"- patent_handoff_ok: {permit_public_contract.get('patent_handoff_ok')}")
        lines.append("")

    partner_input_handoff = (packet.get("summaries") or {}).get("partner_input_handoff") if isinstance((packet.get("summaries") or {}).get("partner_input_handoff"), dict) else {}
    if partner_input_handoff:
        lines.append("## Partner Input Handoff")
        lines.append(f"- partner_count: {partner_input_handoff.get('partner_count')}")
        lines.append(f"- uniform_required_inputs: {partner_input_handoff.get('uniform_required_inputs')}")
        lines.append(f"- common_required_inputs: {', '.join(partner_input_handoff.get('common_required_inputs') or []) or '(none)'}")
        lines.append(f"- ready_after_recommended_injection: {partner_input_handoff.get('ready_after_recommended_injection')}")
        lines.append(f"- ready_after_recommended_injection_count: {partner_input_handoff.get('ready_after_recommended_injection_count')}")
        lines.append(f"- copy_paste_ready: {partner_input_handoff.get('copy_paste_ready')}")
        lines.append("")

    operator_flow = (packet.get("summaries") or {}).get("partner_input_operator_flow") if isinstance((packet.get("summaries") or {}).get("partner_input_operator_flow"), dict) else {}
    if operator_flow:
        lines.append("## Partner Input Operator Flow")
        lines.append(f"- packet_ready: {operator_flow.get('packet_ready')}")
        lines.append(f"- partner_count: {operator_flow.get('partner_count')}")
        lines.append(f"- copy_paste_ready: {operator_flow.get('copy_paste_ready')}")
        lines.append(f"- common_required_inputs: {', '.join(operator_flow.get('common_required_inputs') or []) or '(none)'}")
        lines.append(f"- ready_after_recommended_injection: {operator_flow.get('ready_after_recommended_injection')}")
        for step in operator_flow.get('recommended_sequence') or []:
            lines.append(f"- operator_step: {step}")
        lines.append("")

    first_principles = (packet.get("summaries") or {}).get("ai_platform_first_principles_review") if isinstance((packet.get("summaries") or {}).get("ai_platform_first_principles_review"), dict) else {}
    if first_principles:
        lines.append("## AI Platform First-Principles Review")
        lines.append(f"- packet_ready: {first_principles.get('packet_ready')}")
        lines.append(f"- blocking_issue_count: {first_principles.get('blocking_issue_count')}")
        lines.append(f"- current_bottleneck: {first_principles.get('current_bottleneck') or '(none)'}")
        lines.append(f"- next_experiment_count: {first_principles.get('next_experiment_count')}")
        lines.append("")

    split_first_principles = (packet.get("summaries") or {}).get("system_split_first_principles") if isinstance((packet.get("summaries") or {}).get("system_split_first_principles"), dict) else {}
    if split_first_principles:
        lines.append("## System Split First-Principles")
        lines.append(f"- packet_ready: {split_first_principles.get('packet_ready')}")
        lines.append(f"- platform_ready: {split_first_principles.get('platform_ready')}")
        lines.append(f"- yangdo_ready: {split_first_principles.get('yangdo_ready')}")
        lines.append(f"- permit_ready: {split_first_principles.get('permit_ready')}")
        lines.append(f"- prompt_count: {split_first_principles.get('prompt_count')}")
        lines.append("")

    widget_rental = (packet.get("summaries") or {}).get("widget_rental_catalog") if isinstance((packet.get("summaries") or {}).get("widget_rental_catalog"), dict) else {}
    if widget_rental:
        lines.append("## Widget Rental Catalog")
        lines.append(f"- offering_count: {widget_rental.get('offering_count')}")
        lines.append(f"- standard_offering_count: {widget_rental.get('standard_offering_count')}")
        lines.append(f"- pro_offering_count: {widget_rental.get('pro_offering_count')}")
        lines.append(f"- combo_offering_count: {widget_rental.get('combo_offering_count')}")
        lines.append(f"- yangdo_recommendation_offering_count: {widget_rental.get('yangdo_recommendation_offering_count')}")
        lines.append(f"- yangdo_recommendation_standard_count: {widget_rental.get('yangdo_recommendation_standard_count')}")
        lines.append(f"- yangdo_recommendation_detail_count: {widget_rental.get('yangdo_recommendation_detail_count')}")
        lines.append(f"- yangdo_recommendation_summary_bridge_count: {widget_rental.get('yangdo_recommendation_summary_bridge_count')}")
        lines.append(f"- yangdo_recommendation_detail_lane_count: {widget_rental.get('yangdo_recommendation_detail_lane_count')}")
        lines.append(f"- yangdo_recommendation_consult_assist_count: {widget_rental.get('yangdo_recommendation_consult_assist_count')}")
        lines.append(f"- internal_tenant_count: {widget_rental.get('internal_tenant_count')}")
        lines.append(f"- public_platform_host: {widget_rental.get('public_platform_host') or '(none)'}")
        lines.append(f"- listing_market_host: {widget_rental.get('listing_market_host') or '(none)'}")
        lines.append(f"- widget_standard: {', '.join(widget_rental.get('widget_standard') or []) or '(none)'}")
        lines.append(f"- api_or_detail_pro: {', '.join(widget_rental.get('api_or_detail_pro') or []) or '(none)'}")
        lines.append(f"- yangdo_recommendation_summary: {', '.join(widget_rental.get('yangdo_recommendation_summary') or []) or '(none)'}")
        lines.append(f"- yangdo_recommendation_detail: {', '.join(widget_rental.get('yangdo_recommendation_detail') or []) or '(none)'}")
        package_matrix = widget_rental.get("yangdo_recommendation_package_matrix") if isinstance(widget_rental.get("yangdo_recommendation_package_matrix"), dict) else {}
        summary_bridge = package_matrix.get("summary_market_bridge") if isinstance(package_matrix.get("summary_market_bridge"), dict) else {}
        detail_explainable = package_matrix.get("detail_explainable") if isinstance(package_matrix.get("detail_explainable"), dict) else {}
        consult_assist = package_matrix.get("consult_assist") if isinstance(package_matrix.get("consult_assist"), dict) else {}
        lane_positioning = widget_rental.get("yangdo_recommendation_lane_positioning") if isinstance(widget_rental.get("yangdo_recommendation_lane_positioning"), dict) else {}
        detail_lane = lane_positioning.get("detail_explainable") if isinstance(lane_positioning.get("detail_explainable"), dict) else {}
        lines.append(f"- yangdo_recommendation_summary_market_bridge: {', '.join(summary_bridge.get('offering_ids') or []) or '(none)'}")
        lines.append(f"- yangdo_recommendation_detail_explainable: {', '.join(detail_explainable.get('offering_ids') or []) or '(none)'}")
        lines.append(f"- yangdo_recommendation_consult_assist: {', '.join(consult_assist.get('offering_ids') or []) or '(none)'}")
        lines.append(f"- detail_explainable_upgrade_target: {detail_lane.get('upgrade_target') or '(none)'}")
        lines.append(f"- detail_explainable_cta_bias: {detail_lane.get('cta_bias') or '(none)'}")
        lines.append(f"- yangdo_recommendation_summary_policy: {widget_rental.get('yangdo_recommendation_summary_policy') or '(none)'}")
        lines.append(f"- yangdo_recommendation_detail_policy: {widget_rental.get('yangdo_recommendation_detail_policy') or '(none)'}")
        lines.append("")

    listing_bridge = (packet.get("summaries") or {}).get("listing_platform_bridge_policy") if isinstance((packet.get("summaries") or {}).get("listing_platform_bridge_policy"), dict) else {}
    if listing_bridge:
        lines.append("## Listing Platform Bridge Policy")
        lines.append(f"- platform_host: {listing_bridge.get('platform_host') or '(none)'}")
        lines.append(f"- listing_host: {listing_bridge.get('listing_host') or '(none)'}")
        lines.append(f"- cta_count: {listing_bridge.get('cta_count')}")
        lines.append(f"- routing_rule_count: {listing_bridge.get('routing_rule_count')}")
        lines.append(f"- listing_runtime_policy: {listing_bridge.get('listing_runtime_policy') or '(none)'}")
        lines.append(f"- calculator_runtime_policy: {listing_bridge.get('calculator_runtime_policy') or '(none)'}")
        lines.append(f"- sample_target: {listing_bridge.get('sample_target') or '(none)'}")
        lines.append("")

    co_bridge_snippets = (packet.get("summaries") or {}).get("co_listing_bridge_snippets") if isinstance((packet.get("summaries") or {}).get("co_listing_bridge_snippets"), dict) else {}
    if co_bridge_snippets:
        lines.append("## CO Listing Bridge Snippets")
        lines.append(f"- listing_host: {co_bridge_snippets.get('listing_host') or '(none)'}")
        lines.append(f"- platform_host: {co_bridge_snippets.get('platform_host') or '(none)'}")
        lines.append(f"- placement_count: {co_bridge_snippets.get('placement_count')}")
        lines.append(f"- snippet_file_count: {co_bridge_snippets.get('snippet_file_count')}")
        lines.append(f"- output_dir: {co_bridge_snippets.get('output_dir') or '(none)'}")
        lines.append(f"- combined_file: {co_bridge_snippets.get('combined_file') or '(none)'}")
        lines.append("")

    co_bridge_checklist = (packet.get("summaries") or {}).get("co_listing_bridge_operator_checklist") if isinstance((packet.get("summaries") or {}).get("co_listing_bridge_operator_checklist"), dict) else {}
    if co_bridge_checklist:
        lines.append("## CO Listing Bridge Operator Checklist")
        lines.append(f"- listing_host: {co_bridge_checklist.get('listing_host') or '(none)'}")
        lines.append(f"- platform_host: {co_bridge_checklist.get('platform_host') or '(none)'}")
        lines.append(f"- placement_count: {co_bridge_checklist.get('placement_count')}")
        lines.append(f"- checklist_ready: {co_bridge_checklist.get('checklist_ready')}")
        lines.append(f"- css_file: {co_bridge_checklist.get('css_file') or '(none)'}")
        lines.append(f"- combined_file: {co_bridge_checklist.get('combined_file') or '(none)'}")
        lines.append("")

    co_bridge_plan = (packet.get("summaries") or {}).get("co_listing_live_injection_plan") if isinstance((packet.get("summaries") or {}).get("co_listing_live_injection_plan"), dict) else {}
    if co_bridge_plan:
        lines.append("## CO Listing Live Injection Plan")
        lines.append(f"- listing_host: {co_bridge_plan.get('listing_host') or '(none)'}")
        lines.append(f"- platform_host: {co_bridge_plan.get('platform_host') or '(none)'}")
        lines.append(f"- placement_count: {co_bridge_plan.get('placement_count')}")
        lines.append(f"- selector_verified_count: {co_bridge_plan.get('selector_verified_count')}")
        lines.append(f"- plan_ready: {co_bridge_plan.get('plan_ready')}")
        lines.append(f"- detail_sample_url: {co_bridge_plan.get('detail_sample_url') or '(none)'}")
        lines.append("")

    co_bridge_bundle = (packet.get("summaries") or {}).get("co_listing_injection_bundle") if isinstance((packet.get("summaries") or {}).get("co_listing_injection_bundle"), dict) else {}
    if co_bridge_bundle:
        lines.append("## CO Listing Injection Bundle")
        lines.append(f"- bundle_ready: {co_bridge_bundle.get('bundle_ready')}")
        lines.append(f"- placement_count: {co_bridge_bundle.get('placement_count')}")
        lines.append(f"- output_dir: {co_bridge_bundle.get('output_dir') or '(none)'}")
        lines.append("")

    co_bridge_apply = (packet.get("summaries") or {}).get("co_listing_bridge_apply_packet") if isinstance((packet.get("summaries") or {}).get("co_listing_bridge_apply_packet"), dict) else {}
    if co_bridge_apply:
        lines.append("## CO Listing Bridge Apply Packet")
        lines.append(f"- apply_ready: {co_bridge_apply.get('apply_ready')}")
        lines.append(f"- placement_count: {co_bridge_apply.get('placement_count')}")
        lines.append(f"- placement_ready_count: {co_bridge_apply.get('placement_ready_count')}")
        lines.append(f"- css_file: {co_bridge_apply.get('css_file') or '(none)'}")
        lines.append(f"- bundle_script: {co_bridge_apply.get('bundle_script') or '(none)'}")
        lines.append("")

    kr_proxy_matrix = (packet.get("summaries") or {}).get("kr_proxy_server_matrix") if isinstance((packet.get("summaries") or {}).get("kr_proxy_server_matrix"), dict) else {}
    if kr_proxy_matrix:
        lines.append("## KR Proxy Server Matrix")
        lines.append(f"- matrix_ready: {kr_proxy_matrix.get('matrix_ready')}")
        lines.append(f"- traffic_gate_ok: {kr_proxy_matrix.get('traffic_gate_ok')}")
        lines.append(f"- cutover_ready: {kr_proxy_matrix.get('cutover_ready')}")
        lines.append(f"- public_mount_path: {kr_proxy_matrix.get('public_mount_path') or '(none)'}")
        lines.append(f"- upstream_origin: {kr_proxy_matrix.get('upstream_origin') or '(none)'}")
        lines.append("")

    kr_proxy_bundle = (packet.get("summaries") or {}).get("kr_proxy_server_bundle") if isinstance((packet.get("summaries") or {}).get("kr_proxy_server_bundle"), dict) else {}
    if kr_proxy_bundle:
        lines.append("## KR Proxy Server Bundle")
        lines.append(f"- bundle_ready: {kr_proxy_bundle.get('bundle_ready')}")
        lines.append(f"- public_mount_path: {kr_proxy_bundle.get('public_mount_path') or '(none)'}")
        lines.append(f"- upstream_origin: {kr_proxy_bundle.get('upstream_origin') or '(none)'}")
        lines.append(f"- file_count: {kr_proxy_bundle.get('file_count')}")
        lines.append(f"- output_dir: {kr_proxy_bundle.get('output_dir') or '(none)'}")
        lines.append("")

    kr_live_apply = (packet.get("summaries") or {}).get("kr_live_apply_packet") if isinstance((packet.get("summaries") or {}).get("kr_live_apply_packet"), dict) else {}
    if kr_live_apply:
        lines.append("## KR Live Apply Packet")
        lines.append(f"- apply_packet_ready: {kr_live_apply.get('apply_packet_ready')}")
        lines.append(f"- page_count: {kr_live_apply.get('page_count')}")
        lines.append(f"- service_page_count: {kr_live_apply.get('service_page_count')}")
        lines.append(f"- front_page_slug: {kr_live_apply.get('front_page_slug') or '(none)'}")
        lines.append(f"- menu_name: {kr_live_apply.get('menu_name') or '(none)'}")
        lines.append(f"- bridge_cta_count: {kr_live_apply.get('bridge_cta_count')}")
        lines.append("")
    kr_live_operator = (packet.get("summaries") or {}).get("kr_live_operator_checklist") if isinstance((packet.get("summaries") or {}).get("kr_live_operator_checklist"), dict) else {}
    if kr_live_operator:
        lines.append("## KR Live Operator Checklist")
        lines.append(f"- checklist_ready: {kr_live_operator.get('checklist_ready')}")
        lines.append(f"- platform_host: {kr_live_operator.get('platform_host') or '(none)'}")
        lines.append(f"- listing_host: {kr_live_operator.get('listing_host') or '(none)'}")
        lines.append(f"- public_mount_path: {kr_live_operator.get('public_mount_path') or '(none)'}")
        lines.append(f"- preflight_item_count: {kr_live_operator.get('preflight_item_count')}")
        lines.append(f"- validation_step_count: {kr_live_operator.get('validation_step_count')}")
        lines.append(f"- operator_input_count: {kr_live_operator.get('operator_input_count')}")
        lines.append("")

    improvement_loop = (packet.get("summaries") or {}).get("program_improvement_loop") if isinstance((packet.get("summaries") or {}).get("program_improvement_loop"), dict) else {}
    if improvement_loop:
        lines.append("## Program Improvement Loop")
        lines.append(f"- immediate_blocker_count: {improvement_loop.get('immediate_blocker_count')}")
        lines.append(f"- structural_improvement_count: {improvement_loop.get('structural_improvement_count')}")
        lines.append(f"- patent_hardening_count: {improvement_loop.get('patent_hardening_count')}")
        lines.append(f"- commercialization_gap_count: {improvement_loop.get('commercialization_gap_count')}")
        lines.append(f"- top_action_count: {improvement_loop.get('top_action_count')}")
        for row in improvement_loop.get("top_next_actions") or []:
            if isinstance(row, dict):
                lines.append(f"- top_action: [P{row.get('priority')}] {row.get('title')}: {row.get('action')}")
        lines.append("")

    lines.append("## Blockers")
    blockers = packet.get("blockers") or []
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Normalized Blockers")
    normalized = packet.get("normalized_blockers") or []
    if normalized:
        for item in normalized:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Next Actions")
    actions = packet.get("next_actions") or []
    if actions:
        for item in actions:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Required Inputs")
    lines.append(f"- seoul_live: {', '.join(required.get('seoul_live', [])) or '(none)'}")
    lines.append(f"- partner_fastest_path: {', '.join(required.get('partner_fastest_path', [])) or '(none)'}")
    lines.append(f"- partner_common: {', '.join(required.get('partner_common', [])) or '(none)'}")
    aggregate = required.get("partner_aggregate") if isinstance(required.get("partner_aggregate"), dict) else {}
    if aggregate:
        for key, value in aggregate.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- partner_aggregate: (none)")

    lines.append("")
    lines.append("## Seoul Live Checklist")
    seoul_items = (packet.get("handoff_checklists") or {}).get("seoul_live") if isinstance((packet.get("handoff_checklists") or {}).get("seoul_live"), list) else []
    if seoul_items:
        for item in seoul_items:
            lines.append(f"- {item.get('label')} ({item.get('owner')}): {item.get('description')}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Partner Decision")
    latest_remaining = list(partner_summary.get("latest_flow_remaining_required_inputs") or [])
    latest_resolved = list(partner_summary.get("latest_flow_resolved_inputs") or [])
    preview_scenario = str(partner_summary.get("preview_recommended_scenario") or "").strip()
    preview_remaining = list(partner_summary.get("preview_remaining_required_inputs") or [])
    preview_removed = list(partner_summary.get("preview_removed_inputs") or [])
    lines.append(
        f"- current_remaining_inputs: {', '.join(latest_remaining) or '(none)'} / "
        f"current_resolved_inputs: {', '.join(latest_resolved) or '(none)'}"
    )
    lines.append(f"- current_flow_scope_registered: {partner_summary.get('latest_flow_scope_registered')}")
    if preview_scenario:
        lines.append(
            f"- fastest_path: scenario={preview_scenario} "
            f"remaining={', '.join(preview_remaining) or '(none)'} "
            f"removed_vs_current={', '.join(preview_removed) or '(none)'}"
        )
    if preview_alignment:
        lines.append(
            f"- preview_alignment: ok={preview_alignment.get('ok')} "
            f"baseline_matches_current={preview_alignment.get('baseline_matches_current')} "
            f"recommended_clears_current={preview_alignment.get('recommended_clears_current')}"
        )
    resolution_summary = partner_summary.get("resolution_summary") if isinstance(partner_summary.get("resolution_summary"), dict) else {}
    if resolution_summary:
        lines.append(
            f"- resolution_check: ok={resolution_summary.get('ok')} "
            f"matches_preview_expected_remaining={resolution_summary.get('matches_preview_expected_remaining')}"
        )
    input_snapshot_summary = partner_summary.get("input_snapshot_summary") if isinstance(partner_summary.get("input_snapshot_summary"), dict) else {}
    if input_snapshot_summary:
        scenario_counts = input_snapshot_summary.get("scenario_counts") if isinstance(input_snapshot_summary.get("scenario_counts"), dict) else {}
        lines.append(
            f"- input_snapshot: ready_tenant_count={input_snapshot_summary.get('ready_tenant_count')} "
            f"partner_tenant_count={input_snapshot_summary.get('partner_tenant_count')} "
            f"scenarios={scenario_counts}"
        )
    simulation_summary = partner_summary.get("simulation_matrix_summary") if isinstance(partner_summary.get("simulation_matrix_summary"), dict) else {}
    if simulation_summary:
        lines.append(
            f"- simulation_matrix: ready_after_simulation_count={simulation_summary.get('ready_after_simulation_count')} "
            f"partner_count={simulation_summary.get('partner_count')} "
            f"all_ready_after_simulation={simulation_summary.get('all_ready_after_simulation')}"
        )
    lines.append(
        f"- common_required_inputs: {', '.join(partner_summary.get('common_required_inputs') or []) or '(none)'} "
        f"/ uniform_required_inputs={partner_summary.get('uniform_required_inputs')}"
    )
    for item in partner_summary.get("preview_next_actions") or []:
        lines.append(f"- preview_next_action: {item}")

    lines.append("")
    lines.append("## Partner Checklists")
    partner_items = (packet.get("handoff_checklists") or {}).get("partner_activation") if isinstance((packet.get("handoff_checklists") or {}).get("partner_activation"), list) else []
    for row in partner_items:
        descriptions = "; ".join(
            f"{item.get('label')}[{item.get('owner')}]"
            for item in (row.get("items") or [])
        )
        lines.append(
            f"- {row.get('tenant_id')} / {row.get('channel_id')}: "
            f"ready={row.get('activation_ready')} "
            f"required_inputs={descriptions or '(none)'}"
        )
    if not partner_items:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Artifacts")
    for key, value in (packet.get("artifacts") or {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a unified operations packet from latest readiness/release/risk/patent artifacts")
    parser.add_argument("--readiness", default="logs/live_release_readiness_latest.json")
    parser.add_argument("--release", default="logs/seoul_widget_embed_release_latest.json")
    parser.add_argument("--risk-map", default="logs/system_risk_map_latest.json")
    parser.add_argument("--attorney", default="logs/attorney_handoff_latest.json")
    parser.add_argument("--platform-front-audit", default="logs/platform_front_audit_latest.json")
    parser.add_argument("--surface-stack-audit", default="logs/surface_stack_audit_latest.json")
    parser.add_argument("--private-engine-proxy-spec", default="logs/private_engine_proxy_spec_latest.json")
    parser.add_argument("--wp-surface-lab", default="logs/wp_surface_lab_latest.json")
    parser.add_argument("--wp-surface-lab-runtime", default="logs/wp_surface_lab_runtime_latest.json")
    parser.add_argument("--wp-surface-lab-runtime-validation", default="logs/wp_surface_lab_runtime_validation_latest.json")
    parser.add_argument("--wp-surface-lab-php-runtime", default="logs/wp_surface_lab_php_runtime_latest.json")
    parser.add_argument("--wp-surface-lab-php-fallback", default="logs/wp_surface_lab_php_fallback_latest.json")
    parser.add_argument("--wp-platform-assets", default="logs/wp_platform_assets_latest.json")
    parser.add_argument("--wordpress-platform-ia", default="logs/wordpress_platform_ia_latest.json")
    parser.add_argument("--wp-platform-blueprints", default="logs/wp_platform_blueprints_latest.json")
    parser.add_argument("--wordpress-staging-apply-plan", default="logs/wordpress_staging_apply_plan_latest.json")
    parser.add_argument("--wp-surface-lab-apply", default="logs/wp_surface_lab_apply_latest.json")
    parser.add_argument("--wp-surface-lab-apply-verify-cycle", default="logs/wp_surface_lab_apply_verify_cycle_latest.json")
    parser.add_argument("--wp-surface-lab-page-verify", default="logs/wp_surface_lab_page_verify_latest.json")
    parser.add_argument("--wordpress-platform-encoding-audit", default="logs/wordpress_platform_encoding_audit_latest.json")
    parser.add_argument("--wordpress-platform-ux-audit", default="logs/wordpress_platform_ux_audit_latest.json")
    parser.add_argument("--wordpress-platform-strategy", default="logs/wordpress_platform_strategy_latest.json")
    parser.add_argument("--astra-design-reference", default="logs/astra_design_reference_latest.json")
    parser.add_argument("--kr-reverse-proxy-cutover", default="logs/kr_reverse_proxy_cutover_latest.json")
    parser.add_argument("--kr-traffic-gate-audit", default="logs/kr_traffic_gate_audit_latest.json")
    parser.add_argument("--kr-deploy-readiness", default="logs/kr_platform_deploy_ready_latest.json")
    parser.add_argument("--kr-preview-deploy", default="logs/kr_platform_front_preview_latest.json")
    parser.add_argument("--onboarding-validation", default="logs/tenant_onboarding_validation_latest.json")
    parser.add_argument("--partner-flow", default="logs/partner_onboarding_flow_latest.json")
    parser.add_argument("--partner-preview", default="logs/partner_activation_preview_latest.json")
    parser.add_argument("--partner-preview-alignment", default="logs/partner_preview_alignment_latest.json")
    parser.add_argument("--partner-resolution", default="logs/partner_activation_resolution_latest.json")
    parser.add_argument("--partner-input-snapshot", default="logs/partner_input_snapshot_latest.json")
    parser.add_argument("--partner-simulation-matrix", default="logs/partner_activation_simulation_matrix_latest.json")
    parser.add_argument("--yangdo-recommendation-qa", default="logs/yangdo_recommendation_qa_matrix_latest.json")
    parser.add_argument("--yangdo-recommendation-precision-matrix", default="logs/yangdo_recommendation_precision_matrix_latest.json")
    parser.add_argument("--yangdo-recommendation-diversity-audit", default="logs/yangdo_recommendation_diversity_audit_latest.json")
    parser.add_argument("--yangdo-recommendation-contract-audit", default="logs/yangdo_recommendation_contract_audit_latest.json")
    parser.add_argument("--yangdo-recommendation-bridge-packet", default="logs/yangdo_recommendation_bridge_packet_latest.json")
    parser.add_argument("--yangdo-recommendation-ux-packet", default="logs/yangdo_recommendation_ux_packet_latest.json")
    parser.add_argument("--yangdo-recommendation-alignment-audit", default="logs/yangdo_recommendation_alignment_audit_latest.json")
    parser.add_argument("--yangdo-zero-display-recovery-audit", default="logs/yangdo_zero_display_recovery_audit_latest.json")
    parser.add_argument("--yangdo-service-copy-packet", default="logs/yangdo_service_copy_packet_latest.json")
    parser.add_argument("--permit-service-copy-packet", default="logs/permit_service_copy_packet_latest.json")
    parser.add_argument("--permit-service-alignment-audit", default="logs/permit_service_alignment_audit_latest.json")
    parser.add_argument("--permit-rental-lane-packet", default="logs/permit_rental_lane_packet_latest.json")
    parser.add_argument("--permit-service-ux-packet", default="logs/permit_service_ux_packet_latest.json")
    parser.add_argument("--permit-public-contract-audit", default="logs/permit_public_contract_audit_latest.json")
    parser.add_argument("--partner-input-handoff-packet", default="logs/partner_input_handoff_packet_latest.json")
    parser.add_argument("--partner-input-operator-flow", default="logs/partner_input_operator_flow_latest.json")
    parser.add_argument("--widget-rental-catalog", default="logs/widget_rental_catalog_latest.json")
    parser.add_argument("--program-improvement-loop", default="logs/program_improvement_loop_latest.json")
    parser.add_argument("--ai-platform-first-principles-review", default="logs/ai_platform_first_principles_review_latest.json")
    parser.add_argument("--system-split-first-principles-packet", default="logs/system_split_first_principles_packet_latest.json")
    parser.add_argument("--next-batch-focus-packet", default="logs/next_batch_focus_packet_latest.json")
    parser.add_argument("--listing-platform-bridge-policy", default="logs/listing_platform_bridge_policy_latest.json")
    parser.add_argument("--co-listing-bridge-snippets", default="logs/co_listing_bridge_snippets_latest.json")
    parser.add_argument("--co-listing-bridge-operator-checklist", default="logs/co_listing_bridge_operator_checklist_latest.json")
    parser.add_argument("--co-listing-live-injection-plan", default="logs/co_listing_live_injection_plan_latest.json")
    parser.add_argument("--co-listing-injection-bundle", default="logs/co_listing_injection_bundle_latest.json")
    parser.add_argument("--co-listing-bridge-apply-packet", default="logs/co_listing_bridge_apply_packet_latest.json")
    parser.add_argument("--kr-proxy-server-matrix", default="logs/kr_proxy_server_matrix_latest.json")
    parser.add_argument("--kr-proxy-server-bundle", default="logs/kr_proxy_server_bundle_latest.json")
    parser.add_argument("--kr-live-apply-packet", default="logs/kr_live_apply_packet_latest.json")
    parser.add_argument("--kr-live-operator-checklist", default="logs/kr_live_operator_checklist_latest.json")
    parser.add_argument("--json", default="logs/operations_packet_latest.json")
    parser.add_argument("--md", default="logs/operations_packet_latest.md")
    args = parser.parse_args()

    packet = build_operations_packet(
        readiness_path=(ROOT / str(args.readiness)).resolve(),
        release_path=(ROOT / str(args.release)).resolve(),
        risk_map_path=(ROOT / str(args.risk_map)).resolve(),
        attorney_path=(ROOT / str(args.attorney)).resolve(),
        platform_front_audit_path=(ROOT / str(args.platform_front_audit)).resolve(),
        surface_stack_audit_path=(ROOT / str(args.surface_stack_audit)).resolve(),
        private_engine_proxy_spec_path=(ROOT / str(args.private_engine_proxy_spec)).resolve(),
        wp_surface_lab_path=(ROOT / str(args.wp_surface_lab)).resolve(),
        wp_surface_lab_runtime_path=(ROOT / str(args.wp_surface_lab_runtime)).resolve(),
        wp_surface_lab_runtime_validation_path=(ROOT / str(args.wp_surface_lab_runtime_validation)).resolve(),
        wp_surface_lab_php_runtime_path=(ROOT / str(args.wp_surface_lab_php_runtime)).resolve(),
        wp_surface_lab_php_fallback_path=(ROOT / str(args.wp_surface_lab_php_fallback)).resolve(),
        wp_platform_assets_path=(ROOT / str(args.wp_platform_assets)).resolve(),
        wordpress_platform_ia_path=(ROOT / str(args.wordpress_platform_ia)).resolve(),
        wp_platform_blueprints_path=(ROOT / str(args.wp_platform_blueprints)).resolve(),
        wordpress_staging_apply_plan_path=(ROOT / str(args.wordpress_staging_apply_plan)).resolve(),
        wp_surface_lab_apply_path=(ROOT / str(args.wp_surface_lab_apply)).resolve(),
        wp_surface_lab_apply_verify_cycle_path=(ROOT / str(args.wp_surface_lab_apply_verify_cycle)).resolve(),
        wp_surface_lab_page_verify_path=(ROOT / str(args.wp_surface_lab_page_verify)).resolve(),
        wordpress_platform_encoding_audit_path=(ROOT / str(args.wordpress_platform_encoding_audit)).resolve(),
        wordpress_platform_ux_audit_path=(ROOT / str(args.wordpress_platform_ux_audit)).resolve(),
        wordpress_platform_strategy_path=(ROOT / str(args.wordpress_platform_strategy)).resolve(),
        astra_design_reference_path=(ROOT / str(args.astra_design_reference)).resolve(),
        kr_reverse_proxy_cutover_path=(ROOT / str(args.kr_reverse_proxy_cutover)).resolve(),
        kr_traffic_gate_audit_path=(ROOT / str(args.kr_traffic_gate_audit)).resolve(),
        kr_deploy_readiness_path=(ROOT / str(args.kr_deploy_readiness)).resolve(),
        kr_preview_deploy_path=(ROOT / str(args.kr_preview_deploy)).resolve(),
        onboarding_validation_path=(ROOT / str(args.onboarding_validation)).resolve(),
        partner_flow_path=(ROOT / str(args.partner_flow)).resolve(),
        partner_preview_path=(ROOT / str(args.partner_preview)).resolve(),
        partner_preview_alignment_path=(ROOT / str(args.partner_preview_alignment)).resolve(),
        partner_resolution_path=(ROOT / str(args.partner_resolution)).resolve(),
        partner_input_snapshot_path=(ROOT / str(args.partner_input_snapshot)).resolve(),
        partner_simulation_matrix_path=(ROOT / str(args.partner_simulation_matrix)).resolve(),
        yangdo_recommendation_qa_path=(ROOT / str(args.yangdo_recommendation_qa)).resolve(),
        yangdo_recommendation_precision_matrix_path=(ROOT / str(args.yangdo_recommendation_precision_matrix)).resolve(),
        yangdo_recommendation_diversity_audit_path=(ROOT / str(args.yangdo_recommendation_diversity_audit)).resolve(),
        yangdo_recommendation_contract_audit_path=(ROOT / str(args.yangdo_recommendation_contract_audit)).resolve(),
        yangdo_recommendation_bridge_packet_path=(ROOT / str(args.yangdo_recommendation_bridge_packet)).resolve(),
        yangdo_recommendation_ux_packet_path=(ROOT / str(args.yangdo_recommendation_ux_packet)).resolve(),
        yangdo_recommendation_alignment_audit_path=(ROOT / str(args.yangdo_recommendation_alignment_audit)).resolve(),
        yangdo_zero_display_recovery_audit_path=(ROOT / str(args.yangdo_zero_display_recovery_audit)).resolve(),
        yangdo_service_copy_packet_path=(ROOT / str(args.yangdo_service_copy_packet)).resolve(),
        permit_service_copy_packet_path=(ROOT / str(args.permit_service_copy_packet)).resolve(),
        permit_service_alignment_audit_path=(ROOT / str(args.permit_service_alignment_audit)).resolve(),
        permit_rental_lane_packet_path=(ROOT / str(args.permit_rental_lane_packet)).resolve(),
        permit_service_ux_packet_path=(ROOT / str(args.permit_service_ux_packet)).resolve(),
        permit_public_contract_audit_path=(ROOT / str(args.permit_public_contract_audit)).resolve(),
        partner_input_handoff_packet_path=(ROOT / str(args.partner_input_handoff_packet)).resolve(),
        partner_input_operator_flow_path=(ROOT / str(args.partner_input_operator_flow)).resolve(),
        widget_rental_catalog_path=(ROOT / str(args.widget_rental_catalog)).resolve(),
        program_improvement_loop_path=(ROOT / str(args.program_improvement_loop)).resolve(),
        ai_platform_first_principles_review_path=(ROOT / str(args.ai_platform_first_principles_review)).resolve(),
        system_split_first_principles_packet_path=(ROOT / str(args.system_split_first_principles_packet)).resolve(),
        next_batch_focus_packet_path=(ROOT / str(args.next_batch_focus_packet)).resolve(),
        listing_platform_bridge_policy_path=(ROOT / str(args.listing_platform_bridge_policy)).resolve(),
        co_listing_bridge_snippets_path=(ROOT / str(args.co_listing_bridge_snippets)).resolve(),
        co_listing_bridge_operator_checklist_path=(ROOT / str(args.co_listing_bridge_operator_checklist)).resolve(),
        co_listing_live_injection_plan_path=(ROOT / str(args.co_listing_live_injection_plan)).resolve(),
        co_listing_injection_bundle_path=(ROOT / str(args.co_listing_injection_bundle)).resolve(),
        co_listing_bridge_apply_packet_path=(ROOT / str(args.co_listing_bridge_apply_packet)).resolve(),
        kr_proxy_server_matrix_path=(ROOT / str(args.kr_proxy_server_matrix)).resolve(),
        kr_proxy_server_bundle_path=(ROOT / str(args.kr_proxy_server_bundle)).resolve(),
        kr_live_apply_packet_path=(ROOT / str(args.kr_live_apply_packet)).resolve(),
        kr_live_operator_checklist_path=(ROOT / str(args.kr_live_operator_checklist)).resolve(),
    )

    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "json": str(json_path),
                "md": str(md_path),
                "quality_green": (packet.get("go_live") or {}).get("quality_green"),
                "blocker_count": len(packet.get("blockers") or []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
