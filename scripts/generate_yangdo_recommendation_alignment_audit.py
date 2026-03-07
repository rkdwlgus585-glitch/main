#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE = ROOT / "logs" / "yangdo_recommendation_bridge_packet_latest.json"
DEFAULT_UX = ROOT / "logs" / "yangdo_recommendation_ux_packet_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_ATTORNEY = ROOT / "logs" / "attorney_handoff_latest.json"
DEFAULT_JSON = ROOT / "logs" / "yangdo_recommendation_alignment_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_recommendation_alignment_audit_latest.md"


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
    return [str(item).strip() for item in value if str(item).strip()]


def _track_a(payload: Dict[str, Any]) -> Dict[str, Any]:
    tracks = payload.get("tracks") if isinstance(payload.get("tracks"), list) else []
    for row in tracks:
        if isinstance(row, dict) and row.get("track_id") == "A":
            return row
    return {}


def build_yangdo_recommendation_alignment_audit(
    *,
    bridge_path: Path,
    ux_path: Path,
    rental_path: Path,
    attorney_path: Path,
) -> Dict[str, Any]:
    bridge = _load_json(bridge_path)
    ux = _load_json(ux_path)
    rental = _load_json(rental_path)
    attorney = _load_json(attorney_path)

    bridge_public = bridge.get("public_summary_contract") if isinstance(bridge.get("public_summary_contract"), dict) else {}
    bridge_detail = bridge.get("detail_contract") if isinstance(bridge.get("detail_contract"), dict) else {}
    bridge_rental = bridge.get("rental_packaging") if isinstance(bridge.get("rental_packaging"), dict) else {}
    bridge_market = bridge.get("market_bridge_policy") if isinstance(bridge.get("market_bridge_policy"), dict) else {}

    ux_summary = ux.get("summary") if isinstance(ux.get("summary"), dict) else {}
    ux_public = ux.get("public_summary_experience") if isinstance(ux.get("public_summary_experience"), dict) else {}
    ux_detail = ux.get("consult_detail_experience") if isinstance(ux.get("consult_detail_experience"), dict) else {}
    ux_matrix = ux.get("rental_exposure_matrix") if isinstance(ux.get("rental_exposure_matrix"), dict) else {}

    rental_recommendation = (
        rental.get("packaging", {}).get("partner_rental", {}).get("yangdo_recommendation")
        if isinstance(rental.get("packaging"), dict)
        and isinstance(rental.get("packaging", {}).get("partner_rental"), dict)
        else {}
    )
    rental_package_matrix = (
        rental_recommendation.get("package_matrix") if isinstance(rental_recommendation.get("package_matrix"), dict) else {}
    )
    rental_summary = rental.get("summary") if isinstance(rental.get("summary"), dict) else {}

    track_a = _track_a(attorney)
    attorney_position = track_a.get("attorney_position") if isinstance(track_a.get("attorney_position"), dict) else {}
    claim_focus = _as_list(attorney_position.get("claim_focus"))
    commercial_positioning = _as_list(attorney_position.get("commercial_positioning"))

    issues: List[str] = []

    service_flow_policy = str(bridge_market.get("service_flow_policy") or "")
    ux_flow_policy = str(ux_summary.get("service_flow_policy") or "")
    rental_flow_policy = str(rental_recommendation.get("service_flow_policy") or "")
    service_flow_policy_ok = bool(service_flow_policy) and service_flow_policy == ux_flow_policy == rental_flow_policy
    if not service_flow_policy_ok:
        issues.append("service_flow_policy_mismatch")

    bridge_primary = str(((bridge_public.get("primary_cta") or {}).get("label")) or "")
    bridge_secondary = str(((bridge_public.get("secondary_cta") or {}).get("label")) or "")
    ux_primary = str(ux_public.get("cta_primary_label") or "")
    ux_secondary = str(ux_public.get("cta_secondary_label") or "")
    rental_primary = str(rental_recommendation.get("service_primary_cta") or "")
    rental_secondary = str(rental_recommendation.get("service_secondary_cta") or "")
    cta_labels_ok = bool(bridge_primary and bridge_secondary) and bridge_primary == ux_primary == rental_primary and bridge_secondary == ux_secondary == rental_secondary
    if not cta_labels_ok:
        issues.append("cta_label_mismatch")

    public_fields = _as_list(bridge_public.get("fields"))
    ux_public_fields = _as_list(ux_public.get("visible_fields"))
    detail_fields = _as_list(bridge_detail.get("fields"))
    ux_detail_fields = _as_list(ux_detail.get("visible_fields"))
    field_contract_ok = public_fields == ux_public_fields and detail_fields == ux_detail_fields
    if not field_contract_ok:
        issues.append("field_contract_mismatch")

    bridge_standard = _as_list(bridge_rental.get("summary_offerings"))
    bridge_pro = _as_list(bridge_rental.get("detail_offerings"))
    bridge_internal = _as_list(bridge_rental.get("internal_offerings"))
    ux_standard = _as_list((ux_matrix.get("standard") or {}).get("offerings"))
    ux_pro_detail = _as_list((ux_matrix.get("pro_detail") or {}).get("offerings"))
    ux_pro_consult = _as_list((ux_matrix.get("pro_consult") or {}).get("offerings"))
    ux_internal = _as_list((ux_matrix.get("internal") or {}).get("offerings"))
    rental_standard = _as_list(rental_recommendation.get("summary_offerings"))
    rental_pro = _as_list(rental_recommendation.get("detail_offerings"))
    rental_internal = _as_list(rental_recommendation.get("internal_offerings"))
    rental_summary_bridge = _as_list(((rental_package_matrix.get("summary_market_bridge") or {}).get("offering_ids")))
    rental_detail_explainable = _as_list(((rental_package_matrix.get("detail_explainable") or {}).get("offering_ids")))
    rental_consult_assist = _as_list(((rental_package_matrix.get("consult_assist") or {}).get("offering_ids")))
    rental_internal_full = _as_list(((rental_package_matrix.get("internal_full") or {}).get("offering_ids")))
    bridge_pro_sorted = sorted(bridge_pro)
    rental_pro_sorted = sorted(rental_pro)
    ux_pro_combined_sorted = sorted(set(ux_pro_detail + ux_pro_consult))
    offering_exposure_ok = (
        bridge_standard == ux_standard == rental_standard == rental_summary_bridge
        and bridge_pro_sorted == rental_pro_sorted == ux_pro_combined_sorted
        and bridge_internal == ux_internal == rental_internal == rental_internal_full
        and ux_pro_detail == rental_detail_explainable
        and ux_pro_consult == rental_consult_assist
    )
    if not offering_exposure_ok:
        issues.append("offering_exposure_mismatch")

    claim_focus_join = " ".join(claim_focus).lower()
    commercial_join = " ".join(commercial_positioning).lower()
    patent_handoff_ok = (
        bool(claim_focus)
        and bool(commercial_positioning)
        and ("추천" in claim_focus_join or "precision" in claim_focus_join)
        and ("공개" in claim_focus_join or "등급" in claim_focus_join or "상세" in claim_focus_join or "detail" in claim_focus_join)
        and ("추천" in commercial_join or "precision" in commercial_join)
        and ("요약" in commercial_join or "public" in commercial_join or "pro" in commercial_join or "api" in commercial_join)
    )
    if not patent_handoff_ok:
        issues.append("attorney_handoff_missing_recommendation_split")

    contract_story_ok = (
        str(bridge_public.get("story") or "") == str(ux_public.get("story") or "") == str(rental_recommendation.get("public_story") or "")
        and str(bridge_detail.get("story") or "") == str(ux_detail.get("story") or "") == str(rental_recommendation.get("detail_story") or "")
    )
    if not contract_story_ok:
        issues.append("story_contract_mismatch")

    supported_labels_ok = _as_list(bridge.get("summary", {}).get("supported_precision_labels")) == _as_list(rental_recommendation.get("supported_precision_labels"))
    if not supported_labels_ok:
        issues.append("supported_precision_labels_mismatch")

    alignment_ok = not issues
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "alignment_ok": alignment_ok,
            "issue_count": len(issues),
            "service_flow_policy_ok": service_flow_policy_ok,
            "cta_labels_ok": cta_labels_ok,
            "field_contract_ok": field_contract_ok,
            "offering_exposure_ok": offering_exposure_ok,
            "patent_handoff_ok": patent_handoff_ok,
            "contract_story_ok": contract_story_ok,
            "supported_labels_ok": supported_labels_ok,
            "rental_recommendation_offering_count": int(rental_summary.get("yangdo_recommendation_offering_count", 0) or 0),
        },
        "contracts": {
            "service_flow_policy": {
                "bridge": service_flow_policy,
                "ux": ux_flow_policy,
                "rental": rental_flow_policy,
            },
            "cta_labels": {
                "primary": {
                    "bridge": bridge_primary,
                    "ux": ux_primary,
                    "rental": rental_primary,
                },
                "secondary": {
                    "bridge": bridge_secondary,
                    "ux": ux_secondary,
                    "rental": rental_secondary,
                },
            },
            "public_fields": {
                "bridge": public_fields,
                "ux": ux_public_fields,
            },
            "detail_fields": {
                "bridge": detail_fields,
                "ux": ux_detail_fields,
            },
            "offering_exposure": {
                "standard": {"bridge": bridge_standard, "ux": ux_standard, "rental": rental_standard},
                "pro_detail": {"ux": ux_pro_detail, "rental": rental_detail_explainable},
                "pro_consult": {"ux": ux_pro_consult, "rental": rental_consult_assist},
                "pro_combined": {"bridge": bridge_pro, "rental": rental_pro},
                "internal": {"bridge": bridge_internal, "ux": ux_internal, "rental": rental_internal},
            },
        },
        "attorney_alignment": {
            "claim_focus": claim_focus,
            "commercial_positioning": commercial_positioning,
        },
        "issues": issues,
        "artifacts": {
            "bridge_packet": str(bridge_path.resolve()),
            "ux_packet": str(ux_path.resolve()),
            "rental_catalog": str(rental_path.resolve()),
            "attorney_handoff": str(attorney_path.resolve()),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Yangdo Recommendation Alignment Audit",
        "",
        f"- alignment_ok: {summary.get('alignment_ok')}",
        f"- issue_count: {summary.get('issue_count')}",
        f"- service_flow_policy_ok: {summary.get('service_flow_policy_ok')}",
        f"- cta_labels_ok: {summary.get('cta_labels_ok')}",
        f"- field_contract_ok: {summary.get('field_contract_ok')}",
        f"- offering_exposure_ok: {summary.get('offering_exposure_ok')}",
        f"- patent_handoff_ok: {summary.get('patent_handoff_ok')}",
        f"- contract_story_ok: {summary.get('contract_story_ok')}",
        f"- supported_labels_ok: {summary.get('supported_labels_ok')}",
        "",
        "## Issues",
    ]
    issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
    if issues:
        lines.extend(f"- {issue}" for issue in issues)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit alignment between yangdo recommendation bridge, UX, rental, and attorney artifacts.")
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--attorney", type=Path, default=DEFAULT_ATTORNEY)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_recommendation_alignment_audit(
        bridge_path=args.bridge,
        ux_path=args.ux,
        rental_path=args.rental,
        attorney_path=args.attorney,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("alignment_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
