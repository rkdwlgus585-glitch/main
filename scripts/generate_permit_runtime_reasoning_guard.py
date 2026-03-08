#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_REASON_DECISION_LADDER_INPUT = ROOT / "logs" / "permit_review_reason_decision_ladder_latest.json"
DEFAULT_DEMO_SURFACE_OBSERVABILITY_INPUT = ROOT / "logs" / "permit_demo_surface_observability_latest.json"
DEFAULT_SURFACE_DRIFT_DIGEST_INPUT = ROOT / "logs" / "permit_surface_drift_digest_latest.json"
DEFAULT_PROMPT_CASE_BINDING_PACKET_INPUT = ROOT / "logs" / "permit_prompt_case_binding_packet_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_runtime_reasoning_guard_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_runtime_reasoning_guard_latest.md"


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


def build_guard_report(
    *,
    permit_review_reason_decision_ladder: Dict[str, Any],
    permit_demo_surface_observability: Dict[str, Any],
    permit_surface_drift_digest: Dict[str, Any],
    permit_prompt_case_binding_packet: Dict[str, Any],
) -> Dict[str, Any]:
    ladder_summary = _safe_dict(permit_review_reason_decision_ladder.get("summary"))
    ladder_rows = [_safe_dict(row) for row in _safe_list(permit_review_reason_decision_ladder.get("ladders")) if _safe_dict(row)]
    observability_summary = _safe_dict(permit_demo_surface_observability.get("summary"))
    drift_summary = _safe_dict(permit_surface_drift_digest.get("summary"))
    prompt_case_binding_summary = _safe_dict(permit_prompt_case_binding_packet.get("summary"))

    review_reason_total = int(ladder_summary.get("review_reason_total", 0) or 0)
    prompt_bound_reason_total = int(ladder_summary.get("prompt_bound_reason_total", 0) or 0)
    binding_gap_total = max(0, review_reason_total - prompt_bound_reason_total)
    runtime_reasoning_card_surface_ready = bool(
        observability_summary.get("runtime_reasoning_card_surface_ready", False)
    )
    runtime_prompt_case_binding_surface_ready = bool(
        observability_summary.get("runtime_prompt_case_binding_surface_ready", False)
    )
    runtime_critical_prompt_surface_ready = bool(
        observability_summary.get("runtime_critical_prompt_surface_ready", False)
    )
    reasoning_regression_total = int(drift_summary.get("reasoning_regression_total", 0) or 0)
    reasoning_changed_surface_total = int(drift_summary.get("reasoning_changed_surface_total", 0) or 0)
    missing_binding_reasons = [
        {
            "review_reason": _safe_str(row.get("review_reason")),
            "label": _safe_str(row.get("review_reason_label")),
            "inspect_first": _safe_str(row.get("inspect_first")),
        }
        for row in ladder_rows
        if _safe_str(row.get("review_reason")) and not _safe_list(row.get("binding_preset_ids"))
    ]
    guard_ready = all(
        [
            bool(ladder_summary.get("decision_ladder_ready", False)),
            bool(observability_summary.get("observability_ready", False)),
            runtime_reasoning_card_surface_ready,
            runtime_prompt_case_binding_surface_ready,
            runtime_critical_prompt_surface_ready,
            bool(prompt_case_binding_summary.get("packet_ready", False)),
            bool(drift_summary.get("digest_ready", False)),
            reasoning_regression_total == 0,
            binding_gap_total == 0,
            not missing_binding_reasons,
        ]
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "guard_ready": guard_ready,
            "review_reason_total": review_reason_total,
            "prompt_bound_reason_total": prompt_bound_reason_total,
            "binding_gap_total": binding_gap_total,
            "missing_binding_reason_total": len(missing_binding_reasons),
            "runtime_reasoning_card_surface_ready": runtime_reasoning_card_surface_ready,
            "runtime_prompt_case_binding_surface_ready": runtime_prompt_case_binding_surface_ready,
            "runtime_critical_prompt_surface_ready": runtime_critical_prompt_surface_ready,
            "demo_surface_observability_ready": bool(observability_summary.get("observability_ready", False)),
            "surface_drift_digest_ready": bool(drift_summary.get("digest_ready", False)),
            "surface_drift_delta_ready": bool(drift_summary.get("delta_ready", False)),
            "reasoning_changed_surface_total": reasoning_changed_surface_total,
            "reasoning_regression_total": reasoning_regression_total,
            "prompt_case_binding_packet_ready": bool(prompt_case_binding_summary.get("packet_ready", False)),
            "representative_family_total": int(prompt_case_binding_summary.get("representative_family_total", 0) or 0),
        },
        "missing_binding_reason_preview": missing_binding_reasons[:5],
        "source_paths": {
            "permit_review_reason_decision_ladder": str(DEFAULT_REVIEW_REASON_DECISION_LADDER_INPUT.resolve()),
            "permit_demo_surface_observability": str(DEFAULT_DEMO_SURFACE_OBSERVABILITY_INPUT.resolve()),
            "permit_surface_drift_digest": str(DEFAULT_SURFACE_DRIFT_DIGEST_INPUT.resolve()),
            "permit_prompt_case_binding_packet": str(DEFAULT_PROMPT_CASE_BINDING_PACKET_INPUT.resolve()),
        },
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = _safe_dict(report.get("summary"))
    lines = [
        "# Permit Runtime Reasoning Guard",
        "",
        "## Summary",
        f"- guard_ready: `{summary.get('guard_ready', False)}`",
        f"- review_reason_total: `{summary.get('review_reason_total', 0)}`",
        f"- prompt_bound_reason_total: `{summary.get('prompt_bound_reason_total', 0)}`",
        f"- binding_gap_total: `{summary.get('binding_gap_total', 0)}`",
        f"- missing_binding_reason_total: `{summary.get('missing_binding_reason_total', 0)}`",
        f"- runtime_reasoning_card_surface_ready: `{summary.get('runtime_reasoning_card_surface_ready', False)}`",
        f"- runtime_prompt_case_binding_surface_ready: `{summary.get('runtime_prompt_case_binding_surface_ready', False)}`",
        f"- runtime_critical_prompt_surface_ready: `{summary.get('runtime_critical_prompt_surface_ready', False)}`",
        f"- demo_surface_observability_ready: `{summary.get('demo_surface_observability_ready', False)}`",
        f"- surface_drift_digest_ready: `{summary.get('surface_drift_digest_ready', False)}`",
        f"- surface_drift_delta_ready: `{summary.get('surface_drift_delta_ready', False)}`",
        f"- reasoning_changed_surface_total: `{summary.get('reasoning_changed_surface_total', 0)}`",
        f"- reasoning_regression_total: `{summary.get('reasoning_regression_total', 0)}`",
        f"- prompt_case_binding_packet_ready: `{summary.get('prompt_case_binding_packet_ready', False)}`",
        f"- representative_family_total: `{summary.get('representative_family_total', 0)}`",
    ]
    preview = [_safe_dict(row) for row in _safe_list(report.get("missing_binding_reason_preview")) if _safe_dict(row)]
    if preview:
        lines.extend(["", "## Missing Binding Reason Preview"])
        for row in preview:
            lines.append(
                f"- `{_safe_str(row.get('review_reason'))}` / `{_safe_str(row.get('label'))}` / inspect `{_safe_str(row.get('inspect_first'))}`"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a release guard for the permit runtime reasoning card.")
    parser.add_argument("--review-reason-decision-ladder-input", type=Path, default=DEFAULT_REVIEW_REASON_DECISION_LADDER_INPUT)
    parser.add_argument("--demo-surface-observability-input", type=Path, default=DEFAULT_DEMO_SURFACE_OBSERVABILITY_INPUT)
    parser.add_argument("--surface-drift-digest-input", type=Path, default=DEFAULT_SURFACE_DRIFT_DIGEST_INPUT)
    parser.add_argument("--prompt-case-binding-packet-input", type=Path, default=DEFAULT_PROMPT_CASE_BINDING_PACKET_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_guard_report(
        permit_review_reason_decision_ladder=_load_json(args.review_reason_decision_ladder_input.resolve()),
        permit_demo_surface_observability=_load_json(args.demo_surface_observability_input.resolve()),
        permit_surface_drift_digest=_load_json(args.surface_drift_digest_input.resolve()),
        permit_prompt_case_binding_packet=_load_json(args.prompt_case_binding_packet_input.resolve()),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json_output.resolve()), "md": str(args.md_output.resolve())}, ensure_ascii=False, indent=2))
    return 0 if bool(_safe_dict(report.get("summary")).get("guard_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
