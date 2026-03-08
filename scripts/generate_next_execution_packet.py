#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOCUS = ROOT / "logs" / "next_batch_focus_packet_latest.json"
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_SYSTEM_SPLIT = ROOT / "logs" / "system_split_first_principles_packet_latest.json"
DEFAULT_YANGDO_ZERO = ROOT / "logs" / "yangdo_zero_display_recovery_audit_latest.json"
DEFAULT_YANGDO_COPY = ROOT / "logs" / "yangdo_service_copy_packet_latest.json"
DEFAULT_PERMIT_ALIGNMENT = ROOT / "logs" / "permit_service_alignment_audit_latest.json"
DEFAULT_PARTNER_FLOW = ROOT / "logs" / "partner_input_operator_flow_latest.json"
DEFAULT_PLATFORM = ROOT / "logs" / "ai_platform_first_principles_review_latest.json"
DEFAULT_JSON = ROOT / "logs" / "next_execution_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "next_execution_packet_latest.md"


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


def _artifact(path: Path) -> Dict[str, str]:
    return {"path": str(path.resolve()), "name": path.name}


def _build_yangdo_zero_display_plan(
    *,
    selected: Dict[str, Any],
    zero_audit: Dict[str, Any],
    yangdo_copy: Dict[str, Any],
    focus_path: Path,
    zero_audit_path: Path,
    yangdo_copy_path: Path,
) -> Dict[str, Any]:
    zero_summary = _safe_dict(zero_audit.get("summary"))
    copy_summary = _safe_dict(yangdo_copy.get("summary"))
    ready = bool(zero_summary.get("zero_display_guard_ok")) and bool(copy_summary.get("packet_ready"))
    return {
        "execution_ready": ready,
        "bottleneck": "추천 0건 fallback 계약을 공개/상담/시장 브리지 순서로 고정",
        "evidence_points": [
            f"selected_lane_ok={zero_summary.get('selected_lane_ok')}",
            f"zero_display_total={zero_summary.get('zero_display_total')}",
            f"market_bridge_route_ok={zero_summary.get('market_bridge_route_ok')}",
            f"consult_first_ready={zero_summary.get('consult_first_ready')}",
            f"zero_policy_ready={zero_summary.get('zero_policy_ready')}",
        ],
        "success_criteria": [
            "yangdo_zero_display_guard_ok == true",
            "selected lane remains zero_display_recovery_guard",
            "service copy keeps input recovery -> market bridge -> consult ordering",
            "public summary stays safe while consult lane remains available",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_yangdo_service_copy_packet.py",
            "py -3 H:\\auto\\scripts\\generate_yangdo_zero_display_recovery_audit.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(zero_audit_path),
            _artifact(yangdo_copy_path),
        ],
        "next_after_completion": [
            "detail_explainable 단독 업셀 lane의 상품/카피/운영 차등을 더 독립화",
            "추천 집중도 3차에서 top-2/3 반복도와 focus signature 편향을 강화",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_permit_plan(
    *,
    selected: Dict[str, Any],
    permit_alignment: Dict[str, Any],
    focus_path: Path,
    permit_alignment_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(permit_alignment.get("summary"))
    ready = bool(summary.get("alignment_ok"))
    return {
        "execution_ready": ready,
        "bottleneck": "permit 서비스 설명과 lane 차등 공개를 더 선명하게 분리",
        "evidence_points": [
            f"alignment_ok={summary.get('alignment_ok')}",
            f"service_story_ok={summary.get('service_story_ok')}",
            f"lane_positioning_ok={summary.get('lane_positioning_ok')}",
        ],
        "success_criteria": [
            "permit_service_alignment_ok == true",
            "summary_self_check / detail_checklist / manual_review_assist 차이가 더 선명해질 것",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_permit_service_copy_packet.py",
            "py -3 H:\\auto\\scripts\\generate_permit_service_alignment_audit.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(permit_alignment_path),
        ],
        "next_after_completion": [
            "permit 상품 차등을 partner 설명/과금 문구까지 더 세분화",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_platform_plan(
    *,
    selected: Dict[str, Any],
    platform_review: Dict[str, Any],
    focus_path: Path,
    platform_review_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(platform_review.get("summary"))
    return {
        "execution_ready": bool(summary.get("packet_ready")),
        "bottleneck": "public/private publish 분기와 post-publish verifier 단일화",
        "evidence_points": [
            f"packet_ready={summary.get('packet_ready')}",
            f"current_bottleneck={summary.get('current_bottleneck')}",
        ],
        "success_criteria": [
            "publish gate 단일화",
            "post-publish verifier를 운영 패킷에서 직접 읽을 수 있을 것",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_ai_platform_first_principles_review.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(platform_review_path),
        ],
        "next_after_completion": [
            "live 승인 이후 publish/rollback operator flow를 더 줄인다",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def _build_partner_plan(
    *,
    selected: Dict[str, Any],
    partner_flow: Dict[str, Any],
    focus_path: Path,
    partner_flow_path: Path,
) -> Dict[str, Any]:
    summary = _safe_dict(partner_flow.get("summary"))
    return {
        "execution_ready": bool(summary.get("packet_ready")),
        "bottleneck": "partner 입력 3종을 주입하고 activation까지 닫기",
        "evidence_points": [
            f"packet_ready={summary.get('packet_ready')}",
            f"copy_paste_ready={summary.get('copy_paste_ready')}",
        ],
        "success_criteria": [
            "proof_url / api_key / approval 주입 후 dry-run과 apply 흐름이 모두 통과",
        ],
        "verification_commands": [
            "py -3 H:\\auto\\scripts\\generate_partner_input_handoff_packet.py",
            "py -3 H:\\auto\\scripts\\generate_partner_input_operator_flow.py",
            "py -3 H:\\auto\\scripts\\generate_next_batch_focus_packet.py",
        ],
        "artifacts": [
            _artifact(focus_path),
            _artifact(partner_flow_path),
        ],
        "next_after_completion": [
            "partner별 proof/source/AP key 실입력을 받아 activation을 닫는다",
        ],
        "selected_focus": {
            "track": _safe_str(selected.get("track")),
            "lane_id": _safe_str(selected.get("lane_id")),
            "title": _safe_str(selected.get("title")),
            "execution_prompt": _safe_str(selected.get("execution_prompt")),
            "next_move": _safe_str(selected.get("next_move")),
        },
    }


def build_packet(
    *,
    focus_path: Path,
    operations_path: Path,
    system_split_path: Path,
    yangdo_zero_path: Path,
    yangdo_copy_path: Path,
    permit_alignment_path: Path,
    partner_flow_path: Path,
    platform_review_path: Path,
) -> Dict[str, Any]:
    focus = _load_json(focus_path)
    operations = _load_json(operations_path)
    system_split = _load_json(system_split_path)
    yangdo_zero = _load_json(yangdo_zero_path)
    yangdo_copy = _load_json(yangdo_copy_path)
    permit_alignment = _load_json(permit_alignment_path)
    partner_flow = _load_json(partner_flow_path)
    platform_review = _load_json(platform_review_path)

    summary = _safe_dict(focus.get("summary"))
    selected = _safe_dict(focus.get("selected_focus"))
    selected_track = _safe_str(summary.get("selected_track") or selected.get("track"))
    selected_lane_id = _safe_str(summary.get("selected_lane_id") or selected.get("lane_id"))
    split_tracks = _safe_dict(system_split.get("tracks"))
    track_packet = _safe_dict(split_tracks.get(selected_track))
    selected_ready = bool(summary.get("packet_ready")) and bool(selected_track)

    if selected_track == "yangdo":
        execution = _build_yangdo_zero_display_plan(
            selected=selected,
            zero_audit=yangdo_zero,
            yangdo_copy=yangdo_copy,
            focus_path=focus_path,
            zero_audit_path=yangdo_zero_path,
            yangdo_copy_path=yangdo_copy_path,
        )
    elif selected_track == "permit":
        execution = _build_permit_plan(
            selected=selected,
            permit_alignment=permit_alignment,
            focus_path=focus_path,
            permit_alignment_path=permit_alignment_path,
        )
    elif selected_track == "partner":
        execution = _build_partner_plan(
            selected=selected,
            partner_flow=partner_flow,
            focus_path=focus_path,
            partner_flow_path=partner_flow_path,
        )
    else:
        execution = _build_platform_plan(
            selected=selected,
            platform_review=platform_review,
            focus_path=focus_path,
            platform_review_path=platform_review_path,
        )

    decisions = _safe_dict(operations.get("decisions"))
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "packet_ready": selected_ready,
            "selected_track": selected_track,
            "selected_lane_id": selected_lane_id,
            "execution_ready": bool(execution.get("execution_ready")),
            "deferred_candidate_count": len(_safe_list(focus.get("deferred_candidates"))),
        },
        "selected_execution": execution,
        "context": {
            "seoul_live_decision": _safe_str(decisions.get("seoul_live_decision")),
            "partner_activation_decision": _safe_str(decisions.get("partner_activation_decision")),
            "track_goal": _safe_str(track_packet.get("goal")),
            "track_current_bottleneck": _safe_str(track_packet.get("current_bottleneck")),
            "parallel_candidates": _safe_list(focus.get("parallel_candidates")),
        },
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    selected_execution = _safe_dict(payload.get("selected_execution"))
    context = _safe_dict(payload.get("context"))
    lines = [
        "# Next Execution Packet",
        "",
        f"- packet_ready: `{summary.get('packet_ready')}`",
        f"- selected_track: `{summary.get('selected_track')}`",
        f"- selected_lane_id: `{summary.get('selected_lane_id')}`",
        f"- execution_ready: `{summary.get('execution_ready')}`",
        "",
        "## Execution",
        f"- bottleneck: {selected_execution.get('bottleneck')}",
        f"- title: {(_safe_dict(selected_execution.get('selected_focus'))).get('title', '')}",
        f"- next_move: {(_safe_dict(selected_execution.get('selected_focus'))).get('next_move', '')}",
        "",
        "## Evidence",
    ]
    for item in _safe_list(selected_execution.get("evidence_points")):
        lines.append(f"- {item}")
    lines.extend(["", "## Success Criteria"])
    for item in _safe_list(selected_execution.get("success_criteria")):
        lines.append(f"- {item}")
    lines.extend(["", "## Verification Commands"])
    for item in _safe_list(selected_execution.get("verification_commands")):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Context"])
    lines.append(f"- seoul_live_decision: {context.get('seoul_live_decision')}")
    lines.append(f"- partner_activation_decision: {context.get('partner_activation_decision')}")
    lines.append(f"- track_goal: {context.get('track_goal')}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the concrete next execution packet from the selected batch focus.")
    parser.add_argument("--focus", type=Path, default=DEFAULT_FOCUS)
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--system-split", type=Path, default=DEFAULT_SYSTEM_SPLIT)
    parser.add_argument("--yangdo-zero", type=Path, default=DEFAULT_YANGDO_ZERO)
    parser.add_argument("--yangdo-copy", type=Path, default=DEFAULT_YANGDO_COPY)
    parser.add_argument("--permit-alignment", type=Path, default=DEFAULT_PERMIT_ALIGNMENT)
    parser.add_argument("--partner-flow", type=Path, default=DEFAULT_PARTNER_FLOW)
    parser.add_argument("--platform-review", type=Path, default=DEFAULT_PLATFORM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        focus_path=args.focus,
        operations_path=args.operations,
        system_split_path=args.system_split,
        yangdo_zero_path=args.yangdo_zero,
        yangdo_copy_path=args.yangdo_copy,
        permit_alignment_path=args.permit_alignment,
        partner_flow_path=args.partner_flow,
        platform_review_path=args.platform_review,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
