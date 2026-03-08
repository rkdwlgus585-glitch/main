#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_permit_law_case_coverage_packet(
    *,
    expanded_criteria_path: Path,
    provenance_audit_path: Path,
    focus_family_registry_path: Path,
    family_case_goldset_path: Path,
    review_case_presets_path: Path,
    case_story_surface_path: Path,
    prompt_case_binding_path: Path,
) -> Dict[str, Any]:
    expanded = _load_json(expanded_criteria_path)
    provenance = _load_json(provenance_audit_path)
    family_registry = _load_json(focus_family_registry_path)
    goldset = _load_json(family_case_goldset_path)
    presets = _load_json(review_case_presets_path)
    case_story = _load_json(case_story_surface_path)
    prompt_binding = _load_json(prompt_case_binding_path)

    expanded_summary = expanded.get("summary") if isinstance(expanded.get("summary"), dict) else {}
    requirement_focus = expanded.get("requirement_focus_summary") if isinstance(expanded.get("requirement_focus_summary"), dict) else {}
    quality_audit = expanded.get("quality_audit") if isinstance(expanded.get("quality_audit"), dict) else {}
    provenance_summary = provenance.get("summary") if isinstance(provenance.get("summary"), dict) else {}
    family_summary = family_registry.get("summary") if isinstance(family_registry.get("summary"), dict) else {}
    goldset_summary = goldset.get("summary") if isinstance(goldset.get("summary"), dict) else {}
    presets_summary = presets.get("summary") if isinstance(presets.get("summary"), dict) else {}
    case_story_summary = case_story.get("summary") if isinstance(case_story.get("summary"), dict) else {}
    prompt_binding_summary = prompt_binding.get("summary") if isinstance(prompt_binding.get("summary"), dict) else {}

    real_industry_total = int(expanded_summary.get("real_industry_total", 0) or 0)
    real_with_basis_total = int(expanded_summary.get("real_with_legal_basis_total", 0) or 0)
    real_with_criteria_total = int(expanded_summary.get("real_with_registration_criteria_total", 0) or 0)
    pending_industry_total = int(expanded_summary.get("pending_industry_total", 0) or 0)
    manual_scope_override_total = int(quality_audit.get("manual_scope_override_total", 0) or 0)
    family_total = int(goldset_summary.get("family_total", 0) or 0)
    case_total = int(goldset_summary.get("case_total", 0) or 0)
    manual_review_case_total = int(goldset_summary.get("manual_review_case_total", 0) or 0)

    law_basis_coverage_ok = real_industry_total > 0 and real_with_basis_total >= real_industry_total
    criteria_coverage_ok = real_industry_total > 0 and real_with_criteria_total >= real_industry_total
    provenance_ok = int(provenance_summary.get("rows_missing_legal_basis_total", 0) or 0) == 0
    exception_tracking_ready = manual_scope_override_total >= 1
    case_goldset_ready = bool(goldset_summary.get("goldset_ready"))
    story_surface_ready = bool(case_story_summary.get("story_ready"))
    prompt_binding_ready = bool(prompt_binding_summary.get("packet_ready"))

    blockers = []
    if not law_basis_coverage_ok:
        blockers.append("permit_legal_basis_coverage_incomplete")
    if not criteria_coverage_ok:
        blockers.append("permit_registration_criteria_incomplete")
    if not provenance_ok:
        blockers.append("permit_provenance_missing_legal_basis")
    if not exception_tracking_ready:
        blockers.append("permit_exception_tracking_missing")
    if not case_goldset_ready:
        blockers.append("permit_case_goldset_not_ready")
    if not story_surface_ready:
        blockers.append("permit_case_story_surface_not_ready")
    if not prompt_binding_ready:
        blockers.append("permit_prompt_case_binding_not_ready")

    next_actions = []
    if pending_industry_total:
        next_actions.append("Expand pending permit industries into law-linked criteria packs until pending_industry_total trends to zero.")
    if not exception_tracking_ready:
        next_actions.append("Add more permit exception and manual-scope override cases into the family registry.")
    if not case_goldset_ready or not story_surface_ready:
        next_actions.append("Keep permit family goldset, case presets, and story surface in lockstep for operator and patent evidence reuse.")

    summary = {
        "packet_ready": True,
        "law_basis_coverage_ok": law_basis_coverage_ok,
        "criteria_coverage_ok": criteria_coverage_ok,
        "provenance_ok": provenance_ok,
        "exception_tracking_ready": exception_tracking_ready,
        "case_goldset_ready": case_goldset_ready,
        "story_surface_ready": story_surface_ready,
        "prompt_binding_ready": prompt_binding_ready,
        "real_industry_total": real_industry_total,
        "real_with_legal_basis_total": real_with_basis_total,
        "real_with_registration_criteria_total": real_with_criteria_total,
        "pending_industry_total": pending_industry_total,
        "manual_scope_override_total": manual_scope_override_total,
        "family_total": family_total,
        "case_total": case_total,
        "manual_review_case_total": manual_review_case_total,
        "rule_pack_total": int(expanded_summary.get("rule_pack_total", 0) or 0),
        "rows_with_raw_source_proof_total": int(provenance_summary.get("rows_with_raw_source_proof_total", 0) or 0),
        "focus_family_registry_row_total": int(family_summary.get("family_registry_row_total", 0) or 0),
        "capital_and_technical_with_other_total": int(requirement_focus.get("capital_and_technical_with_other_total", 0) or 0),
        "blocker_count": len(blockers),
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "quality": {
            "expanded_criteria_summary": expanded_summary,
            "requirement_focus_summary": requirement_focus,
            "quality_audit": quality_audit,
            "provenance_summary": provenance_summary,
        },
        "case_surface": {
            "family_registry_summary": family_summary,
            "goldset_summary": goldset_summary,
            "review_case_presets_summary": presets_summary,
            "case_story_surface_summary": case_story_summary,
            "prompt_case_binding_summary": prompt_binding_summary,
        },
        "blockers": blockers,
        "next_actions": next_actions,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Permit Law Case Coverage Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- law_basis_coverage_ok: {summary.get('law_basis_coverage_ok')}",
        f"- criteria_coverage_ok: {summary.get('criteria_coverage_ok')}",
        f"- provenance_ok: {summary.get('provenance_ok')}",
        f"- exception_tracking_ready: {summary.get('exception_tracking_ready')}",
        f"- case_goldset_ready: {summary.get('case_goldset_ready')}",
        f"- story_surface_ready: {summary.get('story_surface_ready')}",
        f"- prompt_binding_ready: {summary.get('prompt_binding_ready')}",
        f"- real_industry_total: {summary.get('real_industry_total')}",
        f"- pending_industry_total: {summary.get('pending_industry_total')}",
        f"- manual_scope_override_total: {summary.get('manual_scope_override_total')}",
        f"- family_total: {summary.get('family_total')}",
        f"- case_total: {summary.get('case_total')}",
        f"- blocker_count: {summary.get('blocker_count')}",
        "",
        "## Blockers",
    ]
    for item in payload.get("blockers") or []:
        lines.append(f"- {item}")
    if not payload.get("blockers"):
        lines.append("- (none)")
    lines.append("")
    lines.append("## Next Actions")
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    if not payload.get("next_actions"):
        lines.append("- (none)")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize permit law/exception/case coverage for the AI permit system.")
    parser.add_argument("--expanded-criteria", type=Path, default=ROOT / "config" / "permit_registration_criteria_expanded.json")
    parser.add_argument("--provenance-audit", type=Path, default=ROOT / "logs" / "permit_provenance_audit_latest.json")
    parser.add_argument("--focus-family-registry", type=Path, default=ROOT / "logs" / "permit_focus_family_registry_latest.json")
    parser.add_argument("--family-case-goldset", type=Path, default=ROOT / "logs" / "permit_family_case_goldset_latest.json")
    parser.add_argument("--review-case-presets", type=Path, default=ROOT / "logs" / "permit_review_case_presets_latest.json")
    parser.add_argument("--case-story-surface", type=Path, default=ROOT / "logs" / "permit_case_story_surface_latest.json")
    parser.add_argument("--prompt-case-binding", type=Path, default=ROOT / "logs" / "permit_prompt_case_binding_packet_latest.json")
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "permit_law_case_coverage_packet_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "permit_law_case_coverage_packet_latest.md")
    args = parser.parse_args()

    payload = build_permit_law_case_coverage_packet(
        expanded_criteria_path=args.expanded_criteria,
        provenance_audit_path=args.provenance_audit,
        focus_family_registry_path=args.focus_family_registry,
        family_case_goldset_path=args.family_case_goldset,
        review_case_presets_path=args.review_case_presets,
        case_story_surface_path=args.case_story_surface,
        prompt_case_binding_path=args.prompt_case_binding,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md), "blocker_count": payload.get("summary", {}).get("blocker_count")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
