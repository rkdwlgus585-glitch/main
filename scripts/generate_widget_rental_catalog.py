#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_THRESHOLDS = ROOT / "tenant_config" / "plan_thresholds.json"
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_PERMIT_SELECTOR = ROOT / "logs" / "permit_selector_catalog_latest.json"
DEFAULT_PERMIT_PLATFORM = ROOT / "logs" / "permit_platform_catalog_latest.json"
DEFAULT_PERMIT_MASTER = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_PERMIT_PROVENANCE = ROOT / "logs" / "permit_provenance_audit_latest.json"
DEFAULT_PERMIT_PATENT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_PERMIT_FAMILY_CASE_GOLDSET = ROOT / "logs" / "permit_family_case_goldset_latest.json"
DEFAULT_PERMIT_CASE_STORY_SURFACE = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_PERMIT_OPERATOR_DEMO_PACKET = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_YANGDO_PRECISION = ROOT / "logs" / "yangdo_recommendation_precision_matrix_latest.json"
DEFAULT_YANGDO_CONTRACT = ROOT / "logs" / "yangdo_recommendation_contract_audit_latest.json"


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


def _permit_family_checksum_samples(permit_patent: Dict[str, Any], limit: int = 6) -> List[Dict[str, str]]:
    rows = [row for row in list(permit_patent.get("families") or []) if isinstance(row, dict)]
    samples: List[Dict[str, str]] = []
    for row in rows:
        claim_packet = row.get("claim_packet") if isinstance(row.get("claim_packet"), dict) else {}
        source_proof_summary = (
            claim_packet.get("source_proof_summary")
            if isinstance(claim_packet.get("source_proof_summary"), dict)
            else {}
        )
        checksums = [
            str(item or "").strip()
            for item in list(source_proof_summary.get("checksum_samples") or [])
            if str(item or "").strip()
        ]
        if not checksums:
            continue
        samples.append(
            {
                "family_key": str(row.get("family_key") or "").strip(),
                "claim_id": str(claim_packet.get("claim_id") or "").strip(),
                "checksum": checksums[0],
            }
        )
        if len(samples) >= limit:
            break
    return samples


def _permit_family_case_samples(
    permit_family_case_goldset: Dict[str, Any],
    limit: int = 120,
) -> List[Dict[str, str]]:
    families = [row for row in list(permit_family_case_goldset.get("families") or []) if isinstance(row, dict)]
    samples: List[Dict[str, str]] = []
    for family in families:
        family_key = str(family.get("family_key") or "").strip()
        claim_id = str(family.get("claim_id") or "").strip()
        for case in list(family.get("cases") or []):
            if not isinstance(case, dict):
                continue
            expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
            sample = {
                "family_key": family_key,
                "claim_id": claim_id or str(case.get("claim_id") or "").strip(),
                "case_id": str(case.get("case_id") or "").strip(),
                "case_kind": str(case.get("case_kind") or "").strip(),
                "service_code": str(case.get("service_code") or "").strip(),
                "expected_status": str(expected.get("overall_status") or "").strip(),
                "proof_coverage_ratio": str(expected.get("proof_coverage_ratio") or "").strip(),
                "review_reason": str(expected.get("review_reason") or "").strip(),
                "manual_review_expected": bool(expected.get("manual_review_expected", False)),
            }
            if not sample["case_id"] or not sample["family_key"]:
                continue
            samples.append(sample)
            if len(samples) >= limit:
                return samples
    return samples


def _permit_case_story_samples(
    permit_case_story_surface: Dict[str, Any],
    limit: int = 24,
) -> List[Dict[str, Any]]:
    families = [row for row in list(permit_case_story_surface.get("families") or []) if isinstance(row, dict)]
    samples: List[Dict[str, Any]] = []
    for family in families:
        review_reasons = [
            str(item.get("review_reason") or "").strip()
            for item in list(family.get("representative_cases") or [])
            if isinstance(item, dict) and str(item.get("review_reason") or "").strip()
        ]
        unique_review_reasons: List[str] = []
        for item in review_reasons:
            if item not in unique_review_reasons:
                unique_review_reasons.append(item)
        representative_preset_ids: List[str] = []
        for item in list(family.get("representative_cases") or []):
            if not isinstance(item, dict):
                continue
            preset_id = str(item.get("preset_id") or "").strip()
            if preset_id and preset_id not in representative_preset_ids:
                representative_preset_ids.append(preset_id)
        sample = {
            "family_key": str(family.get("family_key") or "").strip(),
            "claim_id": str(family.get("claim_id") or "").strip(),
            "preset_total": int(family.get("preset_total", 0) or 0),
            "manual_review_preset_total": int(family.get("manual_review_preset_total", 0) or 0),
            "review_reasons": unique_review_reasons[:3],
            "representative_preset_ids": representative_preset_ids[:3],
            "operator_story_points": [
                str(item or "").strip()
                for item in list(family.get("operator_story_points") or [])
                if str(item or "").strip()
            ][:2],
        }
        if not sample["family_key"]:
            continue
        samples.append(sample)
        if len(samples) >= limit:
            break
    return samples


def _permit_partner_demo_samples(
    permit_operator_demo_packet: Dict[str, Any],
    limit: int = 24,
) -> List[Dict[str, Any]]:
    families = [row for row in list(permit_operator_demo_packet.get("families") or []) if isinstance(row, dict)]
    samples: List[Dict[str, Any]] = []
    for family in families:
        cases = [row for row in list(family.get("demo_cases") or []) if isinstance(row, dict)]
        review_reasons: List[str] = []
        representative_services: List[str] = []
        representative_statuses: List[str] = []
        manual_review_demo_total = 0
        for case in cases:
            reason = str(case.get("review_reason") or "").strip()
            if reason and reason not in review_reasons:
                review_reasons.append(reason)
            service_name = str(case.get("service_name") or case.get("service_code") or "").strip()
            if service_name and service_name not in representative_services:
                representative_services.append(service_name)
            expected_status = str(case.get("expected_status") or "").strip()
            if expected_status and expected_status not in representative_statuses:
                representative_statuses.append(expected_status)
            if bool(case.get("manual_review_expected", False)):
                manual_review_demo_total += 1
        sample = {
            "family_key": str(family.get("family_key") or "").strip(),
            "claim_id": str(family.get("claim_id") or "").strip(),
            "claim_title": str(family.get("claim_title") or "").strip(),
            "proof_coverage_ratio": str(family.get("proof_coverage_ratio") or "").strip(),
            "demo_case_total": len(cases),
            "manual_review_demo_total": manual_review_demo_total,
            "review_reasons": review_reasons[:3],
            "representative_services": representative_services[:3],
            "representative_statuses": representative_statuses[:3],
        }
        if not sample["family_key"] or not sample["claim_id"]:
            continue
        samples.append(sample)
        if len(samples) >= limit:
            break
    return samples


def _estimate_request_token_cost(systems: List[str], token_estimates: Dict[str, Any]) -> Dict[str, int]:
    estimates: Dict[str, int] = {}
    if "yangdo" in systems:
        estimates["yangdo"] = int(token_estimates.get("yangdo_ok", 0) or 0)
    if "permit" in systems:
        estimates["permit"] = int(token_estimates.get("permit_ok", 0) or 0)
    if estimates:
        estimates["combo"] = sum(estimates.values())
    return estimates


def _response_tier(features: List[str], plan: str) -> str:
    if plan == "pro_internal" or any(str(item).endswith("_internal") for item in features):
        return "internal"
    if any(str(item).endswith("_detail") for item in features):
        return "detail"
    return "summary"


def _delivery_modes(plan: str, systems: List[str], features: List[str]) -> List[str]:
    if plan == "pro_internal":
        return ["internal_widget", "internal_api"]
    if plan == "pro":
        modes = ["widget", "api"]
        if "consult" in features:
            modes.append("crm_webhook")
        return modes
    return ["widget"]


def _event_ceiling(plan_meta: Dict[str, Any], request_tokens: Dict[str, int]) -> Dict[str, Any]:
    included_tokens = int(plan_meta.get("included_tokens", 0) or 0)
    max_usage_events = int(plan_meta.get("max_usage_events", 0) or 0)
    combo_tokens = int(request_tokens.get("combo", 0) or 0)
    token_based_limit = 0
    if included_tokens > 0 and combo_tokens > 0:
        token_based_limit = included_tokens // combo_tokens
    effective_limit: int | None
    if included_tokens <= 0 and max_usage_events <= 0:
        effective_limit = None
    elif included_tokens <= 0:
        effective_limit = max_usage_events
    elif max_usage_events <= 0:
        effective_limit = token_based_limit
    else:
        effective_limit = min(token_based_limit, max_usage_events)
    return {
        "included_tokens": included_tokens,
        "max_usage_events": max_usage_events,
        "token_based_limit": token_based_limit,
        "effective_limit": effective_limit,
    }


def _yangdo_recommendation_profile(*, systems: List[str], plan: str) -> Dict[str, Any]:
    enabled = "yangdo" in systems
    if not enabled:
        return {
            "enabled": False,
            "visibility": "not_applicable",
            "safe_fields": [],
            "detail_fields": [],
            "internal_only_fields": [],
        }
    if plan == "pro_internal":
        visibility = "internal_full"
    elif plan == "pro":
        visibility = "detail_explainable"
    else:
        visibility = "safe_summary"
    return {
        "enabled": True,
        "visibility": visibility,
        "safe_fields": [
            "recommendation_label",
            "recommendation_focus",
            "reasons",
            "display_low_eok",
            "display_high_eok",
            "url",
        ],
        "detail_fields": [
            "precision_tier",
            "fit_summary",
            "matched_axes",
            "mismatch_flags",
        ],
        "internal_only_fields": [
            "recommendation_score",
            "similarity",
        ],
    }


def _recommendation_package_lane(*, recommendation_enabled: bool, plan: str, features: List[str], delivery_modes: List[str]) -> str:
    if not recommendation_enabled:
        return "not_applicable"
    if plan == "pro_internal":
        return "internal_full"
    if plan == "standard":
        return "summary_market_bridge"
    if "consult" in features or "crm_webhook" in delivery_modes:
        return "consult_assist"
    return "detail_explainable"


def _recommendation_lane_positioning() -> Dict[str, Dict[str, Any]]:
    return {
        "summary_market_bridge": {
            "role": "public_entry_lane",
            "who_its_for": "공개 화면에서 가격 범위와 추천 요약만 보여주고 바로 시장 확인으로 보내려는 파트너",
            "upgrade_target": "detail_explainable",
            "cta_bias": "market_first",
        },
        "detail_explainable": {
            "role": "standalone_explainable_lane",
            "who_its_for": "상담 workflow 없이도 추천 정밀도와 일치축 설명까지 직접 제공하려는 파트너",
            "upgrade_target": "consult_assist",
            "cta_bias": "explanation_first",
        },
        "consult_assist": {
            "role": "consult_connected_lane",
            "who_its_for": "추천 설명과 함께 상담 또는 CRM 후속 액션까지 연결하려는 파트너",
            "upgrade_target": "internal_full",
            "cta_bias": "consult_first_when_precision_is_low",
        },
        "internal_full": {
            "role": "internal_qa_lane",
            "who_its_for": "원시 추천 진단과 운영 검수를 직접 보는 내부 전용 tenant",
            "upgrade_target": "",
            "cta_bias": "operator_only",
        },
    }


def _permit_package_lane(*, permit_enabled: bool, plan: str, features: List[str], delivery_modes: List[str]) -> str:
    if not permit_enabled:
        return "not_applicable"
    if plan == "pro_internal":
        return "internal_full"
    if plan == "standard":
        return "summary_self_check"
    if "consult" in features or "crm_webhook" in delivery_modes:
        return "manual_review_assist"
    return "detail_checklist"


def _permit_lane_positioning() -> Dict[str, Dict[str, Any]]:
    return {
        "summary_self_check": {
            "role": "public_self_check_lane",
            "who_its_for": "Public widget users who need a fast permit precheck before escalating.",
            "upgrade_target": "detail_checklist",
            "cta_bias": "self_check_first",
        },
        "detail_checklist": {
            "role": "explainable_checklist_lane",
            "who_its_for": "Partners who need criterion-by-criterion checklist output without manual follow-up by default.",
            "upgrade_target": "manual_review_assist",
            "cta_bias": "checklist_first",
        },
        "manual_review_assist": {
            "role": "manual_review_assist_lane",
            "who_its_for": "Partners who need explainable checklist output plus manual-review or consultant follow-up for complex registrations.",
            "upgrade_target": "internal_full",
            "cta_bias": "manual_review_when_complex",
        },
        "internal_full": {
            "role": "internal_registry_lane",
            "who_its_for": "Internal tenants that can inspect pending criteria, mapping confidence, and QA-only registry details.",
            "upgrade_target": "",
            "cta_bias": "operator_only",
        },
    }


def _build_offering_rows(
    *,
    registry: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> List[Dict[str, Any]]:
    plans = thresholds.get("plans") if isinstance(thresholds.get("plans"), dict) else {}
    token_estimates = thresholds.get("token_estimates") if isinstance(thresholds.get("token_estimates"), dict) else {}
    offerings = registry.get("offering_templates") if isinstance(registry.get("offering_templates"), list) else []
    rows: List[Dict[str, Any]] = []
    for offering in offerings:
        if not isinstance(offering, dict):
            continue
        offering_id = str(offering.get("offering_id") or "").strip()
        if not offering_id:
            continue
        plan = str(offering.get("plan") or "standard").strip() or "standard"
        systems = _as_list(offering.get("allowed_systems"))
        features = _as_list(offering.get("allowed_features"))
        plan_meta = plans.get(plan) if isinstance(plans.get(plan), dict) else {}
        request_tokens = _estimate_request_token_cost(systems, token_estimates)
        limits = _event_ceiling(plan_meta, request_tokens)
        recommendation = _yangdo_recommendation_profile(systems=systems, plan=plan)
        delivery_modes = _delivery_modes(plan, systems, features)
        package_lane = _recommendation_package_lane(
            recommendation_enabled=bool(recommendation.get("enabled")),
            plan=plan,
            features=features,
            delivery_modes=delivery_modes,
        )
        permit_enabled = "permit" in systems
        permit_package_lane = _permit_package_lane(
            permit_enabled=permit_enabled,
            plan=plan,
            features=features,
            delivery_modes=delivery_modes,
        )
        rows.append(
            {
                "offering_id": offering_id,
                "display_name": str(offering.get("display_name") or offering_id),
                "plan": plan,
                "systems": systems,
                "features": features,
                "response_tier": _response_tier(features, plan),
                "delivery_modes": delivery_modes,
                "request_token_estimates": request_tokens,
                "limits": limits,
                "overage_price_per_1k_usd": float(plan_meta.get("overage_price_per_1k_usd", 0.0) or 0.0),
                "recommendation_enabled": bool(recommendation.get("enabled")),
                "recommendation_visibility": str(recommendation.get("visibility") or "not_applicable"),
                "recommendation_package_lane": package_lane,
                "recommendation_fields": recommendation,
                "permit_enabled": permit_enabled,
                "permit_package_lane": permit_package_lane,
                "recommended_rental_position": (
                    "public_widget_standard"
                    if plan == "standard"
                    else "partner_api_or_detail" if plan == "pro" else "internal_unlimited"
                ),
            }
        )
    return rows


def build_widget_rental_catalog(
    *,
    registry_path: Path,
    thresholds_path: Path,
    operations_path: Path | None = None,
    permit_selector_path: Path | None = None,
    permit_platform_path: Path | None = None,
    permit_master_path: Path | None = None,
    permit_provenance_path: Path | None = None,
    permit_patent_path: Path | None = None,
    permit_family_case_goldset_path: Path | None = None,
    permit_case_story_surface_path: Path | None = None,
    permit_operator_demo_packet_path: Path | None = None,
    yangdo_precision_path: Path | None = None,
    yangdo_contract_path: Path | None = None,
) -> Dict[str, Any]:
    registry = _load_json(registry_path)
    thresholds = _load_json(thresholds_path)
    operations = _load_json(operations_path or Path())
    permit_selector = _load_json(permit_selector_path or Path())
    permit_platform = _load_json(permit_platform_path or Path())
    permit_master = _load_json(permit_master_path or Path())
    permit_provenance = _load_json(permit_provenance_path or Path())
    permit_patent = _load_json(permit_patent_path or Path())
    permit_family_case_goldset = _load_json(permit_family_case_goldset_path or Path())
    permit_case_story_surface = _load_json(permit_case_story_surface_path or Path())
    permit_operator_demo_packet = _load_json(permit_operator_demo_packet_path or Path())
    yangdo_precision = _load_json(yangdo_precision_path or Path())
    yangdo_contract = _load_json(yangdo_contract_path or Path())

    topology = operations.get("topology") if isinstance(operations.get("topology"), dict) else {}
    decisions = operations.get("decisions") if isinstance(operations.get("decisions"), dict) else {}
    tenants = registry.get("tenants") if isinstance(registry.get("tenants"), list) else []
    default_tenant_id = str(registry.get("default_tenant_id") or "").strip()
    offering_rows = _build_offering_rows(registry=registry, thresholds=thresholds)

    internal_tenants = []
    for tenant in tenants:
        if not isinstance(tenant, dict):
            continue
        if str(tenant.get("plan") or "") != "pro_internal":
            continue
        internal_tenants.append(
            {
                "tenant_id": str(tenant.get("tenant_id") or ""),
                "display_name": str(tenant.get("display_name") or tenant.get("tenant_id") or ""),
                "hosts": _as_list(tenant.get("hosts")),
                "systems": _as_list(tenant.get("allowed_systems")),
                "role": (
                    "main_platform"
                    if str(tenant.get("tenant_id") or "") == default_tenant_id
                    else "internal_unlimited_consumer"
                ),
            }
        )

    standard_rows = [row for row in offering_rows if row.get("plan") == "standard"]
    pro_rows = [row for row in offering_rows if row.get("plan") == "pro"]
    combo_rows = [row for row in offering_rows if len(row.get("systems") or []) > 1]
    single_rows = [row for row in offering_rows if len(row.get("systems") or []) == 1]
    recommendation_rows = [row for row in offering_rows if bool(row.get("recommendation_enabled"))]
    recommendation_standard_rows = [row for row in recommendation_rows if row.get("plan") == "standard"]
    recommendation_detail_rows = [row for row in recommendation_rows if row.get("plan") == "pro"]
    recommendation_internal_rows = [row for row in recommendation_rows if row.get("plan") == "pro_internal"]
    recommendation_summary_bridge_rows = [
        row for row in recommendation_rows if row.get("recommendation_package_lane") == "summary_market_bridge"
    ]
    recommendation_detail_explainable_rows = [
        row for row in recommendation_rows if row.get("recommendation_package_lane") == "detail_explainable"
    ]
    recommendation_consult_assist_rows = [
        row for row in recommendation_rows if row.get("recommendation_package_lane") == "consult_assist"
    ]
    permit_rows = [row for row in offering_rows if bool(row.get("permit_enabled"))]
    permit_standard_rows = [row for row in permit_rows if row.get("permit_package_lane") == "summary_self_check"]
    permit_detail_rows = [row for row in permit_rows if row.get("permit_package_lane") == "detail_checklist"]
    permit_assist_rows = [row for row in permit_rows if row.get("permit_package_lane") == "manual_review_assist"]
    permit_internal_rows = [row for row in permit_rows if row.get("permit_package_lane") == "internal_full"]
    permit_selector_summary = permit_selector.get("summary") if isinstance(permit_selector.get("summary"), dict) else {}
    permit_platform_summary = permit_platform.get("summary") if isinstance(permit_platform.get("summary"), dict) else {}
    permit_master_summary = permit_master.get("summary") if isinstance(permit_master.get("summary"), dict) else {}
    permit_provenance_summary = (
        permit_provenance.get("summary") if isinstance(permit_provenance.get("summary"), dict) else {}
    )
    permit_patent_summary = (
        permit_patent.get("summary") if isinstance(permit_patent.get("summary"), dict) else {}
    )
    permit_checksum_samples = _permit_family_checksum_samples(permit_patent)
    permit_family_case_goldset_summary = (
        permit_family_case_goldset.get("summary")
        if isinstance(permit_family_case_goldset.get("summary"), dict)
        else {}
    )
    permit_family_case_samples = _permit_family_case_samples(permit_family_case_goldset)
    permit_case_story_surface_summary = (
        permit_case_story_surface.get("summary")
        if isinstance(permit_case_story_surface.get("summary"), dict)
        else {}
    )
    permit_case_story_samples = _permit_case_story_samples(permit_case_story_surface)
    permit_operator_demo_summary = (
        permit_operator_demo_packet.get("summary")
        if isinstance(permit_operator_demo_packet.get("summary"), dict)
        else {}
    )
    permit_partner_demo_samples = _permit_partner_demo_samples(permit_operator_demo_packet)
    permit_case_parity_family_total = len(
        {
            str(item.get("family_key") or "").strip()
            for item in permit_family_case_samples
            if str(item.get("family_key") or "").strip()
        }
    )
    yangdo_precision_summary = (
        yangdo_precision.get("summary") if isinstance(yangdo_precision.get("summary"), dict) else {}
    )
    yangdo_contract_summary = (
        yangdo_contract.get("summary") if isinstance(yangdo_contract.get("summary"), dict) else {}
    )

    summary = {
        "offering_count": len(offering_rows),
        "standard_offering_count": len(standard_rows),
        "pro_offering_count": len(pro_rows),
        "combo_offering_count": len(combo_rows),
        "single_system_offering_count": len(single_rows),
        "yangdo_recommendation_offering_count": len(recommendation_rows),
        "yangdo_recommendation_standard_count": len(recommendation_standard_rows),
        "yangdo_recommendation_detail_count": len(recommendation_detail_rows),
        "yangdo_recommendation_internal_count": len(recommendation_internal_rows),
        "yangdo_recommendation_summary_bridge_count": len(recommendation_summary_bridge_rows),
        "yangdo_recommendation_detail_lane_count": len(recommendation_detail_explainable_rows),
        "yangdo_recommendation_consult_assist_count": len(recommendation_consult_assist_rows),
        "permit_offering_count": len(permit_rows),
        "permit_standard_count": len(permit_standard_rows),
        "permit_detail_checklist_count": len(permit_detail_rows),
        "permit_manual_review_assist_count": len(permit_assist_rows),
        "permit_internal_count": len(permit_internal_rows),
        "internal_tenant_count": len(internal_tenants),
        "public_platform_host": str(topology.get("main_platform_host") or "seoulmna.kr"),
        "listing_market_host": str(topology.get("listing_market_host") or "seoulmna.co.kr"),
        "public_mount_host": str(topology.get("public_calculator_mount_host") or topology.get("main_platform_host") or "seoulmna.kr"),
        "private_engine_public_path": str(topology.get("private_engine_public_path") or "/_calc/*"),
        "partner_uniform_required_inputs": bool(decisions.get("partner_uniform_required_inputs")),
        "permit_selector_entry_total": int(permit_selector_summary.get("selector_entry_total", 0) or 0),
        "permit_selector_focus_total": int(permit_selector_summary.get("selector_focus_total", 0) or 0),
        "permit_selector_inferred_total": int(permit_selector_summary.get("selector_inferred_total", 0) or 0),
        "permit_platform_industry_total": int(permit_platform_summary.get("platform_industry_total", 0) or 0),
        "permit_platform_focus_registry_row_total": int(
            permit_platform_summary.get("platform_focus_registry_row_total", 0) or 0
        ),
        "permit_platform_promoted_selector_total": int(
            permit_platform_summary.get("platform_promoted_selector_total", 0) or 0
        ),
        "permit_platform_absorbed_focus_total": int(
            permit_platform_summary.get("platform_absorbed_focus_total", 0) or 0
        ),
        "permit_platform_real_with_selector_alias_total": int(
            permit_platform_summary.get("platform_real_with_selector_alias_total", 0) or 0
        ),
        "permit_master_industry_total": int(permit_master_summary.get("master_industry_total", 0) or 0),
        "permit_master_focus_registry_row_total": int(
            permit_master_summary.get("master_focus_registry_row_total", 0) or 0
        ),
        "permit_master_promoted_row_total": int(permit_master_summary.get("master_promoted_row_total", 0) or 0),
        "permit_master_absorbed_row_total": int(permit_master_summary.get("master_absorbed_row_total", 0) or 0),
        "permit_master_real_with_alias_total": int(permit_master_summary.get("master_real_with_alias_total", 0) or 0),
        "permit_master_canonicalized_promoted_total": int(
            permit_master_summary.get("master_canonicalized_promoted_total", 0) or 0
        ),
        "permit_candidate_pack_total": int(
            permit_provenance_summary.get("candidate_pack_total", 0) or 0
        ),
        "permit_inferred_reverification_total": int(
            permit_provenance_summary.get("master_inferred_overlay_total", 0) or 0
        ),
        "permit_raw_source_proof_row_total": int(
            permit_provenance_summary.get("rows_with_raw_source_proof_total", 0) or 0
        ),
        "permit_focus_family_registry_with_raw_source_proof_total": int(
            permit_provenance_summary.get("focus_family_registry_with_raw_source_proof_total", 0) or 0
        ),
        "permit_focus_family_registry_missing_raw_source_proof_total": int(
            permit_provenance_summary.get("focus_family_registry_missing_raw_source_proof_total", 0) or 0
        ),
        "permit_raw_source_proof_family_total": int(
            permit_patent_summary.get("raw_source_proof_family_total", 0) or 0
        ),
        "permit_claim_packet_family_total": int(
            permit_patent_summary.get("claim_packet_family_total", 0) or 0
        ),
        "permit_claim_packet_complete_family_total": int(
            permit_patent_summary.get("claim_packet_complete_family_total", 0) or 0
        ),
        "permit_checksum_sample_family_total": int(
            permit_patent_summary.get("checksum_sample_family_total", 0) or 0
        ),
        "permit_checksum_sample_total": len(permit_checksum_samples),
        "permit_family_case_goldset_family_total": int(
            permit_family_case_goldset_summary.get("goldset_complete_family_total", 0) or 0
        ),
        "permit_family_case_total": int(permit_family_case_goldset_summary.get("case_total", 0) or 0),
        "permit_family_case_sample_total": len(permit_family_case_samples),
        "permit_edge_case_total": int(permit_family_case_goldset_summary.get("edge_case_total", 0) or 0),
        "permit_edge_case_family_total": int(permit_family_case_goldset_summary.get("edge_case_family_total", 0) or 0),
        "permit_manual_review_case_total": int(permit_family_case_goldset_summary.get("manual_review_case_total", 0) or 0),
        "permit_widget_case_parity_family_total": permit_case_parity_family_total,
        "permit_case_story_family_total": int(
            permit_case_story_surface_summary.get("story_family_total", 0) or 0
        ),
        "permit_case_story_review_reason_total": int(
            permit_case_story_surface_summary.get("review_reason_total", 0) or 0
        ),
        "permit_case_story_manual_review_family_total": int(
            permit_case_story_surface_summary.get("manual_review_family_total", 0) or 0
        ),
        "permit_case_story_sample_total": len(permit_case_story_samples),
        "permit_case_story_surface_ready": bool(
            permit_case_story_surface_summary.get("story_ready", False)
        ),
        "permit_operator_demo_family_total": int(
            permit_operator_demo_summary.get("family_total", 0) or 0
        ),
        "permit_operator_demo_case_total": int(
            permit_operator_demo_summary.get("demo_case_total", 0) or 0
        ),
        "permit_operator_demo_manual_review_total": int(
            permit_operator_demo_summary.get("manual_review_demo_total", 0) or 0
        ),
        "permit_partner_demo_sample_total": len(permit_partner_demo_samples),
        "permit_partner_demo_surface_ready": bool(
            permit_operator_demo_summary.get("operator_demo_ready", False)
        ) and bool(permit_partner_demo_samples),
        "yangdo_recommendation_precision_scenario_count": int(
            yangdo_precision_summary.get("scenario_count", 0) or 0
        ),
        "yangdo_recommendation_precision_ok": bool(yangdo_precision_summary.get("precision_ok", False)),
        "yangdo_recommendation_high_precision_ok": bool(
            yangdo_precision_summary.get("high_precision_ok", False)
        ),
        "yangdo_recommendation_summary_publication_ok": bool(
            yangdo_precision_summary.get("summary_publication_ok", False)
        ),
        "yangdo_recommendation_detail_explainability_ok": bool(
            yangdo_precision_summary.get("detail_explainability_ok", False)
        ),
        "yangdo_recommendation_contract_ok": bool(yangdo_contract_summary.get("contract_ok", False)),
        "yangdo_recommendation_bridge_policy": "kr_service_to_listing_or_consult",
    }

    packaging = {
        "public_platform": {
            "host": summary["public_platform_host"],
            "role": "brand_platform_and_service_entry",
            "calculator_policy": "cta_only_on_home_lazy_gate_on_service_pages",
        },
        "listing_market": {
            "host": summary["listing_market_host"],
            "role": "listing_market_site_only",
            "runtime_policy": "no_public_calculator_runtime",
        },
        "internal_unlimited": {
            "tenants": internal_tenants,
            "policy": "SeoulMNA internal tenants stay unlimited and are excluded from partner token caps.",
        },
        "partner_rental": {
            "widget_standard": [row["offering_id"] for row in standard_rows],
            "api_or_detail_pro": [row["offering_id"] for row in pro_rows],
            "yangdo_recommendation": {
                "enabled_offerings": [row["offering_id"] for row in recommendation_rows],
                "summary_offerings": [row["offering_id"] for row in recommendation_standard_rows],
                "detail_offerings": [row["offering_id"] for row in recommendation_detail_rows],
                "internal_offerings": [row["offering_id"] for row in recommendation_internal_rows],
                "package_matrix": {
                    "summary_only": {
                        "offering_ids": [],
                        "policy": "Reserved for a future minimal recommendation SKU without listing bridge CTA.",
                    },
                    "summary_market_bridge": {
                        "offering_ids": [row["offering_id"] for row in recommendation_summary_bridge_rows],
                        "policy": "Public-safe recommendation summary with a direct market bridge CTA.",
                    },
                    "detail_explainable": {
                        "offering_ids": [row["offering_id"] for row in recommendation_detail_explainable_rows],
                        "policy": "Explainable recommendation detail without consult-assisted workflow.",
                    },
                    "consult_assist": {
                        "offering_ids": [row["offering_id"] for row in recommendation_consult_assist_rows],
                        "policy": "Explainable recommendation detail plus consult follow-up lane.",
                    },
                    "internal_full": {
                        "offering_ids": [row["offering_id"] for row in recommendation_internal_rows],
                        "policy": "Internal QA lane with raw recommendation diagnostics.",
                    },
                },
                "lane_positioning": _recommendation_lane_positioning(),
                "precision_matrix_path": str((yangdo_precision_path or Path()).resolve()) if yangdo_precision_path else "",
                "contract_audit_path": str((yangdo_contract_path or Path()).resolve()) if yangdo_contract_path else "",
                "precision_scenario_count": summary["yangdo_recommendation_precision_scenario_count"],
                "precision_ok": summary["yangdo_recommendation_precision_ok"],
                "high_precision_ok": summary["yangdo_recommendation_high_precision_ok"],
                "summary_publication_ok": summary["yangdo_recommendation_summary_publication_ok"],
                "detail_explainability_ok": summary["yangdo_recommendation_detail_explainability_ok"],
                "contract_ok": summary["yangdo_recommendation_contract_ok"],
                "summary_policy": "Expose recommendation_label, recommendation_focus, reasons, and display range only.",
                "detail_policy": "Expose precision_tier, fit_summary, matched_axes, and mismatch_flags while keeping raw score internal.",
                "internal_policy": "Internal tenants may inspect raw recommendation_score and similarity for QA and tuning.",
                "public_story": "공개 화면은 가격 범위, 추천 라벨, 추천 이유만 노출합니다.",
                "detail_story": "상담형 상세는 추천 정밀도, 일치축, 비일치축, 주의 신호를 설명합니다.",
                "operator_story": "운영 검수는 중복 매물 보정과 내부 추천 점수를 별도로 검토합니다.",
                "bridge_story": ".kr 서비스 페이지에서 추천을 해석하고 실제 매물 확인은 .co.kr 또는 상담형 상세로 분기합니다.",
                "service_primary_cta": "추천 매물 흐름 보기",
                "service_secondary_cta": "상담형 상세 요청",
                "service_flow_policy": "public_summary_then_market_or_consult",
                "listing_runtime_policy": "never_embed_tools_on_listing_domain",
                "supported_precision_labels": ["우선 추천", "조건 유사", "보조 검토"],
            },
            "permit_precheck": {
                "enabled_offerings": [row["offering_id"] for row in permit_rows],
                "summary_offerings": [row["offering_id"] for row in permit_standard_rows],
                "detail_offerings": [row["offering_id"] for row in permit_detail_rows],
                "assist_offerings": [row["offering_id"] for row in permit_assist_rows],
                "internal_offerings": [row["offering_id"] for row in permit_internal_rows],
                "package_matrix": {
                    "summary_self_check": {
                        "offering_ids": [row["offering_id"] for row in permit_standard_rows],
                        "policy": "Public-safe self-check summary with a lazy gate and checklist CTA.",
                    },
                    "detail_checklist": {
                        "offering_ids": [row["offering_id"] for row in permit_detail_rows],
                        "policy": "Criterion-by-criterion checklist output without manual follow-up.",
                    },
                    "manual_review_assist": {
                        "offering_ids": [row["offering_id"] for row in permit_assist_rows],
                        "policy": "Checklist output plus manual-review or consultant follow-up lane.",
                    },
                    "internal_full": {
                        "offering_ids": [row["offering_id"] for row in permit_internal_rows],
                        "policy": "Internal QA lane with raw registry mapping and pending-criteria context.",
                    },
                },
                "lane_positioning": _permit_lane_positioning(),
                "summary_policy": "Expose pass/fail summary, shortfall labels, and next-step CTA only.",
                "detail_policy": "Expose criterion results, evidence checklist, and next actions without raw mapping internals.",
                "assist_policy": "Expose detail checklist plus manual-review assist CTA and consult handoff lane.",
                "internal_policy": "Internal tenants may inspect pending criteria, mapping confidence, and QA-only diagnostics.",
                "public_story": "Start with a fast registration-basis self-check, then move to detail only when needed.",
                "detail_story": "Show criterion-by-criterion checklist output before escalating into manual review.",
                "assist_story": "Use manual-review assist when the basis is ambiguous or additional criteria require operator judgment.",
                "listing_runtime_policy": "never_embed_tools_on_listing_domain",
                "service_primary_cta": "사전검토 시작",
                "service_secondary_cta": "수동 검토 요청",
                "service_flow_policy": "public_summary_then_checklist_or_manual_review",
            },
            "permit_widget_feeds": {
                "selector_feed_path": str((permit_selector_path or Path()).resolve()) if permit_selector_path else "",
                "platform_feed_path": str((permit_platform_path or Path()).resolve()) if permit_platform_path else "",
                "master_feed_path": str((permit_master_path or Path()).resolve()) if permit_master_path else "",
                "provenance_audit_path": str((permit_provenance_path or Path()).resolve()) if permit_provenance_path else "",
                "patent_evidence_bundle_path": str((permit_patent_path or Path()).resolve()) if permit_patent_path else "",
                "family_case_goldset_path": (
                    str((permit_family_case_goldset_path or Path()).resolve()) if permit_family_case_goldset_path else ""
                ),
                "case_story_surface_path": (
                    str((permit_case_story_surface_path or Path()).resolve()) if permit_case_story_surface_path else ""
                ),
                "selector_entry_total": summary["permit_selector_entry_total"],
                "platform_industry_total": summary["permit_platform_industry_total"],
                "platform_focus_registry_row_total": summary["permit_platform_focus_registry_row_total"],
                "platform_promoted_selector_total": summary["permit_platform_promoted_selector_total"],
                "platform_absorbed_focus_total": summary["permit_platform_absorbed_focus_total"],
                "platform_real_with_selector_alias_total": summary["permit_platform_real_with_selector_alias_total"],
                "master_industry_total": summary["permit_master_industry_total"],
                "master_focus_registry_row_total": summary["permit_master_focus_registry_row_total"],
                "master_promoted_row_total": summary["permit_master_promoted_row_total"],
                "master_absorbed_row_total": summary["permit_master_absorbed_row_total"],
                "master_real_with_alias_total": summary["permit_master_real_with_alias_total"],
                "master_canonicalized_promoted_total": summary["permit_master_canonicalized_promoted_total"],
                "candidate_pack_total": summary["permit_candidate_pack_total"],
                "inferred_reverification_total": summary["permit_inferred_reverification_total"],
                "raw_source_proof_row_total": summary["permit_raw_source_proof_row_total"],
                "focus_family_registry_with_raw_source_proof_total": summary["permit_focus_family_registry_with_raw_source_proof_total"],
                "focus_family_registry_missing_raw_source_proof_total": summary["permit_focus_family_registry_missing_raw_source_proof_total"],
                "raw_source_proof_family_total": summary["permit_raw_source_proof_family_total"],
                "claim_packet_family_total": summary["permit_claim_packet_family_total"],
                "claim_packet_complete_family_total": summary["permit_claim_packet_complete_family_total"],
                "checksum_sample_family_total": summary["permit_checksum_sample_family_total"],
                "checksum_sample_total": summary["permit_checksum_sample_total"],
                "family_case_goldset_family_total": summary["permit_family_case_goldset_family_total"],
                "family_case_total": summary["permit_family_case_total"],
                "family_case_sample_total": summary["permit_family_case_sample_total"],
                "edge_case_total": summary["permit_edge_case_total"],
                "edge_case_family_total": summary["permit_edge_case_family_total"],
                "manual_review_case_total": summary["permit_manual_review_case_total"],
                "widget_case_parity_family_total": summary["permit_widget_case_parity_family_total"],
                "case_story_family_total": summary["permit_case_story_family_total"],
                "case_story_review_reason_total": summary["permit_case_story_review_reason_total"],
                "case_story_manual_review_family_total": summary["permit_case_story_manual_review_family_total"],
                "case_story_sample_total": summary["permit_case_story_sample_total"],
                "case_story_surface_ready": summary["permit_case_story_surface_ready"],
                "operator_demo_family_total": summary["permit_operator_demo_family_total"],
                "operator_demo_case_total": summary["permit_operator_demo_case_total"],
                "operator_demo_manual_review_total": summary["permit_operator_demo_manual_review_total"],
                "partner_demo_sample_total": summary["permit_partner_demo_sample_total"],
                "partner_demo_surface_ready": summary["permit_partner_demo_surface_ready"],
                "proof_checksum_samples": permit_checksum_samples,
                "family_case_sample_fields": [
                    "family_key",
                    "claim_id",
                    "case_id",
                    "case_kind",
                    "service_code",
                    "expected_status",
                    "proof_coverage_ratio",
                    "review_reason",
                    "manual_review_expected",
                ],
                "family_case_samples": permit_family_case_samples,
                "case_story_sample_fields": [
                    "family_key",
                    "claim_id",
                    "preset_total",
                    "manual_review_preset_total",
                    "review_reasons",
                    "representative_preset_ids",
                    "operator_story_points",
                ],
                "case_story_samples": permit_case_story_samples,
                "partner_demo_fields": [
                    "family_key",
                    "claim_id",
                    "claim_title",
                    "proof_coverage_ratio",
                    "demo_case_total",
                    "manual_review_demo_total",
                    "review_reasons",
                    "representative_services",
                    "representative_statuses",
                ],
                "partner_demo_samples": permit_partner_demo_samples,
                "recommended_primary_feed": "master_catalog",
                "recommended_overlay_feed": "selector_catalog",
            },
            "recommended_pricing_note": "Expose standard as widget-summary plans and pro as detail/API plans; keep internal pro_internal unlimited for SeoulMNA only.",
        },
    }

    commercialization_notes = [
        "Do not rent the listing domain as a calculator runtime. Keep partner/public calculators mounted behind seoulmna.kr-facing contracts or partner widget hosts.",
        "Use standard plans for iframe/widget summary responses and pro plans for API/detail responses with CRM/webhook integration.",
        "Yangdo rental is no longer price-range only. Standard includes safe recommendation summaries and Pro includes explainable recommendation context.",
        "Recommendation rental exposure is backed by the precision matrix and contract audit, so public summary/detail/internal boundaries stay testable.",
        "Keep SeoulMNA internal tenants on pro_internal so seoulmna.co.kr can consume unlimited internal widgets without partner throttling.",
        "Use the same A/B engine split in commercial packaging: yangdo-only, permit-only, combo.",
        "For permit widgets, use master_catalog as the primary industry feed and selector_catalog as the overlay feed for stable quick-select aliases.",
        "Permit rental should ladder from summary_self_check to detail_checklist to manual_review_assist instead of collapsing every pro plan into one lane.",
        "Master catalog is now backed by direct focus-registry rows; keep the provenance audit attached until candidate-pack and inferred rows are materially reduced.",
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_paths": {
            "registry": str(registry_path.resolve()),
            "thresholds": str(thresholds_path.resolve()),
            "operations_packet": str((operations_path or Path()).resolve()) if operations_path else "",
            "permit_selector_catalog": str((permit_selector_path or Path()).resolve()) if permit_selector_path else "",
            "permit_platform_catalog": str((permit_platform_path or Path()).resolve()) if permit_platform_path else "",
            "permit_master_catalog": str((permit_master_path or Path()).resolve()) if permit_master_path else "",
            "permit_provenance_audit": str((permit_provenance_path or Path()).resolve()) if permit_provenance_path else "",
            "permit_patent_evidence_bundle": str((permit_patent_path or Path()).resolve()) if permit_patent_path else "",
            "permit_family_case_goldset": (
                str((permit_family_case_goldset_path or Path()).resolve()) if permit_family_case_goldset_path else ""
            ),
            "yangdo_recommendation_precision_matrix": str((yangdo_precision_path or Path()).resolve()) if yangdo_precision_path else "",
            "yangdo_recommendation_contract_audit": str((yangdo_contract_path or Path()).resolve()) if yangdo_contract_path else "",
        },
        "summary": summary,
        "packaging": packaging,
        "offerings": offering_rows,
        "commercialization_notes": commercialization_notes,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    packaging = payload.get("packaging") if isinstance(payload.get("packaging"), dict) else {}
    lines = [
        "# Widget Rental Catalog",
        "",
        "## Summary",
        f"- public_platform_host: {summary.get('public_platform_host')}",
        f"- listing_market_host: {summary.get('listing_market_host')}",
        f"- public_mount_host: {summary.get('public_mount_host')}",
        f"- offering_count: {summary.get('offering_count')}",
        f"- standard_offering_count: {summary.get('standard_offering_count')}",
        f"- pro_offering_count: {summary.get('pro_offering_count')}",
        f"- combo_offering_count: {summary.get('combo_offering_count')}",
        f"- yangdo_recommendation_offering_count: {summary.get('yangdo_recommendation_offering_count')}",
        f"- yangdo_recommendation_standard_count: {summary.get('yangdo_recommendation_standard_count')}",
        f"- yangdo_recommendation_detail_count: {summary.get('yangdo_recommendation_detail_count')}",
        f"- yangdo_recommendation_summary_bridge_count: {summary.get('yangdo_recommendation_summary_bridge_count')}",
        f"- yangdo_recommendation_detail_lane_count: {summary.get('yangdo_recommendation_detail_lane_count')}",
        f"- yangdo_recommendation_consult_assist_count: {summary.get('yangdo_recommendation_consult_assist_count')}",
        f"- yangdo_recommendation_precision_scenario_count: {summary.get('yangdo_recommendation_precision_scenario_count')}",
        f"- yangdo_recommendation_precision_ok: {summary.get('yangdo_recommendation_precision_ok')}",
        f"- yangdo_recommendation_contract_ok: {summary.get('yangdo_recommendation_contract_ok')}",
        f"- internal_tenant_count: {summary.get('internal_tenant_count')}",
        f"- permit_selector_entry_total: {summary.get('permit_selector_entry_total')}",
        f"- permit_platform_industry_total: {summary.get('permit_platform_industry_total')}",
        f"- permit_platform_promoted_selector_total: {summary.get('permit_platform_promoted_selector_total')}",
        f"- permit_platform_absorbed_focus_total: {summary.get('permit_platform_absorbed_focus_total')}",
        f"- permit_master_industry_total: {summary.get('permit_master_industry_total')}",
        f"- permit_master_promoted_row_total: {summary.get('permit_master_promoted_row_total')}",
        f"- permit_master_absorbed_row_total: {summary.get('permit_master_absorbed_row_total')}",
        f"- permit_master_canonicalized_promoted_total: {summary.get('permit_master_canonicalized_promoted_total')}",
        f"- permit_candidate_pack_total: {summary.get('permit_candidate_pack_total')}",
        f"- permit_inferred_reverification_total: {summary.get('permit_inferred_reverification_total')}",
        f"- permit_raw_source_proof_row_total: {summary.get('permit_raw_source_proof_row_total')}",
        f"- permit_focus_family_registry_with_raw_source_proof_total: {summary.get('permit_focus_family_registry_with_raw_source_proof_total')}",
        f"- permit_focus_family_registry_missing_raw_source_proof_total: {summary.get('permit_focus_family_registry_missing_raw_source_proof_total')}",
        f"- permit_raw_source_proof_family_total: {summary.get('permit_raw_source_proof_family_total')}",
        f"- permit_claim_packet_family_total: {summary.get('permit_claim_packet_family_total')}",
        f"- permit_claim_packet_complete_family_total: {summary.get('permit_claim_packet_complete_family_total')}",
        f"- permit_checksum_sample_family_total: {summary.get('permit_checksum_sample_family_total')}",
        f"- permit_checksum_sample_total: {summary.get('permit_checksum_sample_total')}",
        f"- permit_family_case_goldset_family_total: {summary.get('permit_family_case_goldset_family_total')}",
        f"- permit_family_case_total: {summary.get('permit_family_case_total')}",
        f"- permit_family_case_sample_total: {summary.get('permit_family_case_sample_total')}",
        f"- permit_edge_case_total: {summary.get('permit_edge_case_total')}",
        f"- permit_edge_case_family_total: {summary.get('permit_edge_case_family_total')}",
        f"- permit_manual_review_case_total: {summary.get('permit_manual_review_case_total')}",
        f"- permit_case_story_family_total: {summary.get('permit_case_story_family_total')}",
        f"- permit_case_story_review_reason_total: {summary.get('permit_case_story_review_reason_total')}",
        f"- permit_case_story_manual_review_family_total: {summary.get('permit_case_story_manual_review_family_total')}",
        f"- permit_case_story_sample_total: {summary.get('permit_case_story_sample_total')}",
        f"- permit_case_story_surface_ready: {summary.get('permit_case_story_surface_ready')}",
        f"- permit_operator_demo_family_total: {summary.get('permit_operator_demo_family_total')}",
        f"- permit_operator_demo_case_total: {summary.get('permit_operator_demo_case_total')}",
        f"- permit_operator_demo_manual_review_total: {summary.get('permit_operator_demo_manual_review_total')}",
        f"- permit_partner_demo_sample_total: {summary.get('permit_partner_demo_sample_total')}",
        f"- permit_partner_demo_surface_ready: {summary.get('permit_partner_demo_surface_ready')}",
        f"- permit_widget_case_parity_family_total: {summary.get('permit_widget_case_parity_family_total')}",
        "",
        "## Packaging",
        f"- public_platform: {(packaging.get('public_platform') or {}).get('calculator_policy')}",
        f"- listing_market: {(packaging.get('listing_market') or {}).get('runtime_policy')}",
        f"- widget_standard: {', '.join((packaging.get('partner_rental') or {}).get('widget_standard') or []) or '(none)'}",
        f"- api_or_detail_pro: {', '.join((packaging.get('partner_rental') or {}).get('api_or_detail_pro') or []) or '(none)'}",
        f"- yangdo_recommendation_summary: {', '.join((((packaging.get('partner_rental') or {}).get('yangdo_recommendation') or {}).get('summary_offerings') or [])) or '(none)'}",
        f"- yangdo_recommendation_detail: {', '.join((((packaging.get('partner_rental') or {}).get('yangdo_recommendation') or {}).get('detail_offerings') or [])) or '(none)'}",
        f"- yangdo_recommendation_summary_market_bridge: {', '.join((((((packaging.get('partner_rental') or {}).get('yangdo_recommendation') or {}).get('package_matrix') or {}).get('summary_market_bridge') or {}).get('offering_ids') or [])) or '(none)'}",
        f"- yangdo_recommendation_consult_assist: {', '.join((((((packaging.get('partner_rental') or {}).get('yangdo_recommendation') or {}).get('package_matrix') or {}).get('consult_assist') or {}).get('offering_ids') or [])) or '(none)'}",
        f"- yangdo_recommendation_public_story: {(((packaging.get('partner_rental') or {}).get('yangdo_recommendation') or {}).get('public_story'))}",
        f"- yangdo_recommendation_detail_story: {(((packaging.get('partner_rental') or {}).get('yangdo_recommendation') or {}).get('detail_story'))}",
        f"- permit_widget_primary_feed: {((packaging.get('partner_rental') or {}).get('permit_widget_feeds') or {}).get('recommended_primary_feed')}",
        f"- permit_widget_case_parity_family_total: {((packaging.get('partner_rental') or {}).get('permit_widget_feeds') or {}).get('widget_case_parity_family_total')}",
        f"- permit_summary_self_check: {', '.join((((((packaging.get('partner_rental') or {}).get('permit_precheck') or {}).get('package_matrix') or {}).get('summary_self_check') or {}).get('offering_ids') or [])) or '(none)'}",
        f"- permit_detail_checklist: {', '.join((((((packaging.get('partner_rental') or {}).get('permit_precheck') or {}).get('package_matrix') or {}).get('detail_checklist') or {}).get('offering_ids') or [])) or '(none)'}",
        f"- permit_manual_review_assist: {', '.join((((((packaging.get('partner_rental') or {}).get('permit_precheck') or {}).get('package_matrix') or {}).get('manual_review_assist') or {}).get('offering_ids') or [])) or '(none)'}",
        "",
        "## Offerings",
    ]
    for row in payload.get("offerings") or []:
        if not isinstance(row, dict):
            continue
        limits = row.get("limits") if isinstance(row.get("limits"), dict) else {}
        lines.append(
            f"- {row.get('offering_id')} ({row.get('plan')} / {row.get('response_tier')}): "
            f"systems={', '.join(row.get('systems') or []) or '(none)'} "
            f"delivery={', '.join(row.get('delivery_modes') or []) or '(none)'} "
            f"effective_limit={limits.get('effective_limit')} "
            f"recommendation={row.get('recommendation_visibility')} "
            f"lane={row.get('recommendation_package_lane')}"
        )
    lines.append("")
    lines.append("## Notes")
    for item in payload.get("commercialization_notes") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the SeoulMNA widget rental catalog")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--permit-selector", type=Path, default=DEFAULT_PERMIT_SELECTOR)
    parser.add_argument("--permit-platform", type=Path, default=DEFAULT_PERMIT_PLATFORM)
    parser.add_argument("--permit-master", type=Path, default=DEFAULT_PERMIT_MASTER)
    parser.add_argument("--permit-provenance", type=Path, default=DEFAULT_PERMIT_PROVENANCE)
    parser.add_argument("--permit-patent", type=Path, default=DEFAULT_PERMIT_PATENT)
    parser.add_argument("--permit-family-case-goldset", type=Path, default=DEFAULT_PERMIT_FAMILY_CASE_GOLDSET)
    parser.add_argument("--permit-case-story-surface", type=Path, default=DEFAULT_PERMIT_CASE_STORY_SURFACE)
    parser.add_argument("--permit-operator-demo-packet", type=Path, default=DEFAULT_PERMIT_OPERATOR_DEMO_PACKET)
    parser.add_argument("--yangdo-precision", type=Path, default=DEFAULT_YANGDO_PRECISION)
    parser.add_argument("--yangdo-contract", type=Path, default=DEFAULT_YANGDO_CONTRACT)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "widget_rental_catalog_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "widget_rental_catalog_latest.md")
    args = parser.parse_args()

    payload = build_widget_rental_catalog(
        registry_path=args.registry,
        thresholds_path=args.thresholds,
        operations_path=args.operations,
        permit_selector_path=args.permit_selector,
        permit_platform_path=args.permit_platform,
        permit_master_path=args.permit_master,
        permit_provenance_path=args.permit_provenance,
        permit_patent_path=args.permit_patent,
        permit_family_case_goldset_path=args.permit_family_case_goldset,
        permit_case_story_surface_path=args.permit_case_story_surface,
        permit_operator_demo_packet_path=args.permit_operator_demo_packet,
        yangdo_precision_path=args.yangdo_precision,
        yangdo_contract_path=args.yangdo_contract,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
