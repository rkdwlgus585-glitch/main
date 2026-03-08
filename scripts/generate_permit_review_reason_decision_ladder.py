#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_STORY_SURFACE_INPUT = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_OPERATOR_DEMO_PACKET_INPUT = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_review_reason_decision_ladder_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_review_reason_decision_ladder_latest.md"


REASON_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "capital_and_technician_shortfall": {
        "label": "자본금·기술인력 동시 부족",
        "decision_priority": 1,
        "inspect_first": "자본금과 기술인력 핵심 입력값 및 증빙",
        "evidence_first": ["capital_eok", "capital_proof", "technicians_count", "technician_certificates"],
        "missing_input_focus": ["capital_eok", "technicians_count"],
        "operator_question": "두 핵심 요건이 모두 기준 미달인지 먼저 고정했는가.",
        "next_action": "자본금과 기술인력 보완 전에는 shortfall로 고정하고 두 증빙을 동시에 다시 요청한다.",
        "manual_review_gate": False,
    },
    "capital_shortfall_only": {
        "label": "자본금 부족",
        "decision_priority": 2,
        "inspect_first": "자본금 입력값과 자본금 증빙",
        "evidence_first": ["capital_eok", "capital_proof"],
        "missing_input_focus": ["capital_eok"],
        "operator_question": "법령 기준 자본금에 못 미치는지 먼저 고정했는가.",
        "next_action": "자본금 보완 전에는 shortfall로 고정하고 보완 증빙을 다시 요청한다.",
        "manual_review_gate": False,
    },
    "technician_shortfall_only": {
        "label": "기술인력 부족",
        "decision_priority": 3,
        "inspect_first": "기술인력 수와 자격 증빙",
        "evidence_first": ["technicians_count", "technician_certificates"],
        "missing_input_focus": ["technicians_count"],
        "operator_question": "기술인력 요건을 충족하지 못하는지 먼저 고정했는가.",
        "next_action": "기술인력 보완 전에는 shortfall로 고정하고 자격 증빙 재제출을 요청한다.",
        "manual_review_gate": False,
    },
    "other_requirement_documents_missing": {
        "label": "기타 요건 서류 누락",
        "decision_priority": 0,
        "inspect_first": "누락 서류와 수동검토 필요 여부",
        "evidence_first": ["document_ready", "other_requirement_documents"],
        "missing_input_focus": ["document_ready"],
        "operator_question": "자동판단을 멈추고 수동검토로 넘길 문서 공백인지 먼저 확인했는가.",
        "next_action": "누락 서류를 우선 요청하고, 판단보류 또는 manual review로 넘긴다.",
        "manual_review_gate": True,
    },
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("review reason decision ladder input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _binding_focus(reason: str, manual_review_expected: bool) -> str:
    if manual_review_expected:
        return "manual_review_gate"
    if reason == "capital_and_technician_shortfall":
        return "capital_and_technician_gap_first"
    if reason == "capital_shortfall_only":
        return "capital_gap_first"
    if reason == "technician_shortfall_only":
        return "technician_gap_first"
    if reason:
        return "review_reason_first"
    return "baseline_reference"


def _binding_question(reason: str, manual_review_expected: bool) -> str:
    if manual_review_expected or reason == "other_requirement_documents_missing":
        return "?대뵒???먮룞?먮떒??硫덉텛怨??섎룞寃?좊줈 ?섍꺼???섎뒗媛."
    if reason == "capital_and_technician_shortfall":
        return "?먮낯湲덇낵 湲곗닠?몃젰??????遺議깊븳吏 癒쇱? 怨좎젙?덈뒗媛."
    if reason == "capital_shortfall_only":
        return "踰뺣졊 湲곗? ?먮낯湲덉뿉 紐?誘몄튂?붿? 癒쇱? 怨좎젙?덈뒗媛."
    if reason == "technician_shortfall_only":
        return "湲곗닠?몃젰 ?붽굔??異⑹”?섏? 紐삵븯?붿? 癒쇱? 怨좎젙?덈뒗媛."
    if reason:
        return "踰뺣졊 洹쇨굅, 泥댄겕由ъ뒪?? ?섎룞寃??以??대뵒??癒쇱? 遺꾧린?섎뒗媛."
    return "??耳?댁뒪瑜?湲곗??먯쑝濡??????대뼡 ?낅젰???뺣쭚 ?꾩닔?멸?."


def _reason_meta(reason: str, manual_review_expected: bool) -> Dict[str, Any]:
    default = {
        "label": reason or "unknown_review_reason",
        "decision_priority": 9,
        "inspect_first": "핵심 누락 입력과 법령 기준",
        "evidence_first": ["core_inputs", "legal_basis"],
        "missing_input_focus": ["core_inputs"],
        "operator_question": "어떤 핵심 입력이 비어 있는지 먼저 고정했는가.",
        "next_action": "누락 입력을 보완 요청하고 결과 상태를 다시 계산한다.",
        "manual_review_gate": manual_review_expected,
    }
    template = dict(REASON_TEMPLATES.get(reason) or {})
    if not template:
        return default
    template["manual_review_gate"] = bool(template.get("manual_review_gate", False) or manual_review_expected)
    return {**default, **template}


def build_report(
    *,
    permit_case_story_surface: Dict[str, Any],
    permit_operator_demo_packet: Dict[str, Any],
) -> Dict[str, Any]:
    story_families = {
        _safe_str(row.get("claim_id")): row
        for row in _safe_list(permit_case_story_surface.get("families"))
        if isinstance(row, dict) and _safe_str(row.get("claim_id"))
    }
    reason_rows: Dict[str, Dict[str, Any]] = {}

    for family in [row for row in _safe_list(permit_operator_demo_packet.get("families")) if isinstance(row, dict)]:
        claim_id = _safe_str(family.get("claim_id"))
        family_key = _safe_str(family.get("family_key"))
        prompt_binding = family.get("prompt_case_binding") if isinstance(family.get("prompt_case_binding"), dict) else {}
        story_family = story_families.get(claim_id, {})
        representative_preset_ids = [
            _safe_str(case.get("preset_id"))
            for case in _safe_list(story_family.get("representative_cases"))
            if isinstance(case, dict) and _safe_str(case.get("preset_id"))
        ]

        for case in [row for row in _safe_list(family.get("demo_cases")) if isinstance(row, dict)]:
            reason = _safe_str(case.get("review_reason"))
            if not reason:
                continue
            service_name = _safe_str(case.get("service_name") or case.get("service_code"))
            expected_status = _safe_str(case.get("expected_status"))
            manual_review_expected = bool(case.get("manual_review_expected", False))
            meta = _reason_meta(reason, manual_review_expected)
            row = reason_rows.setdefault(
                reason,
                {
                    "review_reason": reason,
                    "review_reason_label": meta["label"],
                    "decision_priority": int(meta["decision_priority"]),
                    "inspect_first": _safe_str(meta["inspect_first"]),
                    "evidence_first": [item for item in _safe_list(meta["evidence_first"]) if _safe_str(item)],
                    "missing_input_focus": [item for item in _safe_list(meta["missing_input_focus"]) if _safe_str(item)],
                    "operator_question": _safe_str(meta["operator_question"]),
                    "next_action": _safe_str(meta["next_action"]),
                    "manual_review_gate": bool(meta["manual_review_gate"]),
                    "family_keys": [],
                    "claim_ids": [],
                    "representative_services": [],
                    "expected_statuses": [],
                    "representative_preset_ids": [],
                    "binding_preset_ids": [],
                    "binding_focuses": [],
                    "binding_questions": [],
                },
            )
            if family_key and family_key not in row["family_keys"]:
                row["family_keys"].append(family_key)
            if claim_id and claim_id not in row["claim_ids"]:
                row["claim_ids"].append(claim_id)
            if service_name and service_name not in row["representative_services"]:
                row["representative_services"].append(service_name)
            if expected_status and expected_status not in row["expected_statuses"]:
                row["expected_statuses"].append(expected_status)
            preset_id = _safe_str(case.get("preset_id"))
            if preset_id and preset_id not in row["representative_preset_ids"]:
                row["representative_preset_ids"].append(preset_id)
            if preset_id and preset_id not in row["binding_preset_ids"]:
                row["binding_preset_ids"].append(preset_id)
            derived_focus = _binding_focus(reason, manual_review_expected)
            derived_question = _binding_question(reason, manual_review_expected)
            if derived_focus and derived_focus not in row["binding_focuses"]:
                row["binding_focuses"].append(derived_focus)
            if derived_question and derived_question not in row["binding_questions"]:
                row["binding_questions"].append(derived_question)
            for preset_id in representative_preset_ids:
                if preset_id and preset_id not in row["representative_preset_ids"]:
                    row["representative_preset_ids"].append(preset_id)
            if _safe_str(prompt_binding.get("review_reason")) == reason:
                binding_preset_id = _safe_str(prompt_binding.get("preset_id"))
                binding_focus = _safe_str(prompt_binding.get("binding_focus"))
                binding_question = _safe_str(prompt_binding.get("binding_question"))
                if binding_preset_id and binding_preset_id not in row["binding_preset_ids"]:
                    row["binding_preset_ids"].append(binding_preset_id)
                if binding_focus and binding_focus not in row["binding_focuses"]:
                    row["binding_focuses"].append(binding_focus)
                if binding_question and binding_question not in row["binding_questions"]:
                    row["binding_questions"].append(binding_question)

    ladders = sorted(reason_rows.values(), key=lambda item: (int(item.get("decision_priority", 9)), _safe_str(item.get("review_reason"))))
    manual_review_gate_total = sum(1 for item in ladders if bool(item.get("manual_review_gate")))
    prompt_bound_reason_total = sum(1 for item in ladders if _safe_list(item.get("binding_preset_ids")))
    summary = {
        "review_reason_total": len(ladders),
        "manual_review_gate_total": manual_review_gate_total,
        "prompt_bound_reason_total": prompt_bound_reason_total,
        "story_family_total": int((permit_case_story_surface.get("summary") or {}).get("story_family_total", 0) or 0),
        "operator_demo_family_total": int((permit_operator_demo_packet.get("summary") or {}).get("family_total", 0) or 0),
        "decision_ladder_ready": bool(ladders) and all(_safe_str(item.get("next_action")) for item in ladders),
        "execution_lane_id": "review_reason_decision_ladder",
        "parallel_lane_id": "thinking_prompt_bundle_lock",
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "source_paths": {
            "permit_case_story_surface": str(DEFAULT_CASE_STORY_SURFACE_INPUT.resolve()),
            "permit_operator_demo_packet": str(DEFAULT_OPERATOR_DEMO_PACKET_INPUT.resolve()),
        },
        "ladders": ladders,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Review Reason Decision Ladder",
        "",
        "## Summary",
        f"- review_reason_total: `{summary.get('review_reason_total', 0)}`",
        f"- manual_review_gate_total: `{summary.get('manual_review_gate_total', 0)}`",
        f"- prompt_bound_reason_total: `{summary.get('prompt_bound_reason_total', 0)}`",
        f"- story_family_total: `{summary.get('story_family_total', 0)}`",
        f"- operator_demo_family_total: `{summary.get('operator_demo_family_total', 0)}`",
        f"- decision_ladder_ready: `{summary.get('decision_ladder_ready', False)}`",
        f"- execution_lane_id: `{summary.get('execution_lane_id', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        "",
        "## Ladders",
    ]
    for row in [item for item in _safe_list(report.get("ladders")) if isinstance(item, dict)]:
        lines.extend(
            [
                f"- `{row.get('review_reason', '')}` / inspect `{row.get('inspect_first', '')}` / next `{row.get('next_action', '')}`",
                f"  families={len(_safe_list(row.get('family_keys')))} services={', '.join(str(item) for item in _safe_list(row.get('representative_services'))[:3])}",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact decision ladder for permit review reasons.")
    parser.add_argument("--case-story-surface-input", default=str(DEFAULT_CASE_STORY_SURFACE_INPUT))
    parser.add_argument("--operator-demo-packet-input", default=str(DEFAULT_OPERATOR_DEMO_PACKET_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        permit_case_story_surface=_load_json(Path(args.case_story_surface_input).expanduser().resolve()),
        permit_operator_demo_packet=_load_json(Path(args.operator_demo_packet_input).expanduser().resolve()),
    )
    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0 if bool((report.get("summary") or {}).get("decision_ladder_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
