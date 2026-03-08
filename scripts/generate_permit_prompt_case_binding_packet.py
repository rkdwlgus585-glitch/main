#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRAINSTORM = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_FOUNDER = ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"
DEFAULT_PRESETS = ROOT / "logs" / "permit_review_case_presets_latest.json"
DEFAULT_STORIES = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_OPERATOR_DEMO = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_prompt_case_binding_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_prompt_case_binding_packet_latest.md"


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


def _string_list(value: Any) -> List[str]:
    out: List[str] = []
    for item in _safe_list(value):
        text = _safe_str(item)
        if text and text not in out:
            out.append(text)
    return out


def _question_bindings(founder_questions: List[str]) -> List[Dict[str, Any]]:
    defaults = [
        {
            "question_id": "input_and_operator_time",
            "binding_strategy": "Use one-click review presets and operator demo cases instead of manual field assembly.",
            "case_kinds": ["capital_only_fail", "technician_only_fail", "document_missing_review"],
            "surface_targets": [
                "permit_review_case_presets",
                "permit_operator_demo_packet",
                "permit_case_story_surface",
            ],
        },
        {
            "question_id": "legal_checklist_manual_review",
            "binding_strategy": "Keep legal basis, checklist exposure, and manual-review branching visible on the same family case.",
            "case_kinds": ["document_missing_review"],
            "surface_targets": [
                "permit_case_story_surface",
                "permit_operator_demo_packet",
            ],
        },
        {
            "question_id": "verify_with_runtime_assets",
            "binding_strategy": "Prefer representative cases that already carry demo steps and expected statuses.",
            "case_kinds": ["capital_only_fail", "technician_only_fail", "document_missing_review"],
            "surface_targets": [
                "permit_operator_demo_packet",
            ],
        },
    ]
    bindings: List[Dict[str, Any]] = []
    for index, question in enumerate(founder_questions):
        template = defaults[min(index, len(defaults) - 1)]
        bindings.append(
            {
                "question": question,
                **template,
            }
        )
    if not bindings:
        bindings = defaults
    return bindings


def build_packet(
    *,
    brainstorm_path: Path,
    founder_path: Path,
    presets_path: Path,
    stories_path: Path,
    operator_demo_path: Path,
) -> Dict[str, Any]:
    brainstorm = _load_json(brainstorm_path)
    founder = _load_json(founder_path)
    presets = _load_json(presets_path)
    stories = _load_json(stories_path)
    operator_demo = _load_json(operator_demo_path)

    brainstorm_summary = _safe_dict(brainstorm.get("summary"))
    current_lane = _safe_dict(brainstorm.get("current_execution_lane"))
    critical_prompts = _safe_dict(brainstorm.get("critical_prompts"))
    founder_summary = _safe_dict(founder.get("summary"))
    presets_summary = _safe_dict(presets.get("summary"))
    stories_summary = _safe_dict(stories.get("summary"))
    operator_demo_summary = _safe_dict(operator_demo.get("summary"))

    founder_primary_system = _safe_str(founder_summary.get("primary_system"))
    founder_primary_lane_id = _safe_str(founder_summary.get("primary_lane_id"))
    current_execution_lane_id = _safe_str(current_lane.get("id"))
    current_execution_lane_title = _safe_str(current_lane.get("title"))
    founder_is_permit = founder_primary_system == "permit"
    lane_id = (
        founder_primary_lane_id
        if founder_is_permit and founder_primary_lane_id
        else (current_execution_lane_id or "prompt_case_binding")
    )
    founder_lane_match = (
        founder_primary_lane_id == lane_id
        if founder_is_permit and founder_primary_lane_id
        else True
    )
    prompt_doc_ready = bool(brainstorm_summary.get("prompt_doc_ready"))
    preset_ready = bool(presets_summary.get("preset_ready"))
    story_ready = bool(stories_summary.get("story_ready"))
    operator_demo_ready = bool(operator_demo_summary.get("operator_demo_ready"))

    jump_table: List[Dict[str, Any]] = []
    story_families = {
        _safe_str(row.get("claim_id")): _safe_dict(row)
        for row in _safe_list(stories.get("families"))
        if _safe_str(_safe_dict(row).get("claim_id"))
    }
    for family in _safe_list(operator_demo.get("families")):
        row = _safe_dict(family)
        claim_id = _safe_str(row.get("claim_id"))
        story_row = story_families.get(claim_id, {})
        representative_cases = {
            _safe_str(_safe_dict(case).get("case_kind")): _safe_dict(case)
            for case in _safe_list(story_row.get("representative_cases"))
            if _safe_str(_safe_dict(case).get("case_kind"))
        }
        jump_targets: List[Dict[str, Any]] = []
        for demo_case in _safe_list(row.get("demo_cases")):
            case = _safe_dict(demo_case)
            case_kind = _safe_str(case.get("case_kind"))
            representative = representative_cases.get(case_kind, {})
            jump_targets.append(
                {
                    "case_kind": case_kind,
                    "preset_id": _safe_str(case.get("preset_id")),
                    "service_code": _safe_str(case.get("service_code") or representative.get("service_code")),
                    "expected_status": _safe_str(case.get("expected_status") or representative.get("expected_status")),
                    "review_reason": _safe_str(case.get("review_reason") or representative.get("review_reason")),
                    "manual_review_expected": bool(
                        case.get("manual_review_expected")
                        if "manual_review_expected" in case
                        else representative.get("manual_review_expected")
                    ),
                }
            )
        jump_table.append(
            {
                "family_key": _safe_str(row.get("family_key")),
                "claim_id": claim_id,
                "service_family_demo_count": len(jump_targets),
                "jump_targets": jump_targets,
            }
        )

    question_bindings = _question_bindings(_string_list(critical_prompts.get("founder_mode_questions")))
    representative_family_total = len(jump_table)
    representative_case_total = sum(len(_safe_list(row.get("jump_targets"))) for row in jump_table)
    manual_review_case_total = sum(
        1
        for row in jump_table
        for case in _safe_list(_safe_dict(row).get("jump_targets"))
        if bool(_safe_dict(case).get("manual_review_expected"))
    )
    operator_jump_table_ready = representative_family_total > 0 and representative_case_total > 0
    packet_ready = (
        prompt_doc_ready
        and preset_ready
        and story_ready
        and operator_demo_ready
        and operator_jump_table_ready
        and founder_lane_match
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_prompt_case_binding_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "lane_id": lane_id,
            "founder_primary_system": founder_primary_system,
            "founder_primary_lane_id": founder_primary_lane_id,
            "current_execution_lane_id": current_execution_lane_id,
            "current_execution_lane_title": current_execution_lane_title,
            "current_execution_lane_matches_packet": current_execution_lane_id == lane_id,
            "founder_lane_match": founder_lane_match,
            "prompt_doc_ready": prompt_doc_ready,
            "preset_ready": preset_ready,
            "story_ready": story_ready,
            "operator_demo_ready": operator_demo_ready,
            "operator_jump_table_ready": operator_jump_table_ready,
            "representative_family_total": representative_family_total,
            "representative_case_total": representative_case_total,
            "manual_review_case_total": manual_review_case_total,
        },
        "source_paths": {
            "brainstorm": str(brainstorm_path.resolve()),
            "founder": str(founder_path.resolve()),
            "presets": str(presets_path.resolve()),
            "stories": str(stories_path.resolve()),
            "operator_demo": str(operator_demo_path.resolve()),
        },
        "question_bindings": question_bindings,
        "operator_jump_table": jump_table,
        "next_actions": [
            "Keep founder questions mapped to representative permit presets instead of free-form operator interpretation.",
            "Use the operator jump table when editing permit service copy, release notes, and operator runbooks.",
            "Do not mark the permit founder lane complete unless the jump table remains synchronized with presets and story surfaces.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    lines = [
        "# Permit Prompt Case Binding Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- lane_id: {summary.get('lane_id')}",
        f"- founder_primary_lane_id: {summary.get('founder_primary_lane_id')}",
        f"- current_execution_lane_id: {summary.get('current_execution_lane_id')}",
        f"- founder_lane_match: {summary.get('founder_lane_match')}",
        f"- prompt_doc_ready: {summary.get('prompt_doc_ready')}",
        f"- preset_ready: {summary.get('preset_ready')}",
        f"- story_ready: {summary.get('story_ready')}",
        f"- operator_demo_ready: {summary.get('operator_demo_ready')}",
        f"- operator_jump_table_ready: {summary.get('operator_jump_table_ready')}",
        f"- representative_family_total: {summary.get('representative_family_total')}",
        f"- representative_case_total: {summary.get('representative_case_total')}",
        "",
        "## Founder Question Bindings",
    ]
    for row in _safe_list(payload.get("question_bindings")):
        binding = _safe_dict(row)
        lines.append(
            f"- {binding.get('question')} -> {', '.join(_string_list(binding.get('case_kinds')))}"
        )
    lines.extend(["", "## Operator Jump Table"])
    for row in _safe_list(payload.get("operator_jump_table")):
        item = _safe_dict(row)
        lines.append(
            f"- {item.get('claim_id')}: {len(_safe_list(item.get('jump_targets')))} jump targets"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the canonical permit prompt-case binding packet.")
    parser.add_argument("--brainstorm", type=Path, default=DEFAULT_BRAINSTORM)
    parser.add_argument("--founder", type=Path, default=DEFAULT_FOUNDER)
    parser.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    parser.add_argument("--stories", type=Path, default=DEFAULT_STORIES)
    parser.add_argument("--operator-demo", type=Path, default=DEFAULT_OPERATOR_DEMO)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        brainstorm_path=args.brainstorm,
        founder_path=args.founder,
        presets_path=args.presets,
        stories_path=args.stories,
        operator_demo_path=args.operator_demo,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool(_safe_dict(payload.get("summary")).get("packet_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
