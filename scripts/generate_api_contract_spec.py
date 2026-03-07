#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_tenant_onboarding import _load_json


DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_THRESHOLDS = ROOT / "tenant_config" / "plan_thresholds.json"
DEFAULT_PERMIT_SELECTOR = ROOT / "logs" / "permit_selector_catalog_latest.json"
DEFAULT_PERMIT_PLATFORM = ROOT / "logs" / "permit_platform_catalog_latest.json"
DEFAULT_PERMIT_MASTER = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_PERMIT_PROVENANCE = ROOT / "logs" / "permit_provenance_audit_latest.json"
DEFAULT_PERMIT_PATENT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_OUTPUT = ROOT / "logs" / "api_contract_spec_latest.json"


YANGDO_SUMMARY_FIELDS = [
    "ok",
    "generated_at",
    "estimate_center_eok",
    "estimate_low_eok",
    "estimate_high_eok",
    "confidence_score",
    "confidence_percent",
    "publication_mode",
    "publication_label",
    "publication_reason",
    "price_source_tier",
    "price_source_label",
    "price_sample_count",
    "price_is_estimate",
    "price_range_kind",
    "price_source_channel",
    "price_disclaimer",
    "response_policy",
]

YANGDO_DETAIL_EXTRA_FIELDS = [
    "avg_similarity",
    "neighbor_count",
    "raw_neighbor_count",
    "effective_cluster_count",
    "display_neighbor_count",
    "hot_match_count",
    "duplicate_cluster_adjusted",
    "balance_excluded",
    "relaxed_fallback_used",
    "risk_notes",
    "previous_estimate_eok",
    "yoy_change_pct",
    "yoy_basis",
    "current_year",
    "previous_year",
]

YANGDO_INTERNAL_ONLY_FIELDS = [
    "neighbors",
    "tenant_id",
]

PERMIT_SUMMARY_FIELDS = [
    "ok",
    "service_code",
    "industry_name",
    "overall_status",
    "overall_ok",
    "manual_review_required",
    "coverage_status",
    "required_summary",
    "typed_overall_status",
    "typed_criteria_total",
    "pending_criteria_count",
    "blocking_failure_count",
    "unknown_blocking_count",
    "capital_input_suspicious",
    "next_actions",
    "response_policy",
]

PERMIT_DETAIL_EXTRA_FIELDS = [
    "group_rule_id",
    "mapping_confidence",
    "criterion_results",
    "evidence_checklist",
    "document_templates",
    "legal_basis",
]

PERMIT_INTERNAL_ONLY_FIELDS = [
    "pending_criteria_lines",
    "tenant_id",
]


def _permit_family_checksum_samples(permit_patent_evidence_bundle: dict | None, limit: int = 6) -> list[dict]:
    if not isinstance(permit_patent_evidence_bundle, dict):
        return []
    rows = [row for row in list(permit_patent_evidence_bundle.get("families") or []) if isinstance(row, dict)]
    samples: list[dict] = []
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


def build_contract_spec(
    registry: dict,
    thresholds: dict,
    permit_selector_catalog: dict | None = None,
    permit_platform_catalog: dict | None = None,
    permit_master_catalog: dict | None = None,
    permit_provenance_audit: dict | None = None,
    permit_patent_evidence_bundle: dict | None = None,
) -> dict:
    plan_defaults = registry.get("plan_feature_defaults") if isinstance(registry, dict) else {}
    offering_templates = registry.get("offering_templates") if isinstance(registry, dict) else []
    plans = thresholds.get("plans") if isinstance(thresholds, dict) else {}
    permit_selector_summary = (
        permit_selector_catalog.get("summary")
        if isinstance(permit_selector_catalog, dict) and isinstance(permit_selector_catalog.get("summary"), dict)
        else {}
    )
    permit_platform_summary = (
        permit_platform_catalog.get("summary")
        if isinstance(permit_platform_catalog, dict) and isinstance(permit_platform_catalog.get("summary"), dict)
        else {}
    )
    permit_master_summary = (
        permit_master_catalog.get("summary")
        if isinstance(permit_master_catalog, dict) and isinstance(permit_master_catalog.get("summary"), dict)
        else {}
    )
    permit_provenance_summary = (
        permit_provenance_audit.get("summary")
        if isinstance(permit_provenance_audit, dict) and isinstance(permit_provenance_audit.get("summary"), dict)
        else {}
    )
    permit_patent_summary = (
        permit_patent_evidence_bundle.get("summary")
        if isinstance(permit_patent_evidence_bundle, dict) and isinstance(permit_patent_evidence_bundle.get("summary"), dict)
        else {}
    )
    permit_checksum_samples = _permit_family_checksum_samples(permit_patent_evidence_bundle)

    spec = {
        "api_version": "v1",
        "system_topology": {
            "independent_systems": [
                {
                    "system_id": "yangdo",
                    "purpose": "건설업 면허 양도가 산정 및 양도양수 상담 유입",
                    "patent_track": "A",
                    "required_feature": "estimate",
                    "required_system": "yangdo",
                },
                {
                    "system_id": "permit",
                    "purpose": "등록기준 기반 인허가 사전검토",
                    "patent_track": "B",
                    "required_feature": "permit_precheck",
                    "required_system": "permit",
                },
            ],
            "shared_platform_components": [
                "tenant_gateway",
                "channel_router",
                "response_envelope",
                "usage_billing",
                "partner_activation_gate",
            ],
        },
        "common_request_wrapper": {
            "wrappers": ["request", "selector", "inputs"],
            "request_fields": ["channel_id", "tenant_id", "requested_at", "page_url", "source", "request_id"],
        },
        "common_response_envelope": {
            "top_level_required": ["ok", "service", "api_version", "request_id", "response_meta", "data"],
            "response_meta_fields": ["service", "api_version", "request_id", "channel_id", "tenant_plan", "response_tier", "status"],
            "usage_headers": [
                "X-Usage-Month",
                "X-Usage-Events-Month",
                "X-Usage-Ok-Events-Month",
                "X-Usage-Error-Events-Month",
                "X-Usage-Events-Limit",
                "X-Usage-Events-Remaining",
            ],
        },
        "partner_activation": {
            "required_inputs": ["tenant_id", "proof_url", "approved_source", "api_key"],
            "defaults": {
                "smoke_base_url": "channel.engine_origin",
                "smoke_origin": "channel.branding.site_url",
                "smoke_host": "channel.channel_hosts[0]",
                "skip_smoke": False,
            },
            "validation_flow": [
                "validate_tenant_onboarding",
                "activate_partner_tenant dry-run",
                "activate_partner_tenant apply",
                "run_partner_api_smoke",
            ],
            "post_apply_checks": [
                "health endpoint responds",
                "response_meta present",
                "request_id round trip",
                "channel_id matches partner channel",
                "response tier header present",
            ],
        },
        "services": {
            "yangdo": {
                "endpoint": "/v1/yangdo/estimate",
                "request_contract": {
                    "wrappers": ["request", "selector", "inputs"],
                    "request_fields": ["channel_id", "tenant_id", "requested_at", "page_url", "source", "request_id"],
                    "selector_fields": ["license_text", "license", "service_code"],
                    "input_examples": ["capital_eok", "sales3_eok", "specialty", "license_year", "ok_capital", "ok_engineer", "ok_office"],
                },
                "response_contract": {
                    "top_level_required": ["ok", "service", "api_version", "request_id", "response_meta", "data"],
                    "response_meta_fields": ["service", "api_version", "request_id", "channel_id", "tenant_plan", "response_tier", "status"],
                    "headers": [
                        "X-Api-Version",
                        "X-Service-Name",
                        "X-Request-Id",
                        "X-Channel-Id",
                        "X-Tenant-Plan",
                        "X-Response-Tier",
                        "X-Usage-Month",
                        "X-Usage-Events-Month",
                        "X-Usage-Ok-Events-Month",
                        "X-Usage-Error-Events-Month",
                        "X-Usage-Events-Limit",
                        "X-Usage-Events-Remaining",
                    ],
                    "tier_fields": {
                        "summary": YANGDO_SUMMARY_FIELDS,
                        "detail_extra": YANGDO_DETAIL_EXTRA_FIELDS,
                        "internal_only": YANGDO_INTERNAL_ONLY_FIELDS,
                    },
                },
            },
            "permit": {
                "endpoint": "/v1/permit/precheck",
                "request_contract": {
                    "wrappers": ["request", "selector", "inputs"],
                    "request_fields": ["channel_id", "tenant_id", "requested_at", "page_url", "source", "request_id"],
                    "selector_fields": [
                        "service_code",
                        "selector_code",
                        "canonical_service_code",
                        "service_name",
                        "industry_name",
                        "rule_id",
                    ],
                    "input_examples": ["capital_eok", "technicians_count", "office_secured", "insurance_secured", "document_ready", "safety_secured"],
                },
                "response_contract": {
                    "top_level_required": ["ok", "service", "api_version", "request_id", "response_meta", "data"],
                    "response_meta_fields": ["service", "api_version", "request_id", "channel_id", "tenant_plan", "response_tier", "status"],
                    "headers": [
                        "X-Api-Version",
                        "X-Service-Name",
                        "X-Request-Id",
                        "X-Channel-Id",
                        "X-Tenant-Plan",
                        "X-Response-Tier",
                        "X-Usage-Month",
                        "X-Usage-Events-Month",
                        "X-Usage-Ok-Events-Month",
                        "X-Usage-Error-Events-Month",
                        "X-Usage-Events-Limit",
                        "X-Usage-Events-Remaining",
                    ],
                    "tier_fields": {
                        "summary": PERMIT_SUMMARY_FIELDS,
                        "detail_extra": PERMIT_DETAIL_EXTRA_FIELDS,
                        "internal_only": PERMIT_INTERNAL_ONLY_FIELDS,
                    },
                    "catalog_contracts": {
                        "master_catalog": {
                            "summary_fields": [
                                "master_industry_total",
                                "master_real_row_total",
                                "master_focus_registry_row_total",
                                "master_promoted_row_total",
                                "master_absorbed_row_total",
                                "master_real_with_alias_total",
                                "master_focus_row_total",
                                "master_inferred_overlay_total",
                                "master_selector_alias_total",
                                "rows_with_raw_source_proof_total",
                                "focus_family_registry_with_raw_source_proof_total",
                                "focus_family_registry_missing_raw_source_proof_total",
                                "raw_source_proof_family_total",
                                "claim_packet_family_total",
                                "claim_packet_complete_family_total",
                                "checksum_sample_family_total",
                                "checksum_sample_total",
                            ],
                            "row_fields": [
                                "service_code",
                                "canonical_service_code",
                                "service_name",
                                "major_code",
                                "major_name",
                                "platform_row_origin",
                                "platform_selector_aliases",
                                "platform_has_focus_alias",
                                "platform_has_inferred_alias",
                                "is_platform_row",
                                "law_title",
                                "legal_basis_title",
                                "raw_source_proof",
                            ],
                            "feed_contract_fields": [
                                "primary_feed_name",
                                "overlay_feed_name",
                                "primary_row_key",
                                "canonical_row_key",
                                "alias_list_field",
                                "focus_registry_row_key_policy",
                                "absorbed_row_key_policy",
                            ],
                            "current_summary": {
                                "master_industry_total": int(
                                    permit_master_summary.get("master_industry_total", 0) or 0
                                ),
                                "master_focus_registry_row_total": int(
                                    permit_master_summary.get("master_focus_registry_row_total", 0) or 0
                                ),
                                "master_promoted_row_total": int(
                                    permit_master_summary.get("master_promoted_row_total", 0) or 0
                                ),
                                "master_absorbed_row_total": int(
                                    permit_master_summary.get("master_absorbed_row_total", 0) or 0
                                ),
                                "master_real_with_alias_total": int(
                                    permit_master_summary.get("master_real_with_alias_total", 0) or 0
                                ),
                                "rows_with_raw_source_proof_total": int(
                                    permit_provenance_summary.get("rows_with_raw_source_proof_total", 0) or 0
                                ),
                                "focus_family_registry_with_raw_source_proof_total": int(
                                    permit_provenance_summary.get("focus_family_registry_with_raw_source_proof_total", 0) or 0
                                ),
                                "focus_family_registry_missing_raw_source_proof_total": int(
                                    permit_provenance_summary.get("focus_family_registry_missing_raw_source_proof_total", 0) or 0
                                ),
                                "raw_source_proof_family_total": int(
                                    permit_patent_summary.get("raw_source_proof_family_total", 0) or 0
                                ),
                                "claim_packet_family_total": int(
                                    permit_patent_summary.get("claim_packet_family_total", 0) or 0
                                ),
                                "claim_packet_complete_family_total": int(
                                    permit_patent_summary.get("claim_packet_complete_family_total", 0) or 0
                                ),
                                "checksum_sample_family_total": int(
                                    permit_patent_summary.get("checksum_sample_family_total", 0) or 0
                                ),
                                "checksum_sample_total": len(permit_checksum_samples),
                            },
                            "proof_surface_examples": {
                                "family_checksum_samples": permit_checksum_samples,
                                "claim_packet_fields": [
                                    "claim_id",
                                    "claim_statement",
                                    "covered_input_domains",
                                    "calculation_steps",
                                    "ui_surfaces",
                                    "source_proof_summary",
                                ],
                            },
                        },
                        "selector_catalog": {
                            "summary_fields": [
                                "selector_entry_total",
                                "selector_focus_total",
                                "selector_inferred_total",
                                "selector_real_entry_total",
                                "selector_rules_only_entry_total",
                            ],
                            "row_fields": [
                                "service_code",
                                "canonical_service_code",
                                "service_name",
                                "selector_kind",
                                "selector_category_code",
                                "selector_category_name",
                                "is_rules_only",
                                "law_title",
                                "legal_basis_title",
                                "quality_flags",
                            ],
                            "current_summary": {
                                "selector_entry_total": int(permit_selector_summary.get("selector_entry_total", 0) or 0),
                                "selector_focus_total": int(permit_selector_summary.get("selector_focus_total", 0) or 0),
                                "selector_inferred_total": int(permit_selector_summary.get("selector_inferred_total", 0) or 0),
                            },
                        },
                        "platform_catalog": {
                            "summary_fields": [
                                "platform_industry_total",
                                "platform_real_row_total",
                                "platform_focus_registry_row_total",
                                "platform_promoted_selector_total",
                                "platform_absorbed_focus_total",
                                "platform_real_with_selector_alias_total",
                                "platform_selector_alias_total",
                            ],
                            "row_fields": [
                                "service_code",
                                "canonical_service_code",
                                "service_name",
                                "major_code",
                                "major_name",
                                "platform_row_origin",
                                "platform_selector_aliases",
                                "platform_has_focus_alias",
                                "platform_has_inferred_alias",
                                "is_platform_row",
                                "law_title",
                                "legal_basis_title",
                            ],
                            "current_summary": {
                                "platform_industry_total": int(
                                    permit_platform_summary.get("platform_industry_total", 0) or 0
                                ),
                                "platform_focus_registry_row_total": int(
                                    permit_platform_summary.get("platform_focus_registry_row_total", 0) or 0
                                ),
                                "platform_promoted_selector_total": int(
                                    permit_platform_summary.get("platform_promoted_selector_total", 0) or 0
                                ),
                                "platform_absorbed_focus_total": int(
                                    permit_platform_summary.get("platform_absorbed_focus_total", 0) or 0
                                ),
                                "platform_real_with_selector_alias_total": int(
                                    permit_platform_summary.get("platform_real_with_selector_alias_total", 0) or 0
                                ),
                            },
                        },
                    },
                },
            },
        },
        "plans": [],
        "offering_templates": [],
    }

    if isinstance(plan_defaults, dict):
        for plan_name, features in plan_defaults.items():
            plan_key = str(plan_name or "").strip().lower()
            plan_policy = dict((plans.get(plan_key) or {})) if isinstance(plans, dict) else {}
            feature_set = sorted({str(x or "").strip().lower() for x in (features or []) if str(x or "").strip()})
            spec["plans"].append(
                {
                    "plan": plan_key,
                    "features": feature_set,
                    "max_usage_events": int(plan_policy.get("max_usage_events", 0) or 0),
                    "included_tokens": int(plan_policy.get("included_tokens", 0) or 0),
                    "response_tiers": {
                        "yangdo": "internal" if "estimate_internal" in feature_set else "detail" if "estimate_detail" in feature_set else "summary",
                        "permit": "internal" if "permit_precheck_internal" in feature_set else "detail" if "permit_precheck_detail" in feature_set else "summary",
                    },
                }
            )

    if isinstance(offering_templates, list):
        for row in offering_templates:
            if not isinstance(row, dict):
                continue
            spec["offering_templates"].append(
                {
                    "offering_id": str(row.get("offering_id") or "").strip(),
                    "display_name": str(row.get("display_name") or "").strip(),
                    "plan": str(row.get("plan") or "").strip().lower(),
                    "allowed_systems": sorted({str(x or "").strip().lower() for x in (row.get("allowed_systems") or []) if str(x or "").strip()}),
                    "allowed_features": sorted({str(x or "").strip().lower() for x in (row.get("allowed_features") or []) if str(x or "").strip()}),
                }
            )

    return spec


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate current API contract spec from code/config")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    parser.add_argument("--permit-selector", default=str(DEFAULT_PERMIT_SELECTOR))
    parser.add_argument("--permit-platform", default=str(DEFAULT_PERMIT_PLATFORM))
    parser.add_argument("--permit-master", default=str(DEFAULT_PERMIT_MASTER))
    parser.add_argument("--permit-provenance", default=str(DEFAULT_PERMIT_PROVENANCE))
    parser.add_argument("--permit-patent", default=str(DEFAULT_PERMIT_PATENT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    registry = _load_json(Path(str(args.registry)).resolve())
    thresholds = _load_json(Path(str(args.thresholds)).resolve())
    permit_selector_catalog = _load_json(Path(str(args.permit_selector)).resolve())
    permit_platform_catalog = _load_json(Path(str(args.permit_platform)).resolve())
    permit_master_catalog = _load_json(Path(str(args.permit_master)).resolve())
    permit_provenance_audit = _load_json(Path(str(args.permit_provenance)).resolve())
    permit_patent_evidence_bundle = _load_json(Path(str(args.permit_patent)).resolve())
    spec = build_contract_spec(
        registry,
        thresholds,
        permit_selector_catalog=permit_selector_catalog,
        permit_platform_catalog=permit_platform_catalog,
        permit_master_catalog=permit_master_catalog,
        permit_provenance_audit=permit_provenance_audit,
        permit_patent_evidence_bundle=permit_patent_evidence_bundle,
    )

    output_path = Path(str(args.output)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
