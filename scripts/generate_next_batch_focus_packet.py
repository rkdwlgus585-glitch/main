#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_SYSTEM_SPLIT = ROOT / "logs" / "system_split_first_principles_packet_latest.json"
DEFAULT_YANGDO = ROOT / "logs" / "yangdo_next_action_brainstorm_latest.json"
DEFAULT_PERMIT = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_JSON = ROOT / "logs" / "next_batch_focus_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "next_batch_focus_packet_latest.md"


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


def _resolve_execution_prompt(packet: Dict[str, Any], track_packet: Dict[str, Any]) -> str:
    direct = _safe_str(packet.get("execution_prompt"))
    if direct:
        return direct
    critical = _safe_dict(packet.get("critical_prompts"))
    critical_prompt = _safe_str(critical.get("execution_prompt"))
    if critical_prompt:
        return critical_prompt
    return _safe_str(track_packet.get("execution_prompt"))


def _candidate(*, track: str, lane_id: str, title: str, reason: str, blocked_by: List[str], execution_prompt: str, next_move: str, actionability: str, score: int) -> Dict[str, Any]:
    return {
        "track": track,
        "lane_id": lane_id,
        "title": title,
        "reason": reason,
        "blocked_by": blocked_by,
        "execution_prompt": execution_prompt,
        "next_move": next_move,
        "actionability": actionability,
        "score": score,
    }


def build_packet(*, operations_path: Path, system_split_path: Path, yangdo_path: Path, permit_path: Path) -> Dict[str, Any]:
    operations = _load_json(operations_path)
    system_split = _load_json(system_split_path)
    yangdo = _load_json(yangdo_path)
    permit = _load_json(permit_path)

    decisions = _safe_dict(operations.get("decisions"))
    tracks = _safe_dict(system_split.get("tracks"))
    yangdo_lane = _safe_dict(yangdo.get("current_execution_lane"))
    permit_lane = _safe_dict(permit.get("current_execution_lane"))
    yangdo_parallel = _safe_dict(yangdo.get("parallel_brainstorm_lane"))
    permit_parallel = _safe_dict(permit.get("parallel_brainstorm_lane"))

    platform_blocked = decisions.get("seoul_live_decision") == "awaiting_live_confirmation"
    partner_blocked = decisions.get("partner_activation_decision") == "awaiting_partner_inputs"

    platform_track = _safe_dict(tracks.get("platform"))
    yangdo_track = _safe_dict(tracks.get("yangdo"))
    permit_track = _safe_dict(tracks.get("permit"))

    candidates: List[Dict[str, Any]] = []
    candidates.append(
        _candidate(
            track="yangdo",
            lane_id=_safe_str(yangdo_lane.get("id") or yangdo_track.get("current_bottleneck") or "yangdo_next"),
            title=_safe_str(yangdo_lane.get("title") or "yangdo execution"),
            reason="User-facing value, recommendation explainability, rental differentiation, and patent hardening all improve together.",
            blocked_by=[],
            execution_prompt=_resolve_execution_prompt(yangdo, yangdo_track),
            next_move=_safe_str(yangdo_track.get("next_move") or "Refine market-fit explanation and recommendation exposure."),
            actionability="ready_now",
            score=100,
        )
    )
    candidates.append(
        _candidate(
            track="permit",
            lane_id=_safe_str(permit_lane.get("id") or permit_track.get("current_bottleneck") or "permit_next"),
            title=_safe_str(permit_lane.get("title") or "permit execution"),
            reason="Checklist/detail/manual-review separation is already green enough to push service explanation and rental clarity next.",
            blocked_by=[],
            execution_prompt=_resolve_execution_prompt(permit, permit_track),
            next_move=_safe_str(permit_track.get("next_move") or "Separate checklist detail and manual-review assist more clearly."),
            actionability="ready_now",
            score=85,
        )
    )
    candidates.append(
        _candidate(
            track="platform",
            lane_id=_safe_str(platform_track.get("current_bottleneck") or "platform_publish_gate"),
            title="platform release gate",
            reason="Platform release is important, but the remaining gate is explicit live approval rather than an internal code bottleneck.",
            blocked_by=["confirm_live_yes"] if platform_blocked else [],
            execution_prompt=_safe_str(platform_track.get("execution_prompt")),
            next_move=_safe_str(platform_track.get("next_move") or "Lock publish gate and post-publish verification."),
            actionability="blocked_external" if platform_blocked else "ready_now",
            score=30 if platform_blocked else 90,
        )
    )
    candidates.append(
        _candidate(
            track="partner",
            lane_id="partner_input_operator_flow",
            title="partner input activation closure",
            reason="Partner enablement is structurally ready, but now blocked by real proof URL, API key, and approval inputs.",
            blocked_by=["partner_proof_url", "partner_api_key", "partner_data_source_approval"] if partner_blocked else [],
            execution_prompt="Use the copy-paste handoff packet and operator flow to inject partner inputs and rerun activation.",
            next_move="Inject partner inputs and rerun simulate -> dry-run -> apply.",
            actionability="blocked_external" if partner_blocked else "ready_now",
            score=20 if partner_blocked else 88,
        )
    )

    ranked = sorted(candidates, key=lambda item: (item["actionability"] != "ready_now", -int(item["score"])))
    selected = ranked[0] if ranked else {}
    parallel = [item for item in ranked[1:] if item.get("actionability") == "ready_now"][:2]
    deferred = [item for item in ranked if item.get("actionability") != "ready_now"]

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "packet_ready": bool(selected),
            "selected_track": selected.get("track"),
            "selected_lane_id": selected.get("lane_id"),
            "parallel_candidate_count": len(parallel),
            "deferred_candidate_count": len(deferred),
        },
        "selected_focus": selected,
        "parallel_candidates": parallel,
        "deferred_candidates": deferred,
        "brainstorm_support": {
            "yangdo_parallel_lane": {
                "id": _safe_str(yangdo_parallel.get("id")),
                "title": _safe_str(yangdo_parallel.get("title")),
            },
            "permit_parallel_lane": {
                "id": _safe_str(permit_parallel.get("id")),
                "title": _safe_str(permit_parallel.get("title")),
            },
        },
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    selected = _safe_dict(payload.get("selected_focus"))
    lines = [
        "# Next Batch Focus Packet",
        "",
        f"- packet_ready: `{summary.get('packet_ready')}`",
        f"- selected_track: `{summary.get('selected_track')}`",
        f"- selected_lane_id: `{summary.get('selected_lane_id')}`",
        f"- parallel_candidate_count: `{summary.get('parallel_candidate_count')}`",
        f"- deferred_candidate_count: `{summary.get('deferred_candidate_count')}`",
        "",
        "## Selected Focus",
        f"- track: `{selected.get('track', '')}`",
        f"- lane_id: `{selected.get('lane_id', '')}`",
        f"- title: {selected.get('title', '')}",
        f"- actionability: `{selected.get('actionability', '')}`",
        f"- reason: {selected.get('reason', '')}",
        f"- next_move: {selected.get('next_move', '')}",
        "",
        "## Parallel Candidates",
    ]
    for item in payload.get("parallel_candidates") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"- `{item.get('track')}` / `{item.get('lane_id')}`: {item.get('title')} :: {item.get('next_move')}")
    lines.extend(["", "## Deferred Candidates"])
    for item in payload.get("deferred_candidates") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"- `{item.get('track')}` / `{item.get('lane_id')}` blocked by {', '.join(item.get('blocked_by') or []) or 'none'}")
    return "\\n".join(lines).strip() + "\\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the next actionable batch focus packet.")
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--system-split", type=Path, default=DEFAULT_SYSTEM_SPLIT)
    parser.add_argument("--yangdo", type=Path, default=DEFAULT_YANGDO)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        operations_path=args.operations,
        system_split_path=args.system_split,
        yangdo_path=args.yangdo,
        permit_path=args.permit,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    args.md.write_text(render_markdown(payload), encoding='utf-8')
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
