#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPARABLE = ROOT / "logs" / "yangdo_comparable_selection_overall_latest.json"
DEFAULT_BRIDGE = ROOT / "logs" / "yangdo_recommendation_bridge_packet_latest.json"
DEFAULT_SERVICE_COPY = ROOT / "logs" / "yangdo_service_copy_packet_latest.json"
DEFAULT_UX = ROOT / "logs" / "yangdo_recommendation_ux_packet_latest.json"
DEFAULT_CONTRACT = ROOT / "logs" / "yangdo_recommendation_contract_audit_latest.json"
DEFAULT_BRAINSTORM = ROOT / "logs" / "yangdo_next_action_brainstorm_latest.json"
DEFAULT_ATTORNEY = ROOT / "logs" / "attorney_handoff_latest.json"
DEFAULT_JSON = ROOT / "logs" / "yangdo_zero_display_recovery_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_zero_display_recovery_audit_latest.md"


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


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _contains_any(rows: List[str], keywords: List[str]) -> bool:
    lowered_rows = [str(row or "").strip().lower() for row in rows]
    return any(keyword.lower() in row for row in lowered_rows for keyword in keywords)


def build_yangdo_zero_display_recovery_audit(
    *,
    comparable_path: Path,
    bridge_path: Path,
    service_copy_path: Path,
    ux_path: Path,
    contract_path: Path,
    brainstorm_path: Path,
    attorney_path: Path,
) -> Dict[str, Any]:
    comparable = _load_json(comparable_path)
    bridge = _load_json(bridge_path)
    service_copy = _load_json(service_copy_path)
    ux_packet = _load_json(ux_path)
    contract = _load_json(contract_path)
    brainstorm = _load_json(brainstorm_path)
    attorney = _load_json(attorney_path)

    comparable_zero_display_total = int(comparable.get("records_zero_display") or 0)
    bridge_public = _as_dict(bridge.get("public_summary_contract"))
    bridge_market = _as_dict(bridge.get("market_bridge_policy"))
    service_summary = _as_dict(service_copy.get("summary"))
    zero_display_policy = _as_dict(service_copy.get("zero_display_recovery_policy"))
    cta_ladder = _as_dict(service_copy.get("cta_ladder"))
    consult_detail = _as_dict(ux_packet.get("consult_detail_experience"))
    contract_summary = _as_dict(contract.get("summary"))
    brainstorm_summary = _as_dict(brainstorm.get("summary"))
    brainstorm_lane = _as_dict(brainstorm.get("current_execution_lane"))
    track_a = next((row for row in attorney.get("tracks", []) if isinstance(row, dict) and row.get("track_id") == "A"), {})
    track_a_position = _as_dict(track_a.get("attorney_position"))

    consult_target = str(_as_dict(cta_ladder.get("secondary_consult")).get("target") or "")
    market_target = str(_as_dict(cta_ladder.get("primary_market_bridge")).get("target") or "")
    claim_focus = _as_list(track_a_position.get("claim_focus") or track_a.get("claim_focus"))
    commercial_positioning = _as_list(track_a_position.get("commercial_positioning") or track_a.get("commercial_positioning"))

    lane_selected = str(brainstorm_lane.get("id") or "") == "zero_display_recovery_guard"
    runtime_ready = bool(brainstorm_summary.get("zero_recovery_ready"))
    contract_policy_ok = bool(contract_summary.get("contract_ok"))
    market_bridge_route_ok = str(bridge_market.get("service_flow_policy") or "") == "public_summary_then_market_or_consult"
    consult_first_ready = bool(service_summary.get("low_precision_consult_first_ready")) and "/consult?intent=yangdo" in consult_target
    zero_policy_ready = bool(zero_display_policy.get("policy_ready"))
    market_cta_ready = "/mna-market" in market_target and "/mna-market" in str(_as_dict(bridge_public.get("primary_cta")).get("target") or "")
    consult_lane_ready = bool(consult_detail.get("allowed_offerings")) and bool(consult_detail.get("detail_axes"))
    patent_hook_ready = _contains_any(
        claim_focus + commercial_positioning,
        [
            "공개 등급",
            "시장 브리지",
            "상담형 상세",
            "fallback",
            "추천 요약 필드",
        ],
    )

    guard_ready = all(
        [
            comparable_zero_display_total > 0,
            runtime_ready,
            contract_policy_ok,
            market_bridge_route_ok,
            consult_first_ready,
            zero_policy_ready,
            market_cta_ready,
            consult_lane_ready,
            patent_hook_ready,
        ]
    )
    selected_lane_guard_ok = guard_ready and lane_selected

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_zero_display_recovery_audit_latest",
        "summary": {
            "packet_ready": True,
            "zero_display_total": comparable_zero_display_total,
            "selected_lane_ok": lane_selected,
            "selected_lane_guard_ok": selected_lane_guard_ok,
            "runtime_ready": runtime_ready,
            "contract_policy_ok": contract_policy_ok,
            "market_bridge_route_ok": market_bridge_route_ok,
            "consult_first_ready": consult_first_ready,
            "zero_policy_ready": zero_policy_ready,
            "market_cta_ready": market_cta_ready,
            "consult_lane_ready": consult_lane_ready,
            "patent_hook_ready": patent_hook_ready,
            "zero_display_guard_ok": guard_ready,
        },
        "guard_contract": {
            "trigger": "recommended_count == 0",
            "selected_lane_id": str(brainstorm_lane.get("id") or ""),
            "selected_lane_guard_ok": selected_lane_guard_ok,
            "service_flow_policy": str(bridge_market.get("service_flow_policy") or ""),
            "market_cta_target": market_target,
            "consult_cta_target": consult_target,
            "zero_display_policy": zero_display_policy,
        },
        "evidence": {
            "brainstorm_summary": brainstorm_summary,
            "service_copy_summary": service_summary,
            "contract_summary": contract_summary,
            "consult_detail_experience": consult_detail,
        },
        "next_actions": [
            "추천 0건에서는 입력 보강 -> 시장 흐름 보기 -> 상담형 상세의 순서를 유지합니다.",
            "추천 0건과 보조 검토가 겹치면 상담형 상세 CTA를 더 강하게 노출하는지 다음 UX 실험에서 확인합니다.",
            "특수 업종 분할·합병 입력에서 추천 0건이 나오면 상담형 상세를 더 앞세우는 설명을 추가 검토합니다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = _as_dict(payload.get("summary"))
    guard_contract = _as_dict(payload.get("guard_contract"))
    lines = [
        "# Yangdo Zero Display Recovery Audit",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- zero_display_total: {summary.get('zero_display_total')}",
        f"- selected_lane_ok: {summary.get('selected_lane_ok')}",
        f"- selected_lane_guard_ok: {summary.get('selected_lane_guard_ok')}",
        f"- runtime_ready: {summary.get('runtime_ready')}",
        f"- contract_policy_ok: {summary.get('contract_policy_ok')}",
        f"- market_bridge_route_ok: {summary.get('market_bridge_route_ok')}",
        f"- consult_first_ready: {summary.get('consult_first_ready')}",
        f"- zero_policy_ready: {summary.get('zero_policy_ready')}",
        f"- market_cta_ready: {summary.get('market_cta_ready')}",
        f"- consult_lane_ready: {summary.get('consult_lane_ready')}",
        f"- patent_hook_ready: {summary.get('patent_hook_ready')}",
        f"- zero_display_guard_ok: {summary.get('zero_display_guard_ok')}",
        "",
        "## Guard Contract",
        f"- selected_lane_id: {guard_contract.get('selected_lane_id')}",
        f"- selected_lane_guard_ok: {guard_contract.get('selected_lane_guard_ok')}",
        f"- service_flow_policy: {guard_contract.get('service_flow_policy')}",
        f"- market_cta_target: {guard_contract.get('market_cta_target')}",
        f"- consult_cta_target: {guard_contract.get('consult_cta_target')}",
        "",
        "## Next Actions",
    ]
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the yangdo zero-display recovery guard contract.")
    parser.add_argument("--comparable", type=Path, default=DEFAULT_COMPARABLE)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--service-copy", type=Path, default=DEFAULT_SERVICE_COPY)
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--brainstorm", type=Path, default=DEFAULT_BRAINSTORM)
    parser.add_argument("--attorney", type=Path, default=DEFAULT_ATTORNEY)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_zero_display_recovery_audit(
        comparable_path=args.comparable,
        bridge_path=args.bridge,
        service_copy_path=args.service_copy,
        ux_path=args.ux,
        contract_path=args.contract,
        brainstorm_path=args.brainstorm,
        attorney_path=args.attorney,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
