#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_FOCUS_INPUT = ROOT / "logs" / "permit_focus_priority_latest.json"
DEFAULT_RUNTIME_ASSERTIONS_INPUT = ROOT / "logs" / "permit_runtime_case_assertions_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_capital_registration_logic_packet_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_capital_registration_logic_packet_latest.md"


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


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _family_key(row: Dict[str, Any]) -> str:
    claim_summary = _safe_dict(row.get("claim_packet_summary"))
    for candidate in (
        claim_summary.get("family_key"),
        row.get("seed_law_family"),
        row.get("law_title"),
        row.get("legal_basis_title"),
        row.get("major_name"),
        row.get("service_code"),
    ):
        text = _safe_str(candidate)
        if text:
            return text
    return "unknown_family"


def _guarded_core_only_service_codes(runtime_case_assertions: Dict[str, Any] | None) -> set[str]:
    guarded: set[str] = set()
    for family in _safe_list((runtime_case_assertions or {}).get("families")):
        item = _safe_dict(family)
        for case in _safe_list(item.get("cases")):
            case_item = _safe_dict(case)
            if _safe_str(case_item.get("case_kind")) != "document_missing_review":
                continue
            if not bool(case_item.get("ok")):
                continue
            if _safe_str(case_item.get("expected_status")) != "pass":
                continue
            if _safe_str(case_item.get("actual_status")) != "pass":
                continue
            service_code = _safe_str(case_item.get("service_code"))
            if service_code:
                guarded.add(service_code)
    return guarded


def _focus_rows(master_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in _safe_list(master_catalog.get("industries")):
        item = _safe_dict(row)
        profile = _safe_dict(item.get("registration_requirement_profile"))
        if not item or not profile:
            continue
        if not bool(profile.get("focus_target")):
            continue
        rows.append(item)
    return rows


def _candidate(
    *,
    candidate_id: str,
    title: str,
    reason: str,
    affected_total: int,
    impact: str,
    next_action: str,
) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "reason": reason,
        "affected_total": int(affected_total),
        "impact": impact,
        "next_action": next_action,
    }


def _has_threshold_spread(family: Dict[str, Any]) -> bool:
    capital_min = family.get("capital_min_eok")
    capital_max = family.get("capital_max_eok")
    technicians_min = family.get("technicians_min")
    technicians_max = family.get("technicians_max")
    capital_spread = (
        capital_min is not None
        and capital_max is not None
        and float(capital_min) != float(capital_max)
    )
    technician_spread = (
        technicians_min is not None
        and technicians_max is not None
        and int(technicians_min) != int(technicians_max)
    )
    return bool(capital_spread or technician_spread)


def _threshold_spread_priority_row(family: Dict[str, Any]) -> Dict[str, Any]:
    capital_min = family.get("capital_min_eok")
    capital_max = family.get("capital_max_eok")
    technicians_min = family.get("technicians_min")
    technicians_max = family.get("technicians_max")
    capital_spread_eok = 0.0
    technician_spread = 0
    if capital_min is not None and capital_max is not None:
        capital_spread_eok = round(float(capital_max) - float(capital_min), 3)
    if technicians_min is not None and technicians_max is not None:
        technician_spread = int(technicians_max) - int(technicians_min)
    row_total = int(family.get("row_total", 0) or 0)
    with_other_row_total = int(family.get("with_other_row_total", 0) or 0)
    complexity_score = round(
        (row_total * 2.0)
        + (with_other_row_total * 1.0)
        + (capital_spread_eok * 5.0)
        + (technician_spread * 3.0),
        3,
    )
    return {
        "family_key": _safe_str(family.get("family_key")),
        "row_total": row_total,
        "with_other_row_total": with_other_row_total,
        "capital_spread_eok": capital_spread_eok,
        "technician_spread": technician_spread,
        "sample_service_codes": list(family.get("sample_service_codes") or []),
        "sample_service_names": list(family.get("sample_service_names") or []),
        "complexity_score": complexity_score,
    }


def build_packet(
    *,
    master_catalog: Dict[str, Any],
    focus_report: Dict[str, Any],
    runtime_case_assertions: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    rows = _focus_rows(master_catalog)
    focus_summary = _safe_dict(focus_report.get("summary"))
    guarded_core_only_service_codes = _guarded_core_only_service_codes(runtime_case_assertions)
    family_map: Dict[str, Dict[str, Any]] = {}
    capital_values: List[float] = []
    technician_values: List[int] = []
    capital_evidence_missing_total = 0
    technical_evidence_missing_total = 0
    other_evidence_missing_total = 0
    core_only_total = 0
    core_only_guarded_total = 0
    with_other_total = 0

    for row in rows:
        profile = _safe_dict(row.get("registration_requirement_profile"))
        family_key = _family_key(row)
        family = family_map.setdefault(
            family_key,
            {
                "family_key": family_key,
                "row_total": 0,
                "with_other_row_total": 0,
                "core_only_row_total": 0,
                "capital_evidence_missing_total": 0,
                "technical_evidence_missing_total": 0,
                "other_evidence_missing_total": 0,
                "capital_min_eok": None,
                "capital_max_eok": None,
                "technicians_min": None,
                "technicians_max": None,
                "sample_service_codes": [],
                "sample_service_names": [],
            },
        )
        family["row_total"] += 1

        capital_eok = _safe_float(profile.get("capital_eok"))
        technicians_required = int(profile.get("technicians_required") or 0)
        capital_required = bool(profile.get("capital_required"))
        technical_required = bool(profile.get("technical_personnel_required"))
        other_required = bool(profile.get("other_required"))
        capital_evidence = _safe_list(profile.get("capital_evidence"))
        technical_evidence = _safe_list(profile.get("technical_personnel_evidence"))
        other_evidence = _safe_list(profile.get("other_evidence"))

        if capital_required and technical_required:
            capital_values.append(capital_eok)
            technician_values.append(technicians_required)
            if other_required:
                with_other_total += 1
                family["with_other_row_total"] += 1
            else:
                core_only_total += 1
                family["core_only_row_total"] += 1
                if _safe_str(row.get("service_code")) in guarded_core_only_service_codes:
                    core_only_guarded_total += 1
            if not capital_evidence:
                capital_evidence_missing_total += 1
                family["capital_evidence_missing_total"] += 1
            if not technical_evidence:
                technical_evidence_missing_total += 1
                family["technical_evidence_missing_total"] += 1
            if other_required and not other_evidence:
                other_evidence_missing_total += 1
                family["other_evidence_missing_total"] += 1

        if capital_required:
            current_min = family["capital_min_eok"]
            current_max = family["capital_max_eok"]
            family["capital_min_eok"] = capital_eok if current_min is None else min(current_min, capital_eok)
            family["capital_max_eok"] = capital_eok if current_max is None else max(current_max, capital_eok)
        if technical_required:
            current_min = family["technicians_min"]
            current_max = family["technicians_max"]
            family["technicians_min"] = (
                technicians_required if current_min is None else min(current_min, technicians_required)
            )
            family["technicians_max"] = (
                technicians_required if current_max is None else max(current_max, technicians_required)
            )

        service_code = _safe_str(row.get("service_code"))
        service_name = _safe_str(row.get("service_name"))
        if service_code and service_code not in family["sample_service_codes"] and len(family["sample_service_codes"]) < 3:
            family["sample_service_codes"].append(service_code)
        if service_name and service_name not in family["sample_service_names"] and len(family["sample_service_names"]) < 3:
            family["sample_service_names"].append(service_name)

    family_gaps = sorted(
        family_map.values(),
        key=lambda item: (
            -(
                int(item.get("capital_evidence_missing_total", 0) or 0)
                + int(item.get("technical_evidence_missing_total", 0) or 0)
                + int(item.get("other_evidence_missing_total", 0) or 0)
            ),
            -int(item.get("row_total", 0) or 0),
            _safe_str(item.get("family_key")),
        ),
    )
    threshold_spread_families = [item for item in family_gaps if _has_threshold_spread(item)]
    threshold_spread_family_total = len(threshold_spread_families)
    threshold_spread_row_total = sum(int(item.get("row_total", 0) or 0) for item in threshold_spread_families)
    threshold_spread_priority = sorted(
        [_threshold_spread_priority_row(item) for item in threshold_spread_families],
        key=lambda item: (
            -float(item.get("complexity_score", 0.0) or 0.0),
            -int(item.get("row_total", 0) or 0),
            _safe_str(item.get("family_key")),
        ),
    )
    threshold_spread_top_service_code = ""
    if threshold_spread_priority:
        threshold_spread_top_service_code = _safe_str(
            (threshold_spread_priority[0].get("sample_service_codes") or [""])[0]
        )

    brainstorm_candidates: List[Dict[str, Any]] = []
    if capital_evidence_missing_total:
        brainstorm_candidates.append(
            _candidate(
                candidate_id="capital_evidence_backfill",
                title="capital evidence backfill",
                reason="Capital thresholds are present, but explicit capital-evidence lines are still missing.",
                affected_total=capital_evidence_missing_total,
                impact="Reduces wrong shortfall explanations and strengthens legal explainability at the same time.",
                next_action="Backfill capital-evidence lines from the raw registration-basis rows and lock them into the focus-family packet.",
            )
        )
    if technical_evidence_missing_total:
        brainstorm_candidates.append(
            _candidate(
                candidate_id="technical_evidence_backfill",
                title="technical evidence backfill",
                reason="Technician thresholds exist, but some rows still do not expose the underlying technician evidence.",
                affected_total=technical_evidence_missing_total,
                impact="Cuts operator verification time and lowers technician-shortfall explanation risk.",
                next_action="Backfill technician-evidence lines for the remaining focus rows and keep them visible in the runtime logic packet.",
            )
        )
    if other_evidence_missing_total:
        brainstorm_candidates.append(
            _candidate(
                candidate_id="other_requirement_evidence_backfill",
                title="other requirement evidence backfill",
                reason="Some focus rows still require extra checklist items without attached supporting evidence.",
                affected_total=other_evidence_missing_total,
                impact="Improves manual-review branching quality and reduces document-missing false positives.",
                next_action="Trace the remaining extra requirement rows and attach the raw-source evidence for equipment, deposit, or facility requirements.",
            )
        )
    unresolved_core_only_total = max(0, core_only_total - core_only_guarded_total)
    if unresolved_core_only_total:
        brainstorm_candidates.append(
            _candidate(
                candidate_id="core_only_boundary_guard",
                title="core-only boundary guard",
                reason="One focus row is capital+technician only and should not inherit the heavier with-other checklist path.",
                affected_total=unresolved_core_only_total,
                impact="Prevents over-restrictive results and makes the core-only branch more trustworthy.",
                next_action="Add a dedicated boundary assertion for the core-only focus row and keep its checklist path separate from with-other families.",
            )
        )
    if (
        capital_evidence_missing_total == 0
        and technical_evidence_missing_total == 0
        and other_evidence_missing_total == 0
        and threshold_spread_family_total > 0
    ):
        brainstorm_candidates.append(
            _candidate(
                candidate_id="family_threshold_formula_guard",
                title="family threshold formula guard",
                reason="Several focus families contain multiple subtypes with different capital or technician thresholds, so a single simplified family explanation can drift even when evidence lines exist.",
                affected_total=threshold_spread_row_total,
                impact="Reduces wrong boundary verdicts and keeps subtype-specific capital/technician math explainable in the runtime reasoning surface.",
                next_action=(
                    "Promote subtype-aware threshold guard rows for the spread families and bind the representative boundary scenarios into the capital-registration logic packet."
                    + (
                        f" Start with {threshold_spread_top_service_code}."
                        if threshold_spread_top_service_code
                        else ""
                    )
                ),
            )
        )

    primary_gap_id = ""
    primary_gap_total = 0
    if brainstorm_candidates:
        primary = max(brainstorm_candidates, key=lambda item: int(item.get("affected_total", 0) or 0))
        primary_gap_id = _safe_str(primary.get("candidate_id"))
        primary_gap_total = int(primary.get("affected_total", 0) or 0)

    packet_ready = bool(rows)
    summary = {
        "packet_ready": packet_ready,
        "focus_target_total": int(focus_summary.get("focus_target_total", len(rows)) or len(rows)),
        "real_focus_target_total": int(focus_summary.get("real_focus_target_total", len(rows)) or len(rows)),
        "family_total": len(family_gaps),
        "capital_technical_focus_total": len(rows),
        "with_other_total": with_other_total,
        "core_only_total": core_only_total,
        "core_only_guarded_total": core_only_guarded_total,
        "capital_evidence_missing_total": capital_evidence_missing_total,
        "technical_evidence_missing_total": technical_evidence_missing_total,
        "other_evidence_missing_total": other_evidence_missing_total,
        "capital_min_eok": min(capital_values) if capital_values else 0.0,
        "capital_max_eok": max(capital_values) if capital_values else 0.0,
        "technicians_min": min(technician_values) if technician_values else 0,
        "technicians_max": max(technician_values) if technician_values else 0,
        "threshold_spread_family_total": threshold_spread_family_total,
        "threshold_spread_row_total": threshold_spread_row_total,
        "threshold_spread_priority_family_total": len(threshold_spread_priority),
        "threshold_spread_top_service_code": threshold_spread_top_service_code,
        "brainstorm_candidate_total": len(brainstorm_candidates),
        "primary_gap_id": primary_gap_id,
        "primary_gap_total": primary_gap_total,
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "family_gaps": family_gaps,
        "threshold_spread_priority": threshold_spread_priority,
        "brainstorm_candidates": brainstorm_candidates,
        "source_paths": {
            "master_catalog": str(DEFAULT_MASTER_INPUT.resolve()),
            "focus_report": str(DEFAULT_FOCUS_INPUT.resolve()),
            "runtime_case_assertions": str(DEFAULT_RUNTIME_ASSERTIONS_INPUT.resolve()),
        },
    }


def render_markdown(packet: Dict[str, Any]) -> str:
    summary = _safe_dict(packet.get("summary"))
    lines = [
        "# Permit Capital Registration Logic Packet",
        "",
        "## Summary",
        f"- packet_ready: `{summary.get('packet_ready', False)}`",
        f"- focus_target_total: `{summary.get('focus_target_total', 0)}`",
        f"- family_total: `{summary.get('family_total', 0)}`",
        f"- capital_technical_focus_total: `{summary.get('capital_technical_focus_total', 0)}`",
        f"- with_other_total: `{summary.get('with_other_total', 0)}`",
        f"- core_only_total: `{summary.get('core_only_total', 0)}`",
        f"- core_only_guarded_total: `{summary.get('core_only_guarded_total', 0)}`",
        f"- capital_evidence_missing_total: `{summary.get('capital_evidence_missing_total', 0)}`",
        f"- technical_evidence_missing_total: `{summary.get('technical_evidence_missing_total', 0)}`",
        f"- other_evidence_missing_total: `{summary.get('other_evidence_missing_total', 0)}`",
        f"- capital_min_eok: `{summary.get('capital_min_eok', 0)}`",
        f"- capital_max_eok: `{summary.get('capital_max_eok', 0)}`",
        f"- technicians_min: `{summary.get('technicians_min', 0)}`",
        f"- technicians_max: `{summary.get('technicians_max', 0)}`",
        f"- threshold_spread_family_total: `{summary.get('threshold_spread_family_total', 0)}`",
        f"- threshold_spread_row_total: `{summary.get('threshold_spread_row_total', 0)}`",
        f"- threshold_spread_top_service_code: `{summary.get('threshold_spread_top_service_code', '')}`",
        f"- primary_gap_id: `{summary.get('primary_gap_id', '')}`",
        f"- primary_gap_total: `{summary.get('primary_gap_total', 0)}`",
        "",
        "## Family Gaps",
    ]
    for row in _safe_list(packet.get("family_gaps")):
        item = _safe_dict(row)
        lines.append(
            f"- `{item.get('family_key', '')}` / rows={item.get('row_total', 0)}"
            f" / capital_missing={item.get('capital_evidence_missing_total', 0)}"
            f" / technical_missing={item.get('technical_evidence_missing_total', 0)}"
            f" / other_missing={item.get('other_evidence_missing_total', 0)}"
            f" / capital_range={item.get('capital_min_eok', 0)}-{item.get('capital_max_eok', 0)}"
            f" / technicians_range={item.get('technicians_min', 0)}-{item.get('technicians_max', 0)}"
        )
    lines.extend(["", "## Threshold Spread Priority"])
    for row in _safe_list(packet.get("threshold_spread_priority")):
        item = _safe_dict(row)
        lines.append(
            f"- `{item.get('family_key', '')}` / score={item.get('complexity_score', 0)}"
            f" / rows={item.get('row_total', 0)}"
            f" / with_other_rows={item.get('with_other_row_total', 0)}"
            f" / capital_spread={item.get('capital_spread_eok', 0)}"
            f" / technician_spread={item.get('technician_spread', 0)}"
            f" / top_service={(item.get('sample_service_codes') or [''])[0]}"
        )
    lines.extend(["", "## Brainstorm Candidates"])
    for row in _safe_list(packet.get("brainstorm_candidates")):
        item = _safe_dict(row)
        lines.append(
            f"- `{item.get('candidate_id', '')}` / affected={item.get('affected_total', 0)}"
            f" / {item.get('reason', '')}"
            f" / next {item.get('next_action', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the permit capital-registration logic packet.")
    parser.add_argument("--master-input", type=Path, default=DEFAULT_MASTER_INPUT)
    parser.add_argument("--focus-input", type=Path, default=DEFAULT_FOCUS_INPUT)
    parser.add_argument("--runtime-case-assertions-input", type=Path, default=DEFAULT_RUNTIME_ASSERTIONS_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    packet = build_packet(
        master_catalog=_load_json(args.master_input.resolve()),
        focus_report=_load_json(args.focus_input.resolve()),
        runtime_case_assertions=_load_json(args.runtime_case_assertions_input.resolve()),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "json": str(args.json_output.resolve()), "md": str(args.md_output.resolve())},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if bool(_safe_dict(packet.get("summary")).get("packet_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
