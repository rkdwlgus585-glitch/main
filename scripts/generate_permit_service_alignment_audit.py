#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COPY = ROOT / "logs" / "permit_service_copy_packet_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_ATTORNEY = ROOT / "logs" / "attorney_handoff_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_service_alignment_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_service_alignment_audit_latest.md"


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


def _track_b(payload: Dict[str, Any]) -> Dict[str, Any]:
    tracks = payload.get("tracks") if isinstance(payload.get("tracks"), list) else []
    for row in tracks:
        if isinstance(row, dict) and row.get("track_id") == "B":
            return row
    return {}


def build_permit_service_alignment_audit(
    *,
    copy_path: Path,
    rental_path: Path,
    operations_path: Path,
    attorney_path: Path,
) -> Dict[str, Any]:
    copy_packet = _load_json(copy_path)
    rental = _load_json(rental_path)
    operations = _load_json(operations_path)
    attorney = _load_json(attorney_path)

    copy_summary = copy_packet.get("summary") if isinstance(copy_packet.get("summary"), dict) else {}
    copy_cta = copy_packet.get("cta_ladder") if isinstance(copy_packet.get("cta_ladder"), dict) else {}
    copy_proof = copy_packet.get("proof_points") if isinstance(copy_packet.get("proof_points"), dict) else {}

    rental_summary = rental.get("summary") if isinstance(rental.get("summary"), dict) else {}
    rental_packaging = rental.get("packaging") if isinstance(rental.get("packaging"), dict) else {}
    partner_rental = rental_packaging.get("partner_rental") if isinstance(rental_packaging.get("partner_rental"), dict) else {}
    widget_standard = _as_list(partner_rental.get("widget_standard"))
    api_or_detail_pro = _as_list(partner_rental.get("api_or_detail_pro"))
    offerings = rental.get("offerings") if isinstance(rental.get("offerings"), list) else []
    permit_offerings = [
        row for row in offerings
        if isinstance(row, dict) and "permit" in _as_list(row.get("systems"))
    ]

    op_summaries = operations.get("summaries") if isinstance(operations.get("summaries"), dict) else {}
    op_decisions = operations.get("decisions") if isinstance(operations.get("decisions"), dict) else {}
    op_permit = op_summaries.get("permit_service_copy") if isinstance(op_summaries.get("permit_service_copy"), dict) else {}

    track_b = _track_b(attorney)
    attorney_position = track_b.get("attorney_position") if isinstance(track_b.get("attorney_position"), dict) else {}
    claim_focus = " ".join(_as_list(attorney_position.get("claim_focus"))).lower()
    commercial_positioning = " ".join(_as_list(attorney_position.get("commercial_positioning"))).lower()

    issues: List[str] = []

    cta_contract_ok = (
        str(((copy_cta.get("primary_self_check") or {}).get("label")) or "")
        == str(op_permit.get("primary_self_check_cta") or "")
        and str(((copy_cta.get("secondary_consult") or {}).get("label")) or "")
        == str(op_permit.get("secondary_consult_cta") or "")
        and str(((copy_cta.get("supporting_knowledge") or {}).get("label")) or "")
        == str(op_permit.get("knowledge_cta") or "")
    )
    if not cta_contract_ok:
        issues.append("cta_contract_mismatch")

    proof_point_contract_ok = (
        int(copy_proof.get("permit_selector_entry_total", 0) or 0)
        == int(rental_summary.get("permit_selector_entry_total", 0) or 0)
        and int(copy_proof.get("permit_platform_industry_total", 0) or 0)
        == int(rental_summary.get("permit_platform_industry_total", 0) or 0)
    )
    if not proof_point_contract_ok:
        issues.append("proof_point_mismatch")

    service_story_ok = (
        bool(copy_summary.get("packet_ready"))
        and bool(copy_summary.get("service_copy_ready"))
        and bool(copy_summary.get("checklist_story_ready"))
        and bool(copy_summary.get("manual_review_story_ready"))
        and bool(copy_summary.get("document_story_ready"))
        and bool(op_decisions.get("permit_service_copy_ready"))
        and bool(op_permit.get("packet_ready"))
        and bool(op_permit.get("service_copy_ready"))
        and bool(op_permit.get("checklist_story_ready"))
        and bool(op_permit.get("manual_review_story_ready"))
        and bool(op_permit.get("document_story_ready"))
    )
    if not service_story_ok:
        issues.append("service_story_not_ready")

    rental_positioning_ok = (
        "permit_standard" in widget_standard
        and "permit_pro" in api_or_detail_pro
        and any(isinstance(row, dict) and row.get("offering_id") == "permit_standard" for row in permit_offerings)
        and any(isinstance(row, dict) and row.get("offering_id") == "permit_pro" for row in permit_offerings)
    )
    if not rental_positioning_ok:
        issues.append("rental_positioning_missing")

    patent_handoff_ok = (
        "typed criteria" in claim_focus
        and ("manual-review" in claim_focus or "체크리스트" in claim_focus)
        and ("사전검토" in commercial_positioning or "api 공급" in commercial_positioning or "manual-review gate" in commercial_positioning)
    )
    if not patent_handoff_ok:
        issues.append("attorney_handoff_missing_permit_story")

    alignment_ok = not issues
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "alignment_ok": alignment_ok,
            "issue_count": len(issues),
            "cta_contract_ok": cta_contract_ok,
            "proof_point_contract_ok": proof_point_contract_ok,
            "service_story_ok": service_story_ok,
            "rental_positioning_ok": rental_positioning_ok,
            "patent_handoff_ok": patent_handoff_ok,
            "permit_offering_count": len(permit_offerings),
        },
        "contracts": {
            "ctas": {
                "primary_self_check": {
                    "copy": str(((copy_cta.get("primary_self_check") or {}).get("label")) or ""),
                    "operations": str(op_permit.get("primary_self_check_cta") or ""),
                },
                "secondary_consult": {
                    "copy": str(((copy_cta.get("secondary_consult") or {}).get("label")) or ""),
                    "operations": str(op_permit.get("secondary_consult_cta") or ""),
                },
                "knowledge": {
                    "copy": str(((copy_cta.get("supporting_knowledge") or {}).get("label")) or ""),
                    "operations": str(op_permit.get("knowledge_cta") or ""),
                },
            },
            "proof_points": {
                "selector_entry_total": {
                    "copy": int(copy_proof.get("permit_selector_entry_total", 0) or 0),
                    "rental": int(rental_summary.get("permit_selector_entry_total", 0) or 0),
                },
                "platform_industry_total": {
                    "copy": int(copy_proof.get("permit_platform_industry_total", 0) or 0),
                    "rental": int(rental_summary.get("permit_platform_industry_total", 0) or 0),
                },
            },
            "rental_positioning": {
                "widget_standard": widget_standard,
                "api_or_detail_pro": api_or_detail_pro,
                "permit_offerings": [str(row.get("offering_id") or "") for row in permit_offerings],
            },
        },
        "attorney_alignment": {
            "claim_focus": _as_list(attorney_position.get("claim_focus")),
            "commercial_positioning": _as_list(attorney_position.get("commercial_positioning")),
        },
        "issues": issues,
        "artifacts": {
            "permit_service_copy_packet": str(copy_path.resolve()),
            "widget_rental_catalog": str(rental_path.resolve()),
            "operations_packet": str(operations_path.resolve()),
            "attorney_handoff": str(attorney_path.resolve()),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Permit Service Alignment Audit",
        "",
        f"- alignment_ok: {summary.get('alignment_ok')}",
        f"- issue_count: {summary.get('issue_count')}",
        f"- cta_contract_ok: {summary.get('cta_contract_ok')}",
        f"- proof_point_contract_ok: {summary.get('proof_point_contract_ok')}",
        f"- service_story_ok: {summary.get('service_story_ok')}",
        f"- rental_positioning_ok: {summary.get('rental_positioning_ok')}",
        f"- patent_handoff_ok: {summary.get('patent_handoff_ok')}",
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
    parser = argparse.ArgumentParser(description="Audit alignment between permit service copy, rental, operations, and attorney artifacts.")
    parser.add_argument("--copy", type=Path, default=DEFAULT_COPY)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--attorney", type=Path, default=DEFAULT_ATTORNEY)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_permit_service_alignment_audit(
        copy_path=args.copy,
        rental_path=args.rental,
        operations_path=args.operations,
        attorney_path=args.attorney,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("alignment_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
