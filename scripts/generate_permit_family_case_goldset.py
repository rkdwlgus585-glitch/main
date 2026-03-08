from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT = ROOT / "config" / "permit_focus_family_registry.json"
DEFAULT_MASTER_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_PATENT_INPUT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_family_case_goldset_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_family_case_goldset_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit family case goldset input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except Exception:
        return 0.0


def _profile(row: Dict[str, Any]) -> Dict[str, Any]:
    profile = row.get("registration_requirement_profile") or {}
    return profile if isinstance(profile, dict) else {}


def _row_family_key(row: Dict[str, Any]) -> str:
    proof = row.get("raw_source_proof") or {}
    capture_meta = proof.get("capture_meta") or {} if isinstance(proof, dict) else {}
    for value in (
        capture_meta.get("family_key"),
        row.get("law_title"),
        row.get("seed_law_family"),
    ):
        text = _safe_str(value)
        if text:
            return text
    return ""


def _group_family_rows(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        family_key = _row_family_key(row)
        if not family_key:
            continue
        grouped.setdefault(family_key, []).append(row)
    return grouped


def _other_checklist(profile: Dict[str, Any]) -> Dict[str, bool]:
    components = [
        _safe_str(component)
        for component in list(profile.get("other_components") or [])
        if _safe_str(component)
    ]
    return {component: True for component in components}


def _choose_min_row(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return min(
        rows,
        key=lambda row: (
            _safe_float(_profile(row).get("capital_eok")),
            _safe_int(_profile(row).get("technicians_required")),
            _safe_str(row.get("service_code")),
        ),
    )


def _choose_max_row(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return max(
        rows,
        key=lambda row: (
            _safe_float(_profile(row).get("capital_eok")),
            _safe_int(_profile(row).get("technicians_required")),
            _safe_str(row.get("service_code")),
        ),
    )


def _build_case(
    *,
    family_key: str,
    claim_packet: Dict[str, Any],
    row: Dict[str, Any],
    case_kind: str,
    capital_eok: float,
    technicians_count: int,
    other_requirement_checklist: Dict[str, bool],
    expected_status: str,
    capital_gap_eok: float,
    technicians_gap: int,
    review_reason: str = "",
    manual_review_expected: bool = False,
) -> Dict[str, Any]:
    source_proof_summary = claim_packet.get("source_proof_summary") or {}
    return {
        "case_id": f"{_safe_str(claim_packet.get('claim_id'))}:{case_kind}:{_safe_str(row.get('service_code'))}",
        "case_kind": case_kind,
        "family_key": family_key,
        "claim_id": _safe_str(claim_packet.get("claim_id")),
        "service_code": _safe_str(row.get("service_code")),
        "service_name": _safe_str(row.get("service_name")),
        "law_title": _safe_str(row.get("law_title")),
        "legal_basis_title": _safe_str(row.get("legal_basis_title")),
        "inputs": {
            "industry_selector": _safe_str(row.get("service_code")),
            "capital_eok": round(capital_eok, 2),
            "technicians_count": technicians_count,
            "other_requirement_checklist": other_requirement_checklist,
        },
        "expected": {
            "focus_target": True,
            "overall_status": expected_status,
            "capital_gap_eok": round(capital_gap_eok, 2),
            "technicians_gap": technicians_gap,
            "review_reason": _safe_str(review_reason),
            "manual_review_expected": bool(manual_review_expected),
            "proof_visible": True,
            "claim_id_visible": bool(_safe_str(claim_packet.get("claim_id"))),
            "snapshot_visible": True,
            "checksum_sample_visible": _safe_int(source_proof_summary.get("checksum_sample_total")) > 0,
            "proof_coverage_ratio": _safe_str(source_proof_summary.get("proof_coverage_ratio")),
        },
    }


def build_family_case_goldset(
    *,
    focus_family_registry: Dict[str, Any],
    permit_patent_evidence_bundle: Dict[str, Any],
    master_catalog: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    family_rows = _group_family_rows(
        [row for row in list(focus_family_registry.get("industries") or []) if isinstance(row, dict)]
    )
    master_family_rows = _group_family_rows(
        [
            row
            for row in list((master_catalog or {}).get("industries") or [])
            if isinstance(row, dict) and bool((_profile(row) or {}).get("focus_target"))
        ]
    )

    patent_families = [
        family for family in list(permit_patent_evidence_bundle.get("families") or []) if isinstance(family, dict)
    ]
    families_out: List[Dict[str, Any]] = []
    minimum_pass_case_total = 0
    boundary_case_total = 0
    shortfall_case_total = 0
    capital_only_fail_case_total = 0
    technician_only_fail_case_total = 0
    document_missing_review_case_total = 0
    manual_review_case_total = 0

    for family in patent_families:
        family_key = _safe_str(family.get("family_key"))
        claim_packet = family.get("claim_packet") or {}
        rows = list(family_rows.get(family_key) or master_family_rows.get(family_key) or [])
        if not family_key or not isinstance(claim_packet, dict) or not rows:
            continue

        min_row = _choose_min_row(rows)
        max_row = _choose_max_row(rows)
        min_profile = _profile(min_row)
        max_profile = _profile(max_row)

        min_capital = _safe_float(min_profile.get("capital_eok"))
        min_technicians = _safe_int(min_profile.get("technicians_required"))
        max_capital = _safe_float(max_profile.get("capital_eok"))
        max_technicians = _safe_int(max_profile.get("technicians_required"))
        max_other_checklist = _other_checklist(max_profile)
        has_other_requirements = bool(max_other_checklist)

        minimum_pass_case = _build_case(
            family_key=family_key,
            claim_packet=claim_packet,
            row=min_row,
            case_kind="minimum_pass",
            capital_eok=min_capital,
            technicians_count=min_technicians,
            other_requirement_checklist=_other_checklist(min_profile),
            expected_status="pass",
            capital_gap_eok=0.0,
            technicians_gap=0,
        )
        boundary_case = _build_case(
            family_key=family_key,
            claim_packet=claim_packet,
            row=max_row,
            case_kind="boundary_pass",
            capital_eok=max_capital,
            technicians_count=max_technicians,
            other_requirement_checklist=_other_checklist(max_profile),
            expected_status="pass",
            capital_gap_eok=0.0,
            technicians_gap=0,
        )
        shortfall_case = _build_case(
            family_key=family_key,
            claim_packet=claim_packet,
            row=max_row,
            case_kind="shortfall_fail",
            capital_eok=max(0.0, round(max_capital - 0.1, 2)),
            technicians_count=max(0, max_technicians - 1),
            other_requirement_checklist=_other_checklist(max_profile),
            expected_status="shortfall",
            capital_gap_eok=0.1 if max_capital > 0 else 0.0,
            technicians_gap=1 if max_technicians > 0 else 0,
            review_reason=(
                "capital_and_technician_shortfall"
                if max_capital > 0 and max_technicians > 0
                else (
                    "capital_shortfall_only"
                    if max_capital > 0
                    else ("technician_shortfall_only" if max_technicians > 0 else "")
                )
            ),
        )
        capital_only_fail_case = _build_case(
            family_key=family_key,
            claim_packet=claim_packet,
            row=max_row,
            case_kind="capital_only_fail",
            capital_eok=max(0.0, round(max_capital - 0.1, 2)),
            technicians_count=max_technicians,
            other_requirement_checklist=max_other_checklist,
            expected_status="shortfall" if max_capital > 0 else "pass",
            capital_gap_eok=0.1 if max_capital > 0 else 0.0,
            technicians_gap=0,
            review_reason="capital_shortfall_only" if max_capital > 0 else "capital_not_required",
        )
        technician_only_fail_case = _build_case(
            family_key=family_key,
            claim_packet=claim_packet,
            row=max_row,
            case_kind="technician_only_fail",
            capital_eok=max_capital,
            technicians_count=max(0, max_technicians - 1),
            other_requirement_checklist=max_other_checklist,
            expected_status="shortfall" if max_technicians > 0 else "pass",
            capital_gap_eok=0.0,
            technicians_gap=1 if max_technicians > 0 else 0,
            review_reason="technician_shortfall_only" if max_technicians > 0 else "technician_not_required",
        )
        document_missing_review_case = _build_case(
            family_key=family_key,
            claim_packet=claim_packet,
            row=max_row,
            case_kind="document_missing_review",
            capital_eok=max_capital,
            technicians_count=max_technicians,
            other_requirement_checklist={},
            expected_status="shortfall" if has_other_requirements else "pass",
            capital_gap_eok=0.0,
            technicians_gap=0,
            review_reason="other_requirement_documents_missing" if has_other_requirements else "other_requirements_not_structured",
            manual_review_expected=has_other_requirements,
        )
        minimum_pass_case_total += 1
        boundary_case_total += 1
        shortfall_case_total += 1
        capital_only_fail_case_total += 1
        technician_only_fail_case_total += 1
        document_missing_review_case_total += 1
        if has_other_requirements:
            manual_review_case_total += 1

        families_out.append(
            {
                "family_key": family_key,
                "claim_id": _safe_str(claim_packet.get("claim_id")),
                "row_total": len(rows),
                "sample_service_codes": [
                    _safe_str(min_row.get("service_code")),
                    _safe_str(max_row.get("service_code")),
                ],
                "sample_service_names": [
                    _safe_str(min_row.get("service_name")),
                    _safe_str(max_row.get("service_name")),
                ],
                "cases": [
                    minimum_pass_case,
                    boundary_case,
                    shortfall_case,
                    capital_only_fail_case,
                    technician_only_fail_case,
                    document_missing_review_case,
                ],
            }
        )

    edge_case_total = (
        capital_only_fail_case_total
        + technician_only_fail_case_total
        + document_missing_review_case_total
    )
    case_total = minimum_pass_case_total + boundary_case_total + shortfall_case_total + edge_case_total
    summary = {
        "family_total": len(families_out),
        "case_total": case_total,
        "minimum_pass_case_total": minimum_pass_case_total,
        "boundary_case_total": boundary_case_total,
        "shortfall_case_total": shortfall_case_total,
        "capital_only_fail_case_total": capital_only_fail_case_total,
        "technician_only_fail_case_total": technician_only_fail_case_total,
        "document_missing_review_case_total": document_missing_review_case_total,
        "edge_case_total": edge_case_total,
        "edge_case_family_total": len(families_out) if edge_case_total else 0,
        "manual_review_case_total": manual_review_case_total,
        "claim_packet_complete_family_total": _safe_int(
            (permit_patent_evidence_bundle.get("summary") or {}).get("claim_packet_complete_family_total")
        ),
        "goldset_complete_family_total": len(families_out),
        "parallel_lane_id": "family_case_goldset",
        "edge_case_ready": bool(families_out) and edge_case_total >= len(families_out) * 3,
        "goldset_ready": bool(families_out) and len(families_out) == _safe_int(
            (permit_patent_evidence_bundle.get("summary") or {}).get("claim_packet_complete_family_total")
        ),
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "families": families_out,
    }


def render_markdown(bundle: Dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    lines = [
        "# Permit Family Case Goldset",
        "",
        "## Summary",
        f"- family_total: `{summary.get('family_total', 0)}`",
        f"- case_total: `{summary.get('case_total', 0)}`",
        f"- minimum_pass_case_total: `{summary.get('minimum_pass_case_total', 0)}`",
        f"- boundary_case_total: `{summary.get('boundary_case_total', 0)}`",
        f"- shortfall_case_total: `{summary.get('shortfall_case_total', 0)}`",
        f"- capital_only_fail_case_total: `{summary.get('capital_only_fail_case_total', 0)}`",
        f"- technician_only_fail_case_total: `{summary.get('technician_only_fail_case_total', 0)}`",
        f"- document_missing_review_case_total: `{summary.get('document_missing_review_case_total', 0)}`",
        f"- edge_case_total: `{summary.get('edge_case_total', 0)}`",
        f"- edge_case_family_total: `{summary.get('edge_case_family_total', 0)}`",
        f"- manual_review_case_total: `{summary.get('manual_review_case_total', 0)}`",
        f"- claim_packet_complete_family_total: `{summary.get('claim_packet_complete_family_total', 0)}`",
        f"- goldset_complete_family_total: `{summary.get('goldset_complete_family_total', 0)}`",
        f"- edge_case_ready: `{summary.get('edge_case_ready', False)}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        f"- goldset_ready: `{summary.get('goldset_ready', False)}`",
        "",
        "## Families",
    ]
    for family in list(bundle.get("families") or []):
        if not isinstance(family, dict):
            continue
        lines.append(
            f"- `{family.get('family_key', '')}` claim `{family.get('claim_id', '')}` / "
            f"rows {family.get('row_total', 0)} / cases {len(list(family.get('cases') or []))}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate permit family case gold-set scenarios.")
    parser.add_argument("--focus-family-registry-input", default=str(DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT))
    parser.add_argument("--master-input", default=str(DEFAULT_MASTER_INPUT))
    parser.add_argument("--patent-input", default=str(DEFAULT_PATENT_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    bundle = build_family_case_goldset(
        focus_family_registry=_load_json(Path(args.focus_family_registry_input).expanduser().resolve()),
        permit_patent_evidence_bundle=_load_json(Path(args.patent_input).expanduser().resolve()),
        master_catalog=_load_json(Path(args.master_input).expanduser().resolve()),
    )
    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(bundle), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
