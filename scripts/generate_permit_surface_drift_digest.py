#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OBSERVABILITY_INPUT = ROOT / "logs" / "permit_demo_surface_observability_latest.json"
DEFAULT_RELEASE_BUNDLE_INPUT = ROOT / "logs" / "permit_release_bundle_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_surface_drift_digest_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_surface_drift_digest_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _surface_lookup(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for row in [item for item in list(rows or []) if isinstance(item, dict)]:
        surface_id = str(row.get("surface_id") or "").strip()
        if not surface_id:
            continue
        lookup[surface_id] = {
            "surface_id": surface_id,
            "label": str(row.get("label") or surface_id).strip(),
            "ready": bool(row.get("ready", False)),
            "coverage_total": int(row.get("coverage_total", 0) or 0),
            "sample_total": int(row.get("sample_total", 0) or 0),
        }
    return lookup


def build_surface_drift_digest(
    *,
    permit_demo_surface_observability: Dict[str, Any],
    permit_release_bundle: Dict[str, Any],
    previous_digest: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    observability_summary = (
        dict((permit_demo_surface_observability or {}).get("summary") or {})
        if isinstance(permit_demo_surface_observability, dict)
        else {}
    )
    current_surfaces = [row for row in list((permit_demo_surface_observability or {}).get("surfaces") or []) if isinstance(row, dict)]
    release_summary = (
        dict((permit_release_bundle or {}).get("summary") or {})
        if isinstance(permit_release_bundle, dict)
        else {}
    )
    previous_snapshot = (
        dict((previous_digest or {}).get("current_snapshot") or {})
        if isinstance(previous_digest, dict)
        else {}
    )
    previous_lookup = _surface_lookup(list(previous_snapshot.get("surfaces") or []))
    current_lookup = _surface_lookup(current_surfaces)

    changed_surfaces: List[Dict[str, Any]] = []
    readiness_flip_total = 0
    coverage_shift_total = 0
    sample_shift_total = 0
    prompt_surface_regression_total = 0
    reasoning_changed_surface_total = 0
    reasoning_readiness_flip_total = 0
    reasoning_coverage_shift_total = 0
    reasoning_sample_shift_total = 0
    reasoning_regression_total = 0
    prompt_surface_ids = {"runtime_critical_prompt", "runtime_prompt_case_binding"}
    reasoning_surface_ids = {"runtime_reasoning_card", "runtime_prompt_case_binding", "runtime_critical_prompt"}

    for surface_id in sorted(set(previous_lookup) | set(current_lookup)):
        previous_row = previous_lookup.get(surface_id, {})
        current_row = current_lookup.get(surface_id, {})
        flags: List[str] = []
        reasoning_focus = surface_id in reasoning_surface_ids
        if not previous_row:
            flags.append("surface_added")
        if not current_row:
            flags.append("surface_removed")
        if bool(previous_row.get("ready")) != bool(current_row.get("ready")):
            readiness_flip_total += 1
            flags.append("readiness_flip")
            if reasoning_focus:
                reasoning_readiness_flip_total += 1
            if surface_id in prompt_surface_ids and bool(previous_row.get("ready")) and not bool(current_row.get("ready")):
                prompt_surface_regression_total += 1
            if reasoning_focus and bool(previous_row.get("ready")) and not bool(current_row.get("ready")):
                reasoning_regression_total += 1
        if int(previous_row.get("coverage_total", 0) or 0) != int(current_row.get("coverage_total", 0) or 0):
            coverage_shift_total += 1
            flags.append("coverage_shift")
            if reasoning_focus:
                reasoning_coverage_shift_total += 1
        if int(previous_row.get("sample_total", 0) or 0) != int(current_row.get("sample_total", 0) or 0):
            sample_shift_total += 1
            flags.append("sample_shift")
            if reasoning_focus:
                reasoning_sample_shift_total += 1
        if not flags:
            continue
        if reasoning_focus:
            reasoning_changed_surface_total += 1
        changed_surfaces.append(
            {
                "surface_id": surface_id,
                "label": str(current_row.get("label") or previous_row.get("label") or surface_id),
                "reasoning_focus": reasoning_focus,
                "previous_ready": bool(previous_row.get("ready", False)),
                "current_ready": bool(current_row.get("ready", False)),
                "previous_coverage_total": int(previous_row.get("coverage_total", 0) or 0),
                "current_coverage_total": int(current_row.get("coverage_total", 0) or 0),
                "previous_sample_total": int(previous_row.get("sample_total", 0) or 0),
                "current_sample_total": int(current_row.get("sample_total", 0) or 0),
                "change_flags": flags,
            }
        )

    current_snapshot = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "surface_total": int(observability_summary.get("surface_total", 0) or 0),
            "ready_surface_total": int(observability_summary.get("ready_surface_total", 0) or 0),
            "missing_surface_total": int(observability_summary.get("missing_surface_total", 0) or 0),
            "prompt_case_binding_total": int(observability_summary.get("prompt_case_binding_total", 0) or 0),
            "runtime_critical_prompt_surface_ready": bool(
                observability_summary.get("runtime_critical_prompt_surface_ready", False)
            ),
            "runtime_prompt_case_binding_surface_ready": bool(
                observability_summary.get("runtime_prompt_case_binding_surface_ready", False)
            ),
            "partner_demo_surface_ready": bool(observability_summary.get("partner_demo_surface_ready", False)),
            "release_ready": bool(release_summary.get("release_ready", False)),
        },
        "surfaces": current_surfaces,
    }
    summary = {
        "digest_ready": bool(observability_summary),
        "previous_snapshot_ready": bool(previous_lookup),
        "delta_ready": bool(previous_lookup),
        "release_ready": bool(release_summary.get("release_ready", False)),
        "current_surface_total": int(observability_summary.get("surface_total", 0) or 0),
        "current_ready_surface_total": int(observability_summary.get("ready_surface_total", 0) or 0),
        "changed_surface_total": len(changed_surfaces),
        "readiness_flip_total": readiness_flip_total,
        "coverage_shift_total": coverage_shift_total,
        "sample_shift_total": sample_shift_total,
        "prompt_surface_regression_total": prompt_surface_regression_total,
        "reasoning_changed_surface_total": reasoning_changed_surface_total,
        "reasoning_readiness_flip_total": reasoning_readiness_flip_total,
        "reasoning_coverage_shift_total": reasoning_coverage_shift_total,
        "reasoning_sample_shift_total": reasoning_sample_shift_total,
        "reasoning_regression_total": reasoning_regression_total,
        "drift_detected": bool(changed_surfaces),
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "current_snapshot": current_snapshot,
        "changed_surfaces": changed_surfaces,
        "source_paths": {
            "permit_demo_surface_observability": str(DEFAULT_OBSERVABILITY_INPUT.resolve()),
            "permit_release_bundle": str(DEFAULT_RELEASE_BUNDLE_INPUT.resolve()),
            "previous_digest": str(DEFAULT_JSON_OUTPUT.resolve()),
        },
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Surface Drift Digest",
        "",
        "## Summary",
        f"- digest_ready: `{summary.get('digest_ready', False)}`",
        f"- previous_snapshot_ready: `{summary.get('previous_snapshot_ready', False)}`",
        f"- delta_ready: `{summary.get('delta_ready', False)}`",
        f"- release_ready: `{summary.get('release_ready', False)}`",
        f"- current_surface_total: `{summary.get('current_surface_total', 0)}`",
        f"- current_ready_surface_total: `{summary.get('current_ready_surface_total', 0)}`",
        f"- changed_surface_total: `{summary.get('changed_surface_total', 0)}`",
        f"- readiness_flip_total: `{summary.get('readiness_flip_total', 0)}`",
        f"- coverage_shift_total: `{summary.get('coverage_shift_total', 0)}`",
        f"- sample_shift_total: `{summary.get('sample_shift_total', 0)}`",
        f"- prompt_surface_regression_total: `{summary.get('prompt_surface_regression_total', 0)}`",
        f"- reasoning_changed_surface_total: `{summary.get('reasoning_changed_surface_total', 0)}`",
        f"- reasoning_readiness_flip_total: `{summary.get('reasoning_readiness_flip_total', 0)}`",
        f"- reasoning_coverage_shift_total: `{summary.get('reasoning_coverage_shift_total', 0)}`",
        f"- reasoning_sample_shift_total: `{summary.get('reasoning_sample_shift_total', 0)}`",
        f"- reasoning_regression_total: `{summary.get('reasoning_regression_total', 0)}`",
        f"- drift_detected: `{summary.get('drift_detected', False)}`",
        "",
        "## Changed Surfaces",
    ]
    changed_surfaces = [row for row in list(report.get("changed_surfaces") or []) if isinstance(row, dict)]
    if not changed_surfaces:
        lines.append("- no changed surfaces")
    else:
        for row in changed_surfaces:
            lines.append(
                f"- `{row.get('surface_id', '')}` "
                f"{'[reasoning] ' if row.get('reasoning_focus', False) else ''}"
                f"flags `{', '.join(list(row.get('change_flags') or []))}` / "
                f"ready {row.get('previous_ready', False)} -> {row.get('current_ready', False)} / "
                f"coverage {row.get('previous_coverage_total', 0)} -> {row.get('current_coverage_total', 0)} / "
                f"samples {row.get('previous_sample_total', 0)} -> {row.get('current_sample_total', 0)}"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a release-to-release drift digest for permit demo surfaces.")
    parser.add_argument("--observability-input", type=Path, default=DEFAULT_OBSERVABILITY_INPUT)
    parser.add_argument("--release-bundle-input", type=Path, default=DEFAULT_RELEASE_BUNDLE_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    previous_digest = _load_json(args.json_output.resolve())
    report = build_surface_drift_digest(
        permit_demo_surface_observability=_load_json(args.observability_input.resolve()),
        permit_release_bundle=_load_json(args.release_bundle_input.resolve()),
        previous_digest=previous_digest,
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
    return 0 if bool((report.get("summary") or {}).get("digest_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
