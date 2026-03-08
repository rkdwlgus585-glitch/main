#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator


DEFAULT_MASTER_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_GOLDSET_INPUT = ROOT / "logs" / "permit_family_case_goldset_latest.json"
DEFAULT_HTML_INPUT = ROOT / "output" / "ai_permit_precheck.html"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_runtime_case_assertions_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_runtime_case_assertions_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime case assertion input must be a JSON object")
    return payload


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _runtime_proof_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    required_markers = (
        'id="proofClaimBox"',
        "const renderProofClaim = (industry) => {",
        "claim_packet_summary",
        "법령군 증빙",
    )
    return all(marker in text for marker in required_markers)


def _expand_runtime_html_text(html: str) -> str:
    text = str(html or "")
    sources = [text]
    for encoded in re.findall(r'const encoded="([^"]+)";', text):
        try:
            decoded = base64.b64decode(str(encoded or "").strip()).decode("utf-8")
        except Exception:
            continue
        if decoded:
            sources.append(decoded)
    return "\n".join(sources)


def _runtime_proof_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    required_markers = (
        'id="proofClaimBox"',
        "const renderProofClaim = (industry) => {",
        "claim_packet_summary",
    )
    if not all(marker in text for marker in required_markers):
        return False
    return "법령군 증빙" in text or "踰뺣졊援?利앸튃" in text


def _extract_inline_bootstrap(html: str) -> Dict[str, Any]:
    text = _expand_runtime_html_text(html)
    match = re.search(r'const inlineBootstrapCompressed = "([^"]*)";', text)
    if not match:
        return {}
    encoded = str(match.group(1) or "").strip()
    if not encoded:
        return {}
    raw = gzip.decompress(base64.b64decode(encoded))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("inline bootstrap payload must be a JSON object")
    return payload


def _build_runtime_rule(row: Dict[str, Any]) -> Dict[str, Any]:
    profile = row.get("registration_requirement_profile") if isinstance(row.get("registration_requirement_profile"), dict) else {}
    raw_source_proof = row.get("raw_source_proof") if isinstance(row.get("raw_source_proof"), dict) else {}
    source_urls = [str(item or "").strip() for item in list(raw_source_proof.get("source_urls") or []) if str(item or "").strip()]
    return {
        "industry_name": _safe_str(row.get("service_name")),
        "requirements": {
            "capital_eok": _safe_float(profile.get("capital_eok")),
            "technicians": _safe_int(profile.get("technicians_required")),
            "equipment_count": _safe_int(profile.get("equipment_count_required")),
            "deposit_days": _safe_int(profile.get("deposit_days_required")),
        },
        "legal_basis": [
            {
                "law_title": _safe_str(row.get("law_title")),
                "article": _safe_str(row.get("legal_basis_title")),
                "url": source_urls[0] if source_urls else "",
            }
        ],
    }


def _expected_equipment_count(row: Dict[str, Any], case_inputs: Dict[str, Any]) -> int:
    profile = row.get("registration_requirement_profile") if isinstance(row.get("registration_requirement_profile"), dict) else {}
    required_equipment = _safe_int(profile.get("equipment_count_required"))
    explicit = case_inputs.get("equipment_count")
    if explicit is not None:
        return max(0, _safe_int(explicit))
    checklist = case_inputs.get("other_requirement_checklist")
    if isinstance(checklist, dict) and bool(checklist.get("equipment")):
        return required_equipment
    return 0


def _status_from_diagnosis(diagnosis: Dict[str, Any]) -> str:
    return "pass" if bool(diagnosis.get("overall_ok")) else "shortfall"


def _build_case_assertion(
    row: Dict[str, Any] | None,
    case: Dict[str, Any],
    *,
    bootstrap_row_present: bool,
) -> Dict[str, Any]:
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    case_inputs = case.get("inputs") if isinstance(case.get("inputs"), dict) else {}
    claim_id = _safe_str(case.get("claim_id"))
    if not claim_id:
        claim_id = _safe_str(case.get("claim_packet_id"))
    out = {
        "case_id": _safe_str(case.get("case_id")),
        "case_kind": _safe_str(case.get("case_kind")),
        "family_key": _safe_str(case.get("family_key")),
        "claim_id": claim_id,
        "service_code": _safe_str(case.get("service_code")),
        "service_name": _safe_str(case.get("service_name")),
        "expected_status": _safe_str(expected.get("overall_status")),
        "actual_status": "",
        "expected_capital_gap_eok": round(_safe_float(expected.get("capital_gap_eok")), 4),
        "actual_capital_gap_eok": 0.0,
        "expected_technicians_gap": _safe_int(expected.get("technicians_gap")),
        "actual_technicians_gap": 0,
        "assertion_flags": {
            "bootstrap_row_present": False,
            "claim_id_match": False,
            "proof_visible": False,
            "claim_id_visible": False,
            "snapshot_visible": False,
            "checksum_sample_visible": False,
            "proof_coverage_ratio_match": False,
            "status_match": False,
            "capital_gap_match": False,
            "technicians_gap_match": False,
        },
        "ok": False,
    }
    if not isinstance(row, dict):
        return out

    out["assertion_flags"]["bootstrap_row_present"] = bootstrap_row_present
    claim_summary = row.get("claim_packet_summary") if isinstance(row.get("claim_packet_summary"), dict) else {}
    raw_source_proof = row.get("raw_source_proof") if isinstance(row.get("raw_source_proof"), dict) else {}
    out["assertion_flags"]["claim_id_match"] = _safe_str(claim_summary.get("claim_id")) == claim_id
    proof_visible = bool(raw_source_proof or claim_summary)
    out["assertion_flags"]["proof_visible"] = proof_visible == bool(expected.get("proof_visible", proof_visible))
    out["assertion_flags"]["claim_id_visible"] = bool(claim_summary.get("claim_id")) == bool(
        expected.get("claim_id_visible", bool(claim_summary.get("claim_id")))
    )
    snapshot_visible = bool(
        _safe_str(claim_summary.get("official_snapshot_note")) or _safe_str(raw_source_proof.get("official_snapshot_note"))
    )
    out["assertion_flags"]["snapshot_visible"] = snapshot_visible == bool(
        expected.get("snapshot_visible", snapshot_visible)
    )
    checksum_visible = bool(list(claim_summary.get("checksum_samples") or [])) or bool(
        _safe_str(raw_source_proof.get("source_checksum"))
    )
    out["assertion_flags"]["checksum_sample_visible"] = checksum_visible == bool(
        expected.get("checksum_sample_visible", checksum_visible)
    )
    expected_ratio = _safe_str(expected.get("proof_coverage_ratio"))
    actual_ratio = _safe_str(claim_summary.get("proof_coverage_ratio"))
    out["assertion_flags"]["proof_coverage_ratio_match"] = not expected_ratio or actual_ratio == expected_ratio

    rule = _build_runtime_rule(row)
    diagnosis = permit_diagnosis_calculator.evaluate_registration_diagnosis(
        rule=rule,
        current_capital_eok=_safe_float(case_inputs.get("capital_eok")),
        current_technicians=_safe_int(case_inputs.get("technicians_count")),
        current_equipment_count=_expected_equipment_count(row, case_inputs),
        raw_capital_input=str(case_inputs.get("capital_eok") or ""),
        extra_inputs={
            "other_requirement_checklist": case_inputs.get("other_requirement_checklist")
            if isinstance(case_inputs.get("other_requirement_checklist"), dict)
            else {},
        },
    )
    out["actual_status"] = _status_from_diagnosis(diagnosis)
    out["actual_capital_gap_eok"] = round(_safe_float((diagnosis.get("capital") or {}).get("gap")), 4)
    out["actual_technicians_gap"] = _safe_int((diagnosis.get("technicians") or {}).get("gap"))
    out["assertion_flags"]["status_match"] = out["actual_status"] == out["expected_status"]
    out["assertion_flags"]["capital_gap_match"] = out["actual_capital_gap_eok"] == out["expected_capital_gap_eok"]
    out["assertion_flags"]["technicians_gap_match"] = out["actual_technicians_gap"] == out["expected_technicians_gap"]
    out["ok"] = all(bool(value) for value in out["assertion_flags"].values())
    return out


def build_runtime_case_assertions(
    *,
    master_catalog: Dict[str, Any],
    permit_family_case_goldset: Dict[str, Any],
    runtime_html: str,
) -> Dict[str, Any]:
    bootstrap = _extract_inline_bootstrap(runtime_html)
    permit_catalog = bootstrap.get("permitCatalog") if isinstance(bootstrap.get("permitCatalog"), dict) else {}
    runtime_rows = [row for row in list(permit_catalog.get("industries") or []) if isinstance(row, dict)]
    runtime_row_by_code = {
        _safe_str(row.get("service_code")): row
        for row in runtime_rows
        if _safe_str(row.get("service_code"))
    }
    master_rows = [row for row in list(master_catalog.get("industries") or []) if isinstance(row, dict)]
    master_row_by_code = {
        _safe_str(row.get("service_code")): row
        for row in master_rows
        if _safe_str(row.get("service_code"))
    }

    family_reports: List[Dict[str, Any]] = []
    asserted_family_total = 0
    asserted_case_total = 0
    failed_case_ids: List[str] = []
    for family in [row for row in list(permit_family_case_goldset.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        claim_id = _safe_str(family.get("claim_id"))
        case_reports: List[Dict[str, Any]] = []
        for case in [item for item in list(family.get("cases") or []) if isinstance(item, dict)]:
            service_code = _safe_str(case.get("service_code"))
            runtime_row = runtime_row_by_code.get(service_code)
            assertion_row = runtime_row or master_row_by_code.get(service_code)
            enriched_case = dict(case)
            if not _safe_str(enriched_case.get("claim_id")):
                enriched_case["claim_id"] = claim_id
            case_report = _build_case_assertion(
                assertion_row,
                enriched_case,
                bootstrap_row_present=runtime_row is not None,
            )
            case_reports.append(case_report)
            if bool(case_report.get("ok")):
                asserted_case_total += 1
            else:
                failed_case_ids.append(_safe_str(case_report.get("case_id")))
        family_ok = bool(case_reports) and all(bool(case_report.get("ok")) for case_report in case_reports)
        if family_ok:
            asserted_family_total += 1
        family_reports.append(
            {
                "family_key": family_key,
                "claim_id": claim_id,
                "row_total": _safe_int(family.get("row_total")),
                "case_total": len(case_reports),
                "asserted_case_total": sum(1 for case_report in case_reports if bool(case_report.get("ok"))),
                "ok": family_ok,
                "cases": case_reports,
            }
        )

    summary = {
        "family_total": len(family_reports),
        "case_total": sum(_safe_int(row.get("case_total")) for row in family_reports),
        "asserted_family_total": asserted_family_total,
        "asserted_case_total": asserted_case_total,
        "failed_case_total": len(failed_case_ids),
        "bootstrap_industry_total": len(runtime_rows),
        "runtime_proof_surface_ready": _runtime_proof_surface_ready(runtime_html),
        "execution_lane_id": "family_case_runtime_assertions",
        "parallel_lane_id": "widget_case_parity",
        "runtime_assertions_ready": len(failed_case_ids) == 0 and asserted_family_total == len(family_reports),
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "source_paths": {
            "master_catalog": str(DEFAULT_MASTER_INPUT.resolve()),
            "family_case_goldset": str(DEFAULT_GOLDSET_INPUT.resolve()),
            "runtime_html": str(DEFAULT_HTML_INPUT.resolve()),
        },
        "failed_case_ids": failed_case_ids[:12],
        "families": family_reports,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Runtime Case Assertions",
        "",
        "## Summary",
        f"- family_total: `{summary.get('family_total', 0)}`",
        f"- case_total: `{summary.get('case_total', 0)}`",
        f"- asserted_family_total: `{summary.get('asserted_family_total', 0)}`",
        f"- asserted_case_total: `{summary.get('asserted_case_total', 0)}`",
        f"- failed_case_total: `{summary.get('failed_case_total', 0)}`",
        f"- bootstrap_industry_total: `{summary.get('bootstrap_industry_total', 0)}`",
        f"- runtime_proof_surface_ready: `{summary.get('runtime_proof_surface_ready', False)}`",
        f"- runtime_assertions_ready: `{summary.get('runtime_assertions_ready', False)}`",
        f"- execution_lane_id: `{summary.get('execution_lane_id', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        "",
        "## Families",
    ]
    for family in [row for row in list(report.get("families") or []) if isinstance(row, dict)]:
        lines.append(
            f"- `{family.get('family_key', '')}` claim={family.get('claim_id', '')} "
            f"ok={family.get('ok', False)} cases={family.get('asserted_case_total', 0)}/{family.get('case_total', 0)}"
        )
    if list(report.get("failed_case_ids") or []):
        lines.extend(["", "## Failed Cases"])
        for case_id in list(report.get("failed_case_ids") or []):
            lines.append(f"- `{case_id}`")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate runtime assertions from permit family case gold-set.")
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER_INPUT)
    parser.add_argument("--goldset", type=Path, default=DEFAULT_GOLDSET_INPUT)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_runtime_case_assertions(
        master_catalog=_load_json(args.master.resolve()),
        permit_family_case_goldset=_load_json(args.goldset.resolve()),
        runtime_html=_load_text(args.html.resolve()),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "json": str(args.json_output.resolve()), "md": str(args.md_output.resolve())},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if bool((report.get("summary") or {}).get("runtime_assertions_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
