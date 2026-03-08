#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS_INPUT = ROOT / "logs" / "permit_review_case_presets_latest.json"
DEFAULT_CASE_STORY_INPUT = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_PATENT_INPUT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_operator_demo_packet_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit operator demo packet input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _claim_lookup(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for family in [row for row in list(payload.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        claim_packet = family.get("claim_packet") if isinstance(family.get("claim_packet"), dict) else {}
        if family_key and claim_packet:
            lookup[family_key] = claim_packet
    return lookup


def _story_lookup(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for family in [row for row in list(payload.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        if family_key:
            lookup[family_key] = family
    return lookup


def build_operator_demo_packet(
    *,
    permit_review_case_presets: Dict[str, Any],
    permit_case_story_surface: Dict[str, Any],
    permit_patent_evidence_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    claim_lookup = _claim_lookup(permit_patent_evidence_bundle)
    story_lookup = _story_lookup(permit_case_story_surface)
    families_out: List[Dict[str, Any]] = []
    demo_case_total = 0
    manual_review_demo_total = 0
    review_reasons: List[str] = []

    for family in [row for row in list(permit_review_case_presets.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        claim_id = _safe_str(family.get("claim_id"))
        claim_packet = claim_lookup.get(family_key, {})
        story_surface = story_lookup.get(family_key, {})
        source_proof_summary = (
            claim_packet.get("source_proof_summary")
            if isinstance(claim_packet.get("source_proof_summary"), dict)
            else {}
        )
        demo_cases: List[Dict[str, Any]] = []
        for preset in [item for item in list(family.get("presets") or []) if isinstance(item, dict)]:
            expected = preset.get("expected_outcome") if isinstance(preset.get("expected_outcome"), dict) else {}
            review_reason = _safe_str(expected.get("review_reason"))
            if review_reason and review_reason not in review_reasons:
                review_reasons.append(review_reason)
            manual_review_expected = bool(expected.get("manual_review_expected", False))
            if manual_review_expected:
                manual_review_demo_total += 1
            demo_cases.append(
                {
                    "preset_id": _safe_str(preset.get("preset_id")),
                    "case_kind": _safe_str(preset.get("case_kind")),
                    "preset_label": _safe_str(preset.get("preset_label")),
                    "service_code": _safe_str(preset.get("service_code")),
                    "service_name": _safe_str(preset.get("service_name")),
                    "review_reason": review_reason,
                    "expected_status": _safe_str(expected.get("overall_status")),
                    "manual_review_expected": manual_review_expected,
                    "proof_coverage_ratio": _safe_str(
                        source_proof_summary.get("proof_coverage_ratio")
                    ) or _safe_str(expected.get("proof_coverage_ratio")),
                    "operator_note": _safe_str(preset.get("operator_note")),
                    "demo_steps": [
                        f"업종 `{_safe_str(preset.get('service_name'))}` 선택",
                        f"`{_safe_str(preset.get('preset_label'))}` 클릭",
                        f"결과 카드에서 `{_safe_str(expected.get('overall_status'))}` 와 `{review_reason or 'review_reason 확인'}` 확인",
                    ],
                }
            )
            demo_case_total += 1
        if not demo_cases:
            continue
        families_out.append(
            {
                "family_key": family_key,
                "claim_id": claim_id or _safe_str(claim_packet.get("claim_id")),
                "claim_title": _safe_str(claim_packet.get("claim_title")),
                "proof_coverage_ratio": _safe_str(source_proof_summary.get("proof_coverage_ratio")),
                "checksum_samples": [
                    _safe_str(item)
                    for item in list(source_proof_summary.get("checksum_samples") or [])
                    if _safe_str(item)
                ][:3],
                "operator_story_points": [
                    _safe_str(item)
                    for item in list(story_surface.get("operator_story_points") or [])
                    if _safe_str(item)
                ][:3],
                "demo_cases": demo_cases,
            }
        )

    summary = {
        "family_total": len(families_out),
        "demo_case_total": demo_case_total,
        "manual_review_demo_total": manual_review_demo_total,
        "review_reason_total": len(review_reasons),
        "execution_lane_id": "operator_demo_packet",
        "parallel_lane_id": "operator_demo_surface",
        "operator_demo_ready": bool(families_out) and demo_case_total >= len(families_out) * 3,
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "source_paths": {
            "permit_review_case_presets": str(DEFAULT_PRESETS_INPUT.resolve()),
            "permit_case_story_surface": str(DEFAULT_CASE_STORY_INPUT.resolve()),
            "permit_patent_evidence_bundle": str(DEFAULT_PATENT_INPUT.resolve()),
        },
        "families": families_out,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Operator Demo Packet",
        "",
        "## Summary",
        f"- family_total: `{summary.get('family_total', 0)}`",
        f"- demo_case_total: `{summary.get('demo_case_total', 0)}`",
        f"- manual_review_demo_total: `{summary.get('manual_review_demo_total', 0)}`",
        f"- review_reason_total: `{summary.get('review_reason_total', 0)}`",
        f"- operator_demo_ready: `{summary.get('operator_demo_ready', False)}`",
        f"- execution_lane_id: `{summary.get('execution_lane_id', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        "",
        "## Families",
    ]
    for family in [row for row in list(report.get("families") or []) if isinstance(row, dict)]:
        lines.append(
            f"- `{family.get('family_key', '')}` claim `{family.get('claim_id', '')}` / demo_cases {len(list(family.get('demo_cases') or []))}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact operator demo packet for permit review presets.")
    parser.add_argument("--review-case-presets", type=Path, default=DEFAULT_PRESETS_INPUT)
    parser.add_argument("--case-story-surface", type=Path, default=DEFAULT_CASE_STORY_INPUT)
    parser.add_argument("--patent-evidence", type=Path, default=DEFAULT_PATENT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_operator_demo_packet(
        permit_review_case_presets=_load_json(args.review_case_presets.resolve()),
        permit_case_story_surface=_load_json(args.case_story_surface.resolve()),
        permit_patent_evidence_bundle=_load_json(args.patent_evidence.resolve()),
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
    return 0 if bool((report.get("summary") or {}).get("operator_demo_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
