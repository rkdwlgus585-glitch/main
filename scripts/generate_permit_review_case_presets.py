#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDSET_INPUT = ROOT / "logs" / "permit_family_case_goldset_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_review_case_presets_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_review_case_presets_latest.md"

CASE_KIND_LABELS = {
    "capital_only_fail": "자본금 부족 프리셋",
    "technician_only_fail": "기술인력 부족 프리셋",
    "document_missing_review": "서류 누락 검토 프리셋",
}


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit review case preset input must be a JSON object")
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
        return float(value)
    except Exception:
        return 0.0


def _preset_operator_note(case_kind: str, expected: Dict[str, Any]) -> str:
    review_reason = _safe_str(expected.get("review_reason"))
    if case_kind == "capital_only_fail":
        return "자본금만 부족한 상황을 즉시 재현하는 프리셋입니다."
    if case_kind == "technician_only_fail":
        return "기술인력만 부족한 상황을 즉시 재현하는 프리셋입니다."
    if case_kind == "document_missing_review":
        if bool(expected.get("manual_review_expected")):
            return "기타 요건 증빙이 비어 수동 검토가 필요한 상황을 재현합니다."
        return "구조화되지 않은 기타 요건을 점검하는 검토 프리셋입니다."
    if review_reason:
        return f"{review_reason} 상황을 재현하는 프리셋입니다."
    return "운영 검토용 재현 프리셋입니다."


def _build_preset(family_key: str, claim_id: str, case: Dict[str, Any]) -> Dict[str, Any]:
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    inputs = case.get("inputs") if isinstance(case.get("inputs"), dict) else {}
    case_kind = _safe_str(case.get("case_kind"))
    return {
        "preset_id": _safe_str(case.get("case_id")),
        "family_key": family_key,
        "claim_id": claim_id,
        "case_id": _safe_str(case.get("case_id")),
        "case_kind": case_kind,
        "preset_label": CASE_KIND_LABELS.get(case_kind, case_kind or "검토 프리셋"),
        "service_code": _safe_str(case.get("service_code")),
        "service_name": _safe_str(case.get("service_name")),
        "law_title": _safe_str(case.get("law_title")),
        "legal_basis_title": _safe_str(case.get("legal_basis_title")),
        "input_payload": {
            "industry_selector": _safe_str(inputs.get("industry_selector")),
            "capital_eok": round(_safe_float(inputs.get("capital_eok")), 2),
            "technicians_count": _safe_int(inputs.get("technicians_count")),
            "other_requirement_checklist": (
                dict(inputs.get("other_requirement_checklist"))
                if isinstance(inputs.get("other_requirement_checklist"), dict)
                else {}
            ),
        },
        "expected_outcome": {
            "overall_status": _safe_str(expected.get("overall_status")),
            "capital_gap_eok": round(_safe_float(expected.get("capital_gap_eok")), 2),
            "technicians_gap": _safe_int(expected.get("technicians_gap")),
            "review_reason": _safe_str(expected.get("review_reason")),
            "manual_review_expected": bool(expected.get("manual_review_expected", False)),
            "proof_coverage_ratio": _safe_str(expected.get("proof_coverage_ratio")),
        },
        "operator_note": _preset_operator_note(case_kind, expected),
    }


def build_review_case_presets(*, permit_family_case_goldset: Dict[str, Any]) -> Dict[str, Any]:
    families_out: List[Dict[str, Any]] = []
    preset_total = 0
    capital_only_fail_preset_total = 0
    technician_only_fail_preset_total = 0
    document_missing_review_preset_total = 0
    manual_review_expected_total = 0

    for family in [row for row in list(permit_family_case_goldset.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        claim_id = _safe_str(family.get("claim_id"))
        presets: List[Dict[str, Any]] = []
        for case in [item for item in list(family.get("cases") or []) if isinstance(item, dict)]:
            case_kind = _safe_str(case.get("case_kind"))
            if case_kind not in CASE_KIND_LABELS:
                continue
            preset = _build_preset(family_key, claim_id, case)
            presets.append(preset)
            preset_total += 1
            if case_kind == "capital_only_fail":
                capital_only_fail_preset_total += 1
            elif case_kind == "technician_only_fail":
                technician_only_fail_preset_total += 1
            elif case_kind == "document_missing_review":
                document_missing_review_preset_total += 1
            if bool((preset.get("expected_outcome") or {}).get("manual_review_expected")):
                manual_review_expected_total += 1
        if presets:
            families_out.append(
                {
                    "family_key": family_key,
                    "claim_id": claim_id,
                    "preset_total": len(presets),
                    "presets": presets,
                }
            )

    family_total = len(families_out)
    summary = {
        "family_total": family_total,
        "preset_total": preset_total,
        "preset_family_total": family_total,
        "capital_only_fail_preset_total": capital_only_fail_preset_total,
        "technician_only_fail_preset_total": technician_only_fail_preset_total,
        "document_missing_review_preset_total": document_missing_review_preset_total,
        "manual_review_expected_total": manual_review_expected_total,
        "execution_lane_id": "review_case_input_presets",
        "parallel_lane_id": "case_story_surface",
        "preset_ready": family_total > 0 and preset_total >= family_total * 3,
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "source_paths": {
            "permit_family_case_goldset": str(DEFAULT_GOLDSET_INPUT.resolve()),
        },
        "families": families_out,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Review Case Presets",
        "",
        "## Summary",
        f"- family_total: `{summary.get('family_total', 0)}`",
        f"- preset_total: `{summary.get('preset_total', 0)}`",
        f"- preset_family_total: `{summary.get('preset_family_total', 0)}`",
        f"- capital_only_fail_preset_total: `{summary.get('capital_only_fail_preset_total', 0)}`",
        f"- technician_only_fail_preset_total: `{summary.get('technician_only_fail_preset_total', 0)}`",
        f"- document_missing_review_preset_total: `{summary.get('document_missing_review_preset_total', 0)}`",
        f"- manual_review_expected_total: `{summary.get('manual_review_expected_total', 0)}`",
        f"- preset_ready: `{summary.get('preset_ready', False)}`",
        f"- execution_lane_id: `{summary.get('execution_lane_id', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        "",
        "## Families",
    ]
    for family in [row for row in list(report.get("families") or []) if isinstance(row, dict)]:
        lines.append(
            f"- `{family.get('family_key', '')}` claim `{family.get('claim_id', '')}` / presets {family.get('preset_total', 0)}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate reusable operator review presets from permit edge cases.")
    parser.add_argument("--goldset-input", default=str(DEFAULT_GOLDSET_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    report = build_review_case_presets(
        permit_family_case_goldset=_load_json(Path(args.goldset_input).expanduser().resolve()),
    )
    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0 if bool((report.get("summary") or {}).get("preset_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
