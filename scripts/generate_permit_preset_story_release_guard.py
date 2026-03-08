#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_HTML_INPUT = ROOT / "output" / "ai_permit_precheck.html"
DEFAULT_PRESETS_INPUT = ROOT / "logs" / "permit_review_case_presets_latest.json"
DEFAULT_CASE_STORY_INPUT = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_WIDGET_INPUT = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_API_CONTRACT_INPUT = ROOT / "logs" / "api_contract_spec_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_preset_story_release_guard_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_preset_story_release_guard_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit preset/story release guard input must be a JSON object")
    return payload


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


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


def _marker_status(text: str, markers: Tuple[str, ...]) -> Dict[str, Any]:
    missing = [marker for marker in markers if marker not in text]
    return {
        "ready": not missing,
        "missing_markers": missing,
    }


def _collect_preset_ids(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    family_keys: Set[str] = set()
    preset_ids: Set[str] = set()
    for family in [row for row in list(payload.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        if family_key:
            family_keys.add(family_key)
        for preset in [item for item in list(family.get("presets") or []) if isinstance(item, dict)]:
            preset_id = _safe_str(preset.get("preset_id"))
            if preset_id:
                preset_ids.add(preset_id)
    return family_keys, preset_ids


def _collect_story_surface(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str]]:
    family_keys: Set[str] = set()
    preset_ids: Set[str] = set()
    review_reasons: Set[str] = set()
    for family in [row for row in list(payload.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        if family_key:
            family_keys.add(family_key)
        for case in [item for item in list(family.get("representative_cases") or []) if isinstance(item, dict)]:
            preset_id = _safe_str(case.get("preset_id"))
            review_reason = _safe_str(case.get("review_reason"))
            if preset_id:
                preset_ids.add(preset_id)
            if review_reason:
                review_reasons.add(review_reason)
    return family_keys, preset_ids, review_reasons


def _collect_widget_story_surface(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str]]:
    packaging = payload.get("packaging") if isinstance(payload.get("packaging"), dict) else {}
    partner_rental = packaging.get("partner_rental") if isinstance(packaging.get("partner_rental"), dict) else {}
    permit_widget_feeds = (
        partner_rental.get("permit_widget_feeds")
        if isinstance(partner_rental.get("permit_widget_feeds"), dict)
        else {}
    )
    family_keys: Set[str] = set()
    preset_ids: Set[str] = set()
    review_reasons: Set[str] = set()
    for sample in [row for row in list(permit_widget_feeds.get("case_story_samples") or []) if isinstance(row, dict)]:
        family_key = _safe_str(sample.get("family_key"))
        if family_key:
            family_keys.add(family_key)
        for preset_id in list(sample.get("representative_preset_ids") or []):
            cleaned = _safe_str(preset_id)
            if cleaned:
                preset_ids.add(cleaned)
        for reason in list(sample.get("review_reasons") or []):
            cleaned = _safe_str(reason)
            if cleaned:
                review_reasons.add(cleaned)
    return family_keys, preset_ids, review_reasons


def _collect_api_story_surface(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str]]:
    services = payload.get("services") if isinstance(payload.get("services"), dict) else {}
    permit_service = services.get("permit") if isinstance(services.get("permit"), dict) else {}
    response_contract = (
        permit_service.get("response_contract") if isinstance(permit_service.get("response_contract"), dict) else {}
    )
    catalog_contracts = (
        response_contract.get("catalog_contracts") if isinstance(response_contract.get("catalog_contracts"), dict) else {}
    )
    master_catalog = (
        catalog_contracts.get("master_catalog") if isinstance(catalog_contracts.get("master_catalog"), dict) else {}
    )
    proof_surface_examples = (
        master_catalog.get("proof_surface_examples")
        if isinstance(master_catalog.get("proof_surface_examples"), dict)
        else {}
    )
    family_keys: Set[str] = set()
    preset_ids: Set[str] = set()
    review_reasons: Set[str] = set()
    for sample in [row for row in list(proof_surface_examples.get("case_story_samples") or []) if isinstance(row, dict)]:
        family_key = _safe_str(sample.get("family_key"))
        if family_key:
            family_keys.add(family_key)
        for preset_id in list(sample.get("representative_preset_ids") or []):
            cleaned = _safe_str(preset_id)
            if cleaned:
                preset_ids.add(cleaned)
        for reason in list(sample.get("review_reasons") or []):
            cleaned = _safe_str(reason)
            if cleaned:
                review_reasons.add(cleaned)
    return family_keys, preset_ids, review_reasons


def _sorted_sample(values: Set[str], limit: int = 12) -> List[str]:
    return sorted(values)[:limit]


def build_preset_story_release_guard(
    *,
    runtime_html: str,
    permit_review_case_presets: Dict[str, Any],
    permit_case_story_surface: Dict[str, Any],
    widget_rental_catalog: Dict[str, Any],
    api_contract_spec: Dict[str, Any],
) -> Dict[str, Any]:
    runtime_text = _expand_runtime_html_text(runtime_html)
    review_markers = (
        'id="reviewPresetBox"',
        "const renderReviewCasePresets = (industry) => {",
        "const applyReviewCasePreset = (preset) => {",
        "data-review-preset-id",
    )
    story_markers = (
        'id="caseStoryBox"',
        "const renderCaseStorySurface = (industry) => {",
        "case_story_surface",
        "operator_story_points",
    )
    runtime_review_status = _marker_status(runtime_text, review_markers)
    runtime_story_status = _marker_status(runtime_text, story_markers)

    preset_family_keys, preset_ids = _collect_preset_ids(permit_review_case_presets)
    story_family_keys, story_preset_ids, story_review_reasons = _collect_story_surface(permit_case_story_surface)
    widget_family_keys, widget_preset_ids, widget_review_reasons = _collect_widget_story_surface(widget_rental_catalog)
    api_family_keys, api_preset_ids, api_review_reasons = _collect_api_story_surface(api_contract_spec)

    widget_missing_story_families = story_family_keys - widget_family_keys
    api_missing_story_families = story_family_keys - api_family_keys
    widget_missing_story_presets = story_preset_ids - widget_preset_ids
    api_missing_story_presets = story_preset_ids - api_preset_ids
    widget_missing_review_reasons = story_review_reasons - widget_review_reasons
    api_missing_review_reasons = story_review_reasons - api_review_reasons

    widget_extra_story_families = widget_family_keys - story_family_keys
    api_extra_story_families = api_family_keys - story_family_keys
    widget_extra_story_presets = widget_preset_ids - story_preset_ids
    api_extra_story_presets = api_preset_ids - story_preset_ids
    widget_extra_review_reasons = widget_review_reasons - story_review_reasons
    api_extra_review_reasons = api_review_reasons - story_review_reasons

    story_contract_parity_ready = (
        bool(story_family_keys)
        and not widget_missing_story_families
        and not api_missing_story_families
        and not widget_missing_story_presets
        and not api_missing_story_presets
        and not widget_missing_review_reasons
        and not api_missing_review_reasons
        and not widget_extra_story_families
        and not api_extra_story_families
        and not widget_extra_story_presets
        and not api_extra_story_presets
        and not widget_extra_review_reasons
        and not api_extra_review_reasons
    )
    preset_story_guard_ready = (
        bool(preset_family_keys)
        and bool(preset_ids)
        and bool(story_family_keys)
        and runtime_review_status["ready"]
        and runtime_story_status["ready"]
        and story_contract_parity_ready
    )

    summary = {
        "preset_family_total": len(preset_family_keys),
        "preset_total": len(preset_ids),
        "story_family_total": len(story_family_keys),
        "story_preset_total": len(story_preset_ids),
        "story_review_reason_total": len(story_review_reasons),
        "widget_story_family_total": len(widget_family_keys),
        "widget_story_preset_total": len(widget_preset_ids),
        "widget_story_review_reason_total": len(widget_review_reasons),
        "api_story_family_total": len(api_family_keys),
        "api_story_preset_total": len(api_preset_ids),
        "api_story_review_reason_total": len(api_review_reasons),
        "runtime_review_preset_surface_ready": bool(runtime_review_status["ready"]),
        "runtime_case_story_surface_ready": bool(runtime_story_status["ready"]),
        "story_contract_parity_ready": story_contract_parity_ready,
        "preset_story_guard_ready": preset_story_guard_ready,
        "execution_lane_id": "preset_story_release_guard",
        "parallel_lane_id": "operator_demo_packet",
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "source_paths": {
            "runtime_html": str(DEFAULT_RUNTIME_HTML_INPUT.resolve()),
            "permit_review_case_presets": str(DEFAULT_PRESETS_INPUT.resolve()),
            "permit_case_story_surface": str(DEFAULT_CASE_STORY_INPUT.resolve()),
            "widget_rental_catalog": str(DEFAULT_WIDGET_INPUT.resolve()),
            "api_contract_spec": str(DEFAULT_API_CONTRACT_INPUT.resolve()),
        },
        "runtime_surface": {
            "review_preset": runtime_review_status,
            "case_story": runtime_story_status,
        },
        "missing": {
            "widget_story_families": _sorted_sample(widget_missing_story_families),
            "api_story_families": _sorted_sample(api_missing_story_families),
            "widget_story_presets": _sorted_sample(widget_missing_story_presets),
            "api_story_presets": _sorted_sample(api_missing_story_presets),
            "widget_review_reasons": _sorted_sample(widget_missing_review_reasons),
            "api_review_reasons": _sorted_sample(api_missing_review_reasons),
        },
        "extras": {
            "widget_story_families": _sorted_sample(widget_extra_story_families),
            "api_story_families": _sorted_sample(api_extra_story_families),
            "widget_story_presets": _sorted_sample(widget_extra_story_presets),
            "api_story_presets": _sorted_sample(api_extra_story_presets),
            "widget_review_reasons": _sorted_sample(widget_extra_review_reasons),
            "api_review_reasons": _sorted_sample(api_extra_review_reasons),
        },
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    runtime_surface = dict(report.get("runtime_surface") or {})
    review_surface = dict(runtime_surface.get("review_preset") or {})
    story_surface = dict(runtime_surface.get("case_story") or {})
    missing = dict(report.get("missing") or {})
    extras = dict(report.get("extras") or {})
    lines = [
        "# Permit Preset Story Release Guard",
        "",
        "## Summary",
        f"- preset_family_total: `{summary.get('preset_family_total', 0)}`",
        f"- preset_total: `{summary.get('preset_total', 0)}`",
        f"- story_family_total: `{summary.get('story_family_total', 0)}`",
        f"- story_preset_total: `{summary.get('story_preset_total', 0)}`",
        f"- story_review_reason_total: `{summary.get('story_review_reason_total', 0)}`",
        f"- widget_story_family_total: `{summary.get('widget_story_family_total', 0)}`",
        f"- api_story_family_total: `{summary.get('api_story_family_total', 0)}`",
        f"- runtime_review_preset_surface_ready: `{summary.get('runtime_review_preset_surface_ready', False)}`",
        f"- runtime_case_story_surface_ready: `{summary.get('runtime_case_story_surface_ready', False)}`",
        f"- story_contract_parity_ready: `{summary.get('story_contract_parity_ready', False)}`",
        f"- preset_story_guard_ready: `{summary.get('preset_story_guard_ready', False)}`",
        "",
        "## Runtime Surface",
        f"- review_preset_missing_markers: `{', '.join(review_surface.get('missing_markers', []))}`",
        f"- case_story_missing_markers: `{', '.join(story_surface.get('missing_markers', []))}`",
        "",
        "## Missing Samples",
        f"- widget_story_families: `{', '.join(missing.get('widget_story_families', []))}`",
        f"- api_story_families: `{', '.join(missing.get('api_story_families', []))}`",
        f"- widget_story_presets: `{', '.join(missing.get('widget_story_presets', []))}`",
        f"- api_story_presets: `{', '.join(missing.get('api_story_presets', []))}`",
        f"- widget_review_reasons: `{', '.join(missing.get('widget_review_reasons', []))}`",
        f"- api_review_reasons: `{', '.join(missing.get('api_review_reasons', []))}`",
        "",
        "## Extra Samples",
        f"- widget_story_families: `{', '.join(extras.get('widget_story_families', []))}`",
        f"- api_story_families: `{', '.join(extras.get('api_story_families', []))}`",
        f"- widget_story_presets: `{', '.join(extras.get('widget_story_presets', []))}`",
        f"- api_story_presets: `{', '.join(extras.get('api_story_presets', []))}`",
        f"- widget_review_reasons: `{', '.join(extras.get('widget_review_reasons', []))}`",
        f"- api_review_reasons: `{', '.join(extras.get('api_review_reasons', []))}`",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a release guard for runtime review presets and case-story contract parity.")
    parser.add_argument("--runtime-html", type=Path, default=DEFAULT_RUNTIME_HTML_INPUT)
    parser.add_argument("--review-case-presets", type=Path, default=DEFAULT_PRESETS_INPUT)
    parser.add_argument("--case-story-surface", type=Path, default=DEFAULT_CASE_STORY_INPUT)
    parser.add_argument("--widget", type=Path, default=DEFAULT_WIDGET_INPUT)
    parser.add_argument("--api-contract", type=Path, default=DEFAULT_API_CONTRACT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_preset_story_release_guard(
        runtime_html=_load_text(args.runtime_html.resolve()),
        permit_review_case_presets=_load_json(args.review_case_presets.resolve()),
        permit_case_story_surface=_load_json(args.case_story_surface.resolve()),
        widget_rental_catalog=_load_json(args.widget.resolve()),
        api_contract_spec=_load_json(args.api_contract.resolve()),
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
    return 0 if bool((report.get("summary") or {}).get("preset_story_guard_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
