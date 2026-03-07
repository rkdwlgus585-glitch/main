#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def build_alignment(*, partner_flow_path: Path, partner_preview_path: Path) -> Dict[str, Any]:
    flow = _load_json(partner_flow_path)
    preview = _load_json(partner_preview_path)

    handoff = flow.get("handoff") if isinstance(flow.get("handoff"), dict) else {}
    current_remaining = _as_list(handoff.get("remaining_required_inputs"))
    current_resolved = _as_list(handoff.get("resolved_inputs"))
    preview_scenarios = preview.get("scenarios") if isinstance(preview.get("scenarios"), list) else []
    recommended = preview.get("recommended_path") if isinstance(preview.get("recommended_path"), dict) else {}
    recommended_scenario = str(recommended.get("scenario") or "").strip()
    recommended_remaining = _as_list(recommended.get("remaining_required_inputs"))
    baseline = next((row for row in preview_scenarios if isinstance(row, dict) and str(row.get("scenario") or "") == "baseline"), {})
    baseline_remaining = _as_list((baseline or {}).get("remaining_required_inputs"))
    scenario_map = {
        str(row.get("scenario") or "").strip(): row
        for row in preview_scenarios
        if isinstance(row, dict) and str(row.get("scenario") or "").strip()
    }
    recommended_row = scenario_map.get(recommended_scenario, {})
    recommended_resolved = _as_list((recommended_row or {}).get("resolved_inputs"))

    current_set = set(current_remaining)
    recommended_set = set(recommended_remaining)
    baseline_set = set(baseline_remaining)
    removed_inputs = sorted(current_set - recommended_set)
    unresolved_delta = sorted(recommended_set - current_set)
    baseline_matches_current = baseline_set == current_set
    recommended_reduces_current = recommended_set.issubset(current_set) and len(recommended_set) <= len(current_set)
    recommended_clears_current = len(recommended_remaining) == 0 and current_set.issubset(set(recommended_resolved))

    ok = bool(recommended_scenario) and baseline_matches_current and recommended_reduces_current
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scope": {
            "offering_id": str(flow.get("offering_id") or preview.get("offering_id") or ""),
            "tenant_id": str(flow.get("tenant_id") or preview.get("tenant_id") or ""),
            "channel_id": str(flow.get("channel_id") or preview.get("channel_id") or ""),
            "host": str(flow.get("host") or preview.get("host") or ""),
        },
        "current": {
            "remaining_required_inputs": current_remaining,
            "resolved_inputs": current_resolved,
        },
        "preview": {
            "scenario_count": len(preview_scenarios),
            "recommended_scenario": recommended_scenario,
            "recommended_remaining_required_inputs": recommended_remaining,
            "recommended_resolved_inputs": recommended_resolved,
            "baseline_remaining_required_inputs": baseline_remaining,
            "removed_inputs_vs_current": removed_inputs,
            "unexpected_inputs_vs_current": unresolved_delta,
        },
        "summary": {
            "ok": ok,
            "baseline_matches_current": baseline_matches_current,
            "recommended_reduces_current": recommended_reduces_current,
            "recommended_clears_current": recommended_clears_current,
            "removed_input_count": len(removed_inputs),
            "unexpected_input_count": len(unresolved_delta),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
    preview = payload.get("preview") if isinstance(payload.get("preview"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}

    lines = [
        "# Partner Preview Alignment",
        "",
        f"- tenant_id: {scope.get('tenant_id')}",
        f"- channel_id: {scope.get('channel_id')}",
        f"- offering_id: {scope.get('offering_id')}",
        f"- host: {scope.get('host')}",
        "",
        "## Current Canonical Flow",
        f"- remaining_required_inputs: {', '.join(current.get('remaining_required_inputs') or []) or '(none)'}",
        f"- resolved_inputs: {', '.join(current.get('resolved_inputs') or []) or '(none)'}",
        "",
        "## Preview Recommendation",
        f"- recommended_scenario: {preview.get('recommended_scenario')}",
        f"- baseline_remaining_required_inputs: {', '.join(preview.get('baseline_remaining_required_inputs') or []) or '(none)'}",
        f"- recommended_remaining_required_inputs: {', '.join(preview.get('recommended_remaining_required_inputs') or []) or '(none)'}",
        f"- removed_inputs_vs_current: {', '.join(preview.get('removed_inputs_vs_current') or []) or '(none)'}",
        f"- unexpected_inputs_vs_current: {', '.join(preview.get('unexpected_inputs_vs_current') or []) or '(none)'}",
        "",
        "## Summary",
        f"- ok: {summary.get('ok')}",
        f"- baseline_matches_current: {summary.get('baseline_matches_current')}",
        f"- recommended_reduces_current: {summary.get('recommended_reduces_current')}",
        f"- recommended_clears_current: {summary.get('recommended_clears_current')}",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify that partner activation preview matches the current canonical blocker state")
    parser.add_argument("--partner-flow", default="logs/partner_onboarding_flow_latest.json")
    parser.add_argument("--partner-preview", default="logs/partner_activation_preview_latest.json")
    parser.add_argument("--json", default="logs/partner_preview_alignment_latest.json")
    parser.add_argument("--md", default="logs/partner_preview_alignment_latest.md")
    args = parser.parse_args()

    payload = build_alignment(
        partner_flow_path=(ROOT / str(args.partner_flow)).resolve(),
        partner_preview_path=(ROOT / str(args.partner_preview)).resolve(),
    )

    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path), "summary": payload.get("summary")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
