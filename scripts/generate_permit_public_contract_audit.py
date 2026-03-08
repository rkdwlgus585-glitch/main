#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UX = ROOT / "logs" / "permit_service_ux_packet_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_ATTORNEY = ROOT / "logs" / "attorney_handoff_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_public_contract_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_public_contract_audit_latest.md"


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


def _track_b(attorney: Dict[str, Any]) -> Dict[str, Any]:
    for row in list(attorney.get("tracks") or []):
        if isinstance(row, dict) and str(row.get("track_id") or "").strip() == "B":
            return row
    return {}


def build_permit_public_contract_audit(
    *,
    ux_path: Path,
    rental_path: Path,
    operations_path: Path,
    attorney_path: Path,
) -> Dict[str, Any]:
    ux = _load_json(ux_path)
    rental = _load_json(rental_path)
    operations = _load_json(operations_path)
    attorney = _load_json(attorney_path)

    public_exp = ux.get("public_summary_experience") if isinstance(ux.get("public_summary_experience"), dict) else {}
    detail_exp = ux.get("detail_checklist_experience") if isinstance(ux.get("detail_checklist_experience"), dict) else {}
    assist_exp = ux.get("manual_review_assist_experience") if isinstance(ux.get("manual_review_assist_experience"), dict) else {}
    internal_exp = ux.get("internal_review_experience") if isinstance(ux.get("internal_review_experience"), dict) else {}
    ux_summary = ux.get("summary") if isinstance(ux.get("summary"), dict) else {}

    permit_rental = ((((rental.get("packaging") or {}).get("partner_rental") or {}).get("permit_precheck")) or {})
    permit_rental = permit_rental if isinstance(permit_rental, dict) else {}
    permit_matrix = permit_rental.get("package_matrix") if isinstance(permit_rental.get("package_matrix"), dict) else {}

    op_decisions = operations.get("decisions") if isinstance(operations.get("decisions"), dict) else {}
    op_summaries = operations.get("summaries") if isinstance(operations.get("summaries"), dict) else {}
    op_permit_ux = op_summaries.get("permit_service_ux") if isinstance(op_summaries.get("permit_service_ux"), dict) else {}

    track_b = _track_b(attorney)
    attorney_position = track_b.get("attorney_position") if isinstance(track_b.get("attorney_position"), dict) else {}
    claim_focus_text = " ".join(_as_list(attorney_position.get("claim_focus"))).lower()
    commercial_positioning_text = " ".join(_as_list(attorney_position.get("commercial_positioning"))).lower()

    public_fields = _as_list(public_exp.get("visible_fields"))
    detail_fields = _as_list(detail_exp.get("visible_fields"))
    assist_fields = _as_list(assist_exp.get("visible_fields"))
    internal_fields = _as_list(internal_exp.get("visible_fields"))

    expected_public_fields = ["overall_status", "required_summary", "next_actions"]
    forbidden_public = {"criterion_results", "pending_criteria_lines", "mapping_confidence", "legal_basis"}
    forbidden_detail = {"pending_criteria_lines", "mapping_confidence"}

    public_summary_only_ok = public_fields == expected_public_fields and not any(field in forbidden_public for field in public_fields)
    detail_checklist_contract_ok = (
        {"criterion_results", "evidence_checklist", "document_templates", "legal_basis"}.issubset(set(detail_fields))
        and not any(field in forbidden_detail for field in detail_fields)
    )
    assist_contract_ok = (
        {"manual_review_required", "coverage_status"}.issubset(set(assist_fields))
        and {"criterion_results", "evidence_checklist", "document_templates", "legal_basis"}.issubset(set(assist_fields))
    )
    internal_visibility_ok = {"pending_criteria_lines", "mapping_confidence"}.issubset(set(internal_fields))
    offering_exposure_ok = (
        _as_list(public_exp.get("allowed_offerings")) == _as_list(((permit_matrix.get("summary_self_check") or {}).get("offering_ids")))
        and _as_list(detail_exp.get("allowed_offerings")) == _as_list(((permit_matrix.get("detail_checklist") or {}).get("offering_ids")))
        and _as_list(assist_exp.get("allowed_offerings")) == _as_list(((permit_matrix.get("manual_review_assist") or {}).get("offering_ids")))
    )
    focus_or_position_text = f"{claim_focus_text} {commercial_positioning_text}".strip()
    has_checklist_story = "checklist" in focus_or_position_text or "체크리스트" in focus_or_position_text
    has_gate_story = (
        "manual review" in focus_or_position_text
        or "manual-review" in focus_or_position_text
        or "gate" in focus_or_position_text
        or "수동 검토" in focus_or_position_text
        or "판정보류" in focus_or_position_text
    )
    has_mapping_story = (
        "coverage" in focus_or_position_text
        or "mapping" in focus_or_position_text
        or "criteria" in focus_or_position_text
        or "typed criteria" in focus_or_position_text
        or "매핑" in focus_or_position_text
        or "기준" in focus_or_position_text
        or "규칙카탈로그" in focus_or_position_text
    )
    patent_handoff_ok = has_checklist_story and has_gate_story and has_mapping_story

    issues: List[str] = []
    if not bool(ux_summary.get("packet_ready")) or not bool(op_decisions.get("permit_service_ux_ready")):
        issues.append("permit_service_ux_not_ready")
    if not public_summary_only_ok:
        issues.append("public_summary_contract_mismatch")
    if not detail_checklist_contract_ok:
        issues.append("detail_checklist_contract_mismatch")
    if not assist_contract_ok:
        issues.append("manual_review_assist_contract_mismatch")
    if not internal_visibility_ok:
        issues.append("internal_visibility_contract_mismatch")
    if not offering_exposure_ok:
        issues.append("offering_exposure_contract_mismatch")
    if not patent_handoff_ok:
        issues.append("attorney_handoff_missing_permit_contract_story")

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "contract_ok": not issues,
            "issue_count": len(issues),
            "public_summary_only_ok": public_summary_only_ok,
            "detail_checklist_contract_ok": detail_checklist_contract_ok,
            "assist_contract_ok": assist_contract_ok,
            "internal_visibility_ok": internal_visibility_ok,
            "offering_exposure_ok": offering_exposure_ok,
            "patent_handoff_ok": patent_handoff_ok,
        },
        "contracts": {
            "public_fields": public_fields,
            "detail_fields": detail_fields,
            "assist_fields": assist_fields,
            "internal_fields": internal_fields,
            "public_allowed_offerings": _as_list(public_exp.get("allowed_offerings")),
            "detail_allowed_offerings": _as_list(detail_exp.get("allowed_offerings")),
            "assist_allowed_offerings": _as_list(assist_exp.get("allowed_offerings")),
            "expected_public_offerings": _as_list(((permit_matrix.get("summary_self_check") or {}).get("offering_ids"))),
            "expected_detail_offerings": _as_list(((permit_matrix.get("detail_checklist") or {}).get("offering_ids"))),
            "expected_assist_offerings": _as_list(((permit_matrix.get("manual_review_assist") or {}).get("offering_ids"))),
            "service_flow_policy": str(ux_summary.get("service_flow_policy") or op_permit_ux.get("service_flow_policy") or ""),
        },
        "issues": issues,
        "artifacts": {
            "permit_service_ux_packet": str(ux_path.resolve()),
            "widget_rental_catalog": str(rental_path.resolve()),
            "operations_packet": str(operations_path.resolve()),
            "attorney_handoff": str(attorney_path.resolve()),
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Permit Public Contract Audit",
        "",
        f"- contract_ok: {summary.get('contract_ok')}",
        f"- issue_count: {summary.get('issue_count')}",
        f"- public_summary_only_ok: {summary.get('public_summary_only_ok')}",
        f"- detail_checklist_contract_ok: {summary.get('detail_checklist_contract_ok')}",
        f"- assist_contract_ok: {summary.get('assist_contract_ok')}",
        f"- internal_visibility_ok: {summary.get('internal_visibility_ok')}",
        f"- offering_exposure_ok: {summary.get('offering_exposure_ok')}",
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
    parser = argparse.ArgumentParser(description="Audit public/detail/internal exposure contract for permit service lanes.")
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--attorney", type=Path, default=DEFAULT_ATTORNEY)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_permit_public_contract_audit(
        ux_path=args.ux,
        rental_path=args.rental,
        operations_path=args.operations,
        attorney_path=args.attorney,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0 if bool((payload.get("summary") or {}).get("contract_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
