#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLOSED_LANE_ID = "runtime_reasoning_guard"
DEFAULT_BRAINSTORM = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_FOUNDER = ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"
DEFAULT_SYSTEM_SPLIT = ROOT / "logs" / "system_split_first_principles_packet_latest.json"
DEFAULT_THINKING_BUNDLE = ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_closed_lane_stale_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_closed_lane_stale_audit_latest.md"


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


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _collect_stale_refs(
    *,
    artifact: str,
    fields: List[tuple[str, Any]],
    closed_lane_id: str,
) -> List[Dict[str, str]]:
    stale_rows: List[Dict[str, str]] = []
    for field_name, value in fields:
        text = _safe_str(value)
        if text != closed_lane_id:
            continue
        stale_rows.append(
            {
                "artifact": artifact,
                "field": field_name,
                "value": text,
            }
        )
    return stale_rows


def build_audit(
    *,
    closed_lane_id: str,
    brainstorm: Dict[str, Any],
    founder_bundle: Dict[str, Any],
    system_split_packet: Dict[str, Any],
    thinking_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    brainstorm_summary = _safe_dict(brainstorm.get("summary"))
    runtime_reasoning_guard_exit_ready = bool(brainstorm_summary.get("runtime_reasoning_guard_exit_ready", False))
    if closed_lane_id == "runtime_reasoning_guard" and not runtime_reasoning_guard_exit_ready:
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "audit_id": "permit_closed_lane_stale_audit_latest",
            "summary": {
                "audit_ready": True,
                "audit_skipped": True,
                "closed_lane_id": closed_lane_id,
                "stale_reference_total": 0,
                "stale_artifact_total": 0,
                "stale_execution_lane_total": 0,
                "stale_parallel_lane_total": 0,
                "stale_primary_lane_total": 0,
                "stale_system_bottleneck_total": 0,
                "stale_prompt_bundle_lane_total": 0,
                "runtime_reasoning_guard_exit_ready": False,
            },
            "stale_artifacts": [],
            "stale_references": [],
        }

    stale_rows: List[Dict[str, str]] = []

    stale_rows.extend(
        _collect_stale_refs(
            artifact="permit_next_action_brainstorm",
            fields=[
                ("summary.execution_lane", brainstorm_summary.get("execution_lane")),
                ("summary.parallel_lane", brainstorm_summary.get("parallel_lane")),
                ("current_execution_lane.id", _safe_dict(brainstorm.get("current_execution_lane")).get("id")),
                ("parallel_brainstorm_lane.id", _safe_dict(brainstorm.get("parallel_brainstorm_lane")).get("id")),
            ],
            closed_lane_id=closed_lane_id,
        )
    )

    founder_summary = _safe_dict(founder_bundle.get("summary"))
    stale_rows.extend(
        _collect_stale_refs(
            artifact="founder_mode_prompt_bundle",
            fields=[
                ("summary.primary_lane_id", founder_summary.get("primary_lane_id")),
                ("primary_execution.id", _safe_dict(founder_bundle.get("primary_execution")).get("id")),
            ],
            closed_lane_id=closed_lane_id,
        )
    )

    system_split_permit = _safe_dict(_safe_dict(system_split_packet.get("tracks")).get("permit"))
    stale_rows.extend(
        _collect_stale_refs(
            artifact="system_split_first_principles_packet",
            fields=[
                ("tracks.permit.current_bottleneck", system_split_permit.get("current_bottleneck")),
            ],
            closed_lane_id=closed_lane_id,
        )
    )

    thinking_summary = _safe_dict(thinking_bundle.get("summary"))
    stale_rows.extend(
        _collect_stale_refs(
            artifact="permit_thinking_prompt_bundle_packet",
            fields=[
                ("summary.lane_id", thinking_summary.get("lane_id")),
                ("summary.founder_primary_lane_id", thinking_summary.get("founder_primary_lane_id")),
                ("summary.current_execution_lane_id", thinking_summary.get("current_execution_lane_id")),
                ("summary.system_current_bottleneck", thinking_summary.get("system_current_bottleneck")),
            ],
            closed_lane_id=closed_lane_id,
        )
    )

    stale_artifacts = sorted({row["artifact"] for row in stale_rows})
    summary = {
        "audit_ready": len(stale_rows) == 0,
        "audit_skipped": False,
        "closed_lane_id": closed_lane_id,
        "stale_reference_total": len(stale_rows),
        "stale_artifact_total": len(stale_artifacts),
        "stale_execution_lane_total": sum(
            1
            for row in stale_rows
            if row["field"] in {"summary.execution_lane", "current_execution_lane.id"}
        ),
        "stale_parallel_lane_total": sum(
            1
            for row in stale_rows
            if row["field"] in {"summary.parallel_lane", "parallel_brainstorm_lane.id"}
        ),
        "stale_primary_lane_total": sum(
            1
            for row in stale_rows
            if row["field"] in {"summary.primary_lane_id", "primary_execution.id"}
        ),
        "stale_system_bottleneck_total": sum(
            1
            for row in stale_rows
            if row["field"] in {"tracks.permit.current_bottleneck", "summary.system_current_bottleneck"}
        ),
        "stale_prompt_bundle_lane_total": sum(
            1
            for row in stale_rows
            if row["field"] in {"summary.lane_id", "summary.founder_primary_lane_id", "summary.current_execution_lane_id"}
        ),
        "runtime_reasoning_guard_exit_ready": runtime_reasoning_guard_exit_ready,
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "audit_id": "permit_closed_lane_stale_audit_latest",
        "summary": summary,
        "stale_artifacts": stale_artifacts,
        "stale_references": stale_rows,
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    lines = [
        "# Permit Closed Lane Stale Audit",
        "",
        f"- audit_ready: `{summary.get('audit_ready', False)}`",
        f"- closed_lane_id: `{summary.get('closed_lane_id', '')}`",
        f"- stale_reference_total: `{summary.get('stale_reference_total', 0)}`",
        f"- stale_artifact_total: `{summary.get('stale_artifact_total', 0)}`",
        f"- stale_execution_lane_total: `{summary.get('stale_execution_lane_total', 0)}`",
        f"- stale_parallel_lane_total: `{summary.get('stale_parallel_lane_total', 0)}`",
        f"- stale_primary_lane_total: `{summary.get('stale_primary_lane_total', 0)}`",
        f"- stale_system_bottleneck_total: `{summary.get('stale_system_bottleneck_total', 0)}`",
        f"- stale_prompt_bundle_lane_total: `{summary.get('stale_prompt_bundle_lane_total', 0)}`",
        "",
        "## Stale References",
    ]
    stale_rows = list(payload.get("stale_references") or [])
    if not stale_rows:
        lines.append("- none")
    else:
        for row in stale_rows:
            item = _safe_dict(row)
            lines.append(
                f"- `{item.get('artifact', '')}` / `{item.get('field', '')}` / `{item.get('value', '')}`"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit stale closed-lane references across permit prompt packets.")
    parser.add_argument("--closed-lane-id", default=DEFAULT_CLOSED_LANE_ID)
    parser.add_argument("--brainstorm", type=Path, default=DEFAULT_BRAINSTORM)
    parser.add_argument("--founder", type=Path, default=DEFAULT_FOUNDER)
    parser.add_argument("--system-split", type=Path, default=DEFAULT_SYSTEM_SPLIT)
    parser.add_argument("--thinking-bundle", type=Path, default=DEFAULT_THINKING_BUNDLE)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_audit(
        closed_lane_id=_safe_str(args.closed_lane_id) or DEFAULT_CLOSED_LANE_ID,
        brainstorm=_load_json(args.brainstorm.expanduser().resolve()),
        founder_bundle=_load_json(args.founder.expanduser().resolve()),
        system_split_packet=_load_json(args.system_split.expanduser().resolve()),
        thinking_bundle=_load_json(args.thinking_bundle.expanduser().resolve()),
    )

    json_output = args.json.expanduser().resolve()
    md_output = args.md.expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0 if bool(_safe_dict(payload.get("summary")).get("audit_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
