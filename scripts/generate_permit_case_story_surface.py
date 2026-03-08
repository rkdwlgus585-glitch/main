#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS_INPUT = ROOT / "logs" / "permit_review_case_presets_latest.json"
DEFAULT_CASE_RELEASE_GUARD_INPUT = ROOT / "logs" / "permit_case_release_guard_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_case_story_surface_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit case story input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _review_reason_story(reason: str, manual_review_expected: bool) -> str:
    if reason == "capital_shortfall_only":
        return "자본금만 부족한 경우를 별도 케이스로 분리해 즉시 shortfall 판정 근거를 보여줍니다."
    if reason == "technician_shortfall_only":
        return "기술인력만 부족한 경우를 별도 케이스로 분리해 shortfall 원인을 설명합니다."
    if reason == "other_requirement_documents_missing":
        return "기타 증빙이 비어 있는 경우 자동 shortfall과 함께 수동 검토 필요성을 강조합니다."
    if manual_review_expected:
        return "자동 판정만으로 닫지 않고 운영 검토가 필요한 상황으로 취급합니다."
    return "운영 검토용 경계 사례로 유지합니다."


def build_case_story_surface(
    *,
    permit_review_case_presets: Dict[str, Any],
    permit_case_release_guard: Dict[str, Any],
) -> Dict[str, Any]:
    families_out: List[Dict[str, Any]] = []
    review_reasons: set[str] = set()
    manual_review_family_total = 0

    for family in [row for row in list(permit_review_case_presets.get("families") or []) if isinstance(row, dict)]:
        presets = [item for item in list(family.get("presets") or []) if isinstance(item, dict)]
        if not presets:
            continue
        representative_cases: List[Dict[str, Any]] = []
        story_points: List[str] = []
        family_manual_review_total = 0
        for preset in presets:
            expected = preset.get("expected_outcome") if isinstance(preset.get("expected_outcome"), dict) else {}
            review_reason = _safe_str(expected.get("review_reason"))
            manual_review_expected = bool(expected.get("manual_review_expected", False))
            if review_reason:
                review_reasons.add(review_reason)
            if manual_review_expected:
                family_manual_review_total += 1
            representative_cases.append(
                {
                    "preset_id": _safe_str(preset.get("preset_id")),
                    "case_kind": _safe_str(preset.get("case_kind")),
                    "service_code": _safe_str(preset.get("service_code")),
                    "service_name": _safe_str(preset.get("service_name")),
                    "expected_status": _safe_str(expected.get("overall_status")),
                    "review_reason": review_reason,
                    "manual_review_expected": manual_review_expected,
                }
            )
            story_points.append(_review_reason_story(review_reason, manual_review_expected))
        if family_manual_review_total:
            manual_review_family_total += 1
        deduped_story_points: List[str] = []
        for item in story_points:
            if item and item not in deduped_story_points:
                deduped_story_points.append(item)
        families_out.append(
            {
                "family_key": _safe_str(family.get("family_key")),
                "claim_id": _safe_str(family.get("claim_id")),
                "preset_total": _safe_int(family.get("preset_total")),
                "manual_review_preset_total": family_manual_review_total,
                "representative_cases": representative_cases,
                "operator_story_points": deduped_story_points,
            }
        )

    case_guard_summary = (
        permit_case_release_guard.get("summary")
        if isinstance(permit_case_release_guard.get("summary"), dict)
        else {}
    )
    summary = {
        "family_total": len(families_out),
        "story_family_total": len(families_out),
        "edge_case_total": sum(_safe_int(family.get("preset_total")) for family in families_out),
        "review_reason_total": len(review_reasons),
        "manual_review_family_total": manual_review_family_total,
        "case_release_guard_ready": bool(case_guard_summary.get("release_guard_ready", False)),
        "execution_lane_id": "case_story_surface",
        "parallel_lane_id": "review_case_input_presets",
        "story_ready": bool(families_out),
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "source_paths": {
            "permit_review_case_presets": str(DEFAULT_PRESETS_INPUT.resolve()),
            "permit_case_release_guard": str(DEFAULT_CASE_RELEASE_GUARD_INPUT.resolve()),
        },
        "families": families_out,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Case Story Surface",
        "",
        "## Summary",
        f"- family_total: `{summary.get('family_total', 0)}`",
        f"- story_family_total: `{summary.get('story_family_total', 0)}`",
        f"- edge_case_total: `{summary.get('edge_case_total', 0)}`",
        f"- review_reason_total: `{summary.get('review_reason_total', 0)}`",
        f"- manual_review_family_total: `{summary.get('manual_review_family_total', 0)}`",
        f"- case_release_guard_ready: `{summary.get('case_release_guard_ready', False)}`",
        f"- story_ready: `{summary.get('story_ready', False)}`",
        f"- execution_lane_id: `{summary.get('execution_lane_id', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        "",
        "## Families",
    ]
    for family in [row for row in list(report.get("families") or []) if isinstance(row, dict)]:
        lines.append(
            f"- `{family.get('family_key', '')}` claim `{family.get('claim_id', '')}` / presets {family.get('preset_total', 0)} / manual_review {family.get('manual_review_preset_total', 0)}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate operator/patent story surface for permit review edge cases.")
    parser.add_argument("--presets-input", default=str(DEFAULT_PRESETS_INPUT))
    parser.add_argument("--case-release-guard-input", default=str(DEFAULT_CASE_RELEASE_GUARD_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    report = build_case_story_surface(
        permit_review_case_presets=_load_json(Path(args.presets_input).expanduser().resolve()),
        permit_case_release_guard=_load_json(Path(args.case_release_guard_input).expanduser().resolve()),
    )
    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0 if bool((report.get("summary") or {}).get("story_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
