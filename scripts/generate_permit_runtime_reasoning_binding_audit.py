#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COPY = ROOT / "logs" / "permit_service_copy_packet_latest.json"
DEFAULT_UX = ROOT / "logs" / "permit_service_ux_packet_latest.json"
DEFAULT_CRITICAL = ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.json"
DEFAULT_THINKING = ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.json"
DEFAULT_BRAINSTORM = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_runtime_reasoning_binding_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_runtime_reasoning_binding_audit_latest.md"
EXPECTED_LANE_ID = "runtime_reasoning_guard"


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


def _string_list(value: Any) -> List[str]:
    out: List[str] = []
    for item in _safe_list(value):
        text = _safe_str(item)
        if text and text not in out:
            out.append(text)
    return out


def _contains_keywords(items: List[str], keywords: List[str]) -> bool:
    haystack = " ".join(_string_list(items))
    return all(keyword in haystack for keyword in keywords)


def _operator_story_ready(items: List[str]) -> bool:
    texts = _string_list(items)
    if not texts:
        return False
    haystack = " ".join(texts).lower()
    structural_tokens = ("lane", "cta", "manual", "review", "checklist", "detail")
    return any(token in haystack for token in structural_tokens)


def _truthy_lane_set(*values: Any) -> set[str]:
    lanes: set[str] = set()
    for value in values:
        text = _safe_str(value)
        if text:
            lanes.add(text)
    return lanes


def build_packet(
    *,
    copy_path: Path,
    ux_path: Path,
    critical_path: Path,
    thinking_path: Path,
    brainstorm_path: Path,
) -> Dict[str, Any]:
    copy_packet = _load_json(copy_path)
    ux_packet = _load_json(ux_path)
    critical_packet = _load_json(critical_path)
    thinking_packet = _load_json(thinking_path)
    brainstorm_packet = _load_json(brainstorm_path)

    copy_summary = _safe_dict(copy_packet.get("summary"))
    copy_ladder = _safe_dict(copy_packet.get("lane_ladder"))
    copy_next_actions = _string_list(copy_packet.get("next_actions"))
    ux_summary = _safe_dict(ux_packet.get("summary"))
    public_summary = _safe_dict(ux_packet.get("public_summary_experience"))
    detail_summary = _safe_dict(ux_packet.get("detail_checklist_experience"))
    assist_summary = _safe_dict(ux_packet.get("manual_review_assist_experience"))
    critical_summary = _safe_dict(critical_packet.get("summary"))
    thinking_summary = _safe_dict(thinking_packet.get("summary"))
    brainstorm_summary = _safe_dict(brainstorm_packet.get("summary"))
    current_execution_lane = _safe_dict(brainstorm_packet.get("current_execution_lane"))
    founder_primary_lane_id = _safe_str(critical_summary.get("founder_primary_lane_id"))
    founder_parallel_lane_id = _safe_str(thinking_summary.get("founder_parallel_lane_id"))
    successor_execution_lane_id = _safe_str(brainstorm_summary.get("execution_lane")) or _safe_str(current_execution_lane.get("id"))
    allowed_successor_lane_ids = set(_string_list(thinking_summary.get("allowed_successor_lane_ids")))

    critical_lane_id = _safe_str(critical_summary.get("lane_id"))
    thinking_lane_id = _safe_str(thinking_summary.get("lane_id"))
    lane_id = critical_lane_id or thinking_lane_id or EXPECTED_LANE_ID

    detail_cta = _safe_str(detail_summary.get("cta_primary_label"))
    assist_cta = _safe_str(assist_summary.get("cta_primary_label"))
    public_cta = _safe_str(public_summary.get("cta_primary_label"))
    detail_offerings = set(_string_list(detail_summary.get("allowed_offerings")))
    assist_offerings = set(_string_list(assist_summary.get("allowed_offerings")))

    direct_guard_mode_ok = (
        lane_id == EXPECTED_LANE_ID
        and critical_lane_id == EXPECTED_LANE_ID
        and founder_primary_lane_id in {"", EXPECTED_LANE_ID}
    )
    successor_transition_ok = bool(successor_execution_lane_id) and successor_execution_lane_id != EXPECTED_LANE_ID
    successor_family = set(allowed_successor_lane_ids)
    if thinking_lane_id and thinking_lane_id != EXPECTED_LANE_ID:
        successor_family.add(thinking_lane_id)
    successor_anchor_ok = bool(thinking_lane_id) and thinking_lane_id != EXPECTED_LANE_ID
    successor_execution_ok = successor_execution_lane_id in {"", thinking_lane_id}
    successor_critical_ok = critical_lane_id in successor_family if critical_lane_id else False
    founder_lane_candidates = _truthy_lane_set(founder_primary_lane_id, founder_parallel_lane_id)
    successor_founder_ok = (
        any(candidate in (_truthy_lane_set(thinking_lane_id) | successor_family) for candidate in founder_lane_candidates)
        if founder_lane_candidates
        else successor_critical_ok
    )
    runtime_lane_match_ok = direct_guard_mode_ok or (
        successor_anchor_ok
        and successor_execution_ok
        and successor_critical_ok
        and successor_founder_ok
    )
    cta_split_ok = bool(public_cta and detail_cta and assist_cta) and len({public_cta, detail_cta, assist_cta}) == 3
    offering_split_ok = bool(detail_offerings) and bool(assist_offerings) and detail_offerings != assist_offerings
    ladder_split_ok = _safe_str(_safe_dict(copy_ladder.get("detail_checklist")).get("upgrade_target")) == "manual_review_assist"
    operator_story_ok = _operator_story_ready(copy_next_actions)
    release_surface_ok = (
        _safe_str(ux_summary.get("service_flow_policy")) == "public_summary_then_checklist_or_manual_review"
        and bool(public_summary)
        and bool(detail_summary)
        and bool(assist_summary)
    )
    runtime_binding_ok = (
        bool(critical_summary.get("packet_ready"))
        and bool(thinking_summary.get("packet_ready"))
        and bool(thinking_summary.get("runtime_target_ready"))
        and runtime_lane_match_ok
    )
    service_binding_ok = (
        bool(copy_summary.get("packet_ready"))
        and bool(ux_summary.get("packet_ready"))
        and cta_split_ok
        and offering_split_ok
        and ladder_split_ok
        and release_surface_ok
    )
    operator_binding_ok = (
        bool(critical_summary.get("operator_surface_ready"))
        and bool(thinking_summary.get("operator_target_ready"))
        and operator_story_ok
    )
    release_binding_ok = (
        bool(critical_summary.get("release_surface_ready"))
        and bool(thinking_summary.get("release_target_ready"))
        and release_surface_ok
    )

    issues: List[str] = []
    if not runtime_lane_match_ok:
        issues.append("runtime_reasoning_lane_mismatch")
    if not cta_split_ok:
        issues.append("service_cta_split_missing")
    if not offering_split_ok:
        issues.append("detail_assist_offering_split_missing")
    if not ladder_split_ok:
        issues.append("detail_to_assist_upgrade_target_missing")
    if not operator_story_ok:
        issues.append("operator_story_keywords_missing")
    if not release_surface_ok:
        issues.append("release_surface_contract_incomplete")

    packet_ready = runtime_binding_ok and service_binding_ok and operator_binding_ok and release_binding_ok and not issues
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_runtime_reasoning_binding_audit_latest",
        "summary": {
            "packet_ready": packet_ready,
            "lane_id": lane_id or EXPECTED_LANE_ID,
            "expected_lane_id": EXPECTED_LANE_ID,
            "critical_lane_id": critical_lane_id,
            "thinking_lane_id": thinking_lane_id,
            "runtime_binding_ok": runtime_binding_ok,
            "successor_transition_ok": successor_transition_ok,
            "direct_guard_mode_ok": direct_guard_mode_ok,
            "successor_anchor_ok": successor_anchor_ok,
            "successor_execution_ok": successor_execution_ok,
            "successor_critical_ok": successor_critical_ok,
            "successor_founder_ok": successor_founder_ok,
            "service_binding_ok": service_binding_ok,
            "operator_binding_ok": operator_binding_ok,
            "release_binding_ok": release_binding_ok,
            "cta_split_ok": cta_split_ok,
            "offering_split_ok": offering_split_ok,
            "issue_count": len(issues),
        },
        "contracts": {
            "lane_match": {
                "critical_prompt_surface_lane_id": critical_lane_id,
                "thinking_prompt_bundle_lane_id": thinking_lane_id,
                "founder_primary_lane_id": founder_primary_lane_id,
                "founder_parallel_lane_id": founder_parallel_lane_id,
                "brainstorm_execution_lane_id": _safe_str(brainstorm_summary.get("execution_lane")),
                "brainstorm_current_execution_lane_id": _safe_str(current_execution_lane.get("id")),
                "allowed_successor_lane_ids": sorted(successor_family),
            },
            "cta_split": {
                "public_summary": public_cta,
                "detail_checklist": detail_cta,
                "manual_review_assist": assist_cta,
            },
            "offering_split": {
                "detail_checklist": sorted(detail_offerings),
                "manual_review_assist": sorted(assist_offerings),
            },
            "operator_story": {
                "next_actions": copy_next_actions,
                "keyword_contract": ["lane", "cta", "manual-review or checklist split"],
            },
        },
        "issues": issues,
        "next_actions": [
            "Keep runtime reasoning guard as the single permit execution lane until service, release, and operator surfaces stop drifting.",
            "Do not collapse detail checklist and manual review assist into a shared CTA or a shared offering bucket.",
            "Treat this audit as the canonical proof that permit reasoning survives runtime, service, and operator handoff without reinterpretation.",
        ],
        "artifacts": {
            "permit_service_copy_packet": str(copy_path.resolve()),
            "permit_service_ux_packet": str(ux_path.resolve()),
            "permit_critical_prompt_surface_packet": str(critical_path.resolve()),
            "permit_thinking_prompt_bundle_packet": str(thinking_path.resolve()),
            "permit_next_action_brainstorm": str(brainstorm_path.resolve()),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    contracts = _safe_dict(payload.get("contracts"))
    lines = [
        "# Permit Runtime Reasoning Binding Audit",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- lane_id: {summary.get('lane_id')}",
        f"- expected_lane_id: {summary.get('expected_lane_id')}",
        f"- critical_lane_id: {summary.get('critical_lane_id')}",
        f"- thinking_lane_id: {summary.get('thinking_lane_id')}",
        f"- runtime_binding_ok: {summary.get('runtime_binding_ok')}",
        f"- successor_transition_ok: {summary.get('successor_transition_ok')}",
        f"- direct_guard_mode_ok: {summary.get('direct_guard_mode_ok')}",
        f"- successor_anchor_ok: {summary.get('successor_anchor_ok')}",
        f"- successor_execution_ok: {summary.get('successor_execution_ok')}",
        f"- successor_critical_ok: {summary.get('successor_critical_ok')}",
        f"- successor_founder_ok: {summary.get('successor_founder_ok')}",
        f"- service_binding_ok: {summary.get('service_binding_ok')}",
        f"- operator_binding_ok: {summary.get('operator_binding_ok')}",
        f"- release_binding_ok: {summary.get('release_binding_ok')}",
        f"- cta_split_ok: {summary.get('cta_split_ok')}",
        f"- offering_split_ok: {summary.get('offering_split_ok')}",
        f"- issue_count: {summary.get('issue_count')}",
        "",
        "## Lane Match",
    ]
    for key, value in _safe_dict(contracts.get("lane_match")).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## CTA Split"])
    for key, value in _safe_dict(contracts.get("cta_split")).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Offering Split"])
    for key, value in _safe_dict(contracts.get("offering_split")).items():
        lines.append(f"- {key}: {', '.join(value) if isinstance(value, list) else value}")
    lines.extend(["", "## Issues"])
    for item in _safe_list(payload.get("issues")):
        lines.append(f"- {item}")
    if not _safe_list(payload.get("issues")):
        lines.append("- (none)")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit permit runtime reasoning lane binding across service and operator surfaces.")
    parser.add_argument("--copy", type=Path, default=DEFAULT_COPY)
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--critical", type=Path, default=DEFAULT_CRITICAL)
    parser.add_argument("--thinking", type=Path, default=DEFAULT_THINKING)
    parser.add_argument("--brainstorm", type=Path, default=DEFAULT_BRAINSTORM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        copy_path=args.copy,
        ux_path=args.ux,
        critical_path=args.critical,
        thinking_path=args.thinking,
        brainstorm_path=args.brainstorm,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool(_safe_dict(payload.get("summary")).get("packet_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
