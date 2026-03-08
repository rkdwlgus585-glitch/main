#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_BRAINSTORM = ROOT / "logs" / "yangdo_next_action_brainstorm_latest.json"
DEFAULT_ZERO_DISPLAY = ROOT / "logs" / "yangdo_zero_display_recovery_audit_latest.json"
DEFAULT_PUBLIC_LANGUAGE = ROOT / "logs" / "yangdo_public_language_audit_latest.json"
DEFAULT_FOUNDER_CHAIN = ROOT / "logs" / "founder_execution_chain_latest.json"
DEFAULT_NEXT_EXECUTION = ROOT / "logs" / "next_execution_packet_latest.json"
DEFAULT_BRIDGE = ROOT / "logs" / "yangdo_kr_bridge_latest.json"
DEFAULT_SERVICE_COPY = ROOT / "logs" / "yangdo_service_copy_packet_latest.json"
DEFAULT_JSON = ROOT / "logs" / "yangdo_test_thread_handoff_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_test_thread_handoff_latest.md"


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


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, str):
        text = value.strip()
        if text:
            yield text


def _extract_live_urls(bridge_payload: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for text in _iter_strings(bridge_payload):
        if text.startswith("http") and "yangdo" in text.lower() and text not in out:
            out.append(text)
    return out


def _pick_customer_live_url(bridge_payload: Dict[str, Any]) -> str:
    candidates = _extract_live_urls(bridge_payload)
    preferred = [url for url in candidates if "yangdo-ai-customer" in url]
    if preferred:
        return preferred[0]
    return candidates[0] if candidates else "https://seoulmna.kr/yangdo-ai-customer-10/"


def _implemented_rules() -> List[Dict[str, str]]:
    return [
        {
            "id": "special-sector-reorg-required",
            "title": "전기·정보통신·소방은 포괄 / 분할·합병 선택이 필수",
            "detail": "세 업종은 양도 구조를 고르지 않으면 계산을 막고, 구조 선택에 따라 입력 규칙과 안내 문구가 달라진다.",
        },
        {
            "id": "special-sector-split-exclusions",
            "title": "분할·합병은 최근 3년 실적과 자본금 중심",
            "detail": "전기·정보통신·소방에서 분할·합병이면 최근 3년 실적 합계와 자본금이 중심 축이고, 시평·이익잉여금·외부신용·부채비율·유동비율은 가격 반영에서 제외된다.",
        },
        {
            "id": "special-sector-balance-separated",
            "title": "전기·정보통신·소방 공제조합 잔액은 별도 참고",
            "detail": "세 업종은 공제조합 잔액을 가격과 분리해 보여주며, 양도가 영향은 0으로 고정한다.",
        },
        {
            "id": "autoloop-followup",
            "title": "추천 0건 / 1건은 보강 버튼과 자동 재계산 루프 사용",
            "detail": "저표본이나 단일추천이면 가장 영향 큰 입력칸으로 복귀시키고, 값 수정 후 재계산을 자동으로 한 번 이어준다.",
        },
        {
            "id": "mobile-recommend-first",
            "title": "모바일은 추천 매물 우선 노출",
            "detail": "모바일에서는 근거 표를 기본 접힘으로 두고, 추천 카드와 보강 CTA가 먼저 보이도록 결과 배치를 줄였다.",
        },
        {
            "id": "recommendation-order",
            "title": "추천 정렬은 점수 우선, 번호대는 근소 차이 fallback",
            "detail": "업종·실적·가격대 적합도가 우선이고, 7천/6천/5천 번호대는 점수가 거의 비슷할 때만 fallback으로 사용한다.",
        },
    ]


def build_packet(
    *,
    operations_path: Path,
    brainstorm_path: Path,
    zero_display_path: Path,
    public_language_path: Path,
    founder_chain_path: Path,
    next_execution_path: Path,
    bridge_path: Path,
    service_copy_path: Path,
) -> Dict[str, Any]:
    operations = _load_json(operations_path)
    brainstorm = _load_json(brainstorm_path)
    zero_display = _load_json(zero_display_path)
    public_language = _load_json(public_language_path)
    founder_chain = _load_json(founder_chain_path)
    next_execution = _load_json(next_execution_path)
    bridge = _load_json(bridge_path)
    service_copy = _load_json(service_copy_path)

    ops_decisions = _safe_dict(operations.get("decisions"))
    ops_summaries = _safe_dict(operations.get("summaries"))
    brainstorm_summary = _safe_dict(brainstorm.get("summary"))
    zero_display_summary = _safe_dict(zero_display.get("summary"))
    public_language_summary = _safe_dict(public_language.get("summary"))
    founder_summary = _safe_dict(founder_chain.get("summary"))
    next_execution_summary = _safe_dict(next_execution.get("summary"))
    service_copy_summary = _safe_dict(service_copy.get("summary"))
    service_copy_hero = _safe_dict(service_copy.get("hero"))
    service_copy_cta = _safe_dict(service_copy.get("cta_ladder"))

    live_customer_url = _pick_customer_live_url(bridge)
    primary_market_bridge = _safe_dict(service_copy_cta.get("primary_market_bridge"))
    secondary_consult = _safe_dict(service_copy_cta.get("secondary_consult"))

    packet = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_test_thread_handoff_latest",
        "target_thread": "양도양수 테스트 스레드",
        "purpose": "양도양수 테스트 스레드가 이전 대화 맥락 없이도 즉시 이어서 작업할 수 있도록 현재 상태를 한 번에 넘기는 handoff 패킷",
        "workspace": {
            "primary_path": "H:\\auto",
            "tool_compatible_alias": str(ROOT),
            "note": "도구 접근은 C 경로 정션을 써도 되고, 실제 워크스페이스는 H:\\auto 기준으로 유지한다.",
        },
        "live_service": {
            "customer_url": live_customer_url,
            "service_slug": _safe_str(service_copy_summary.get("service_slug") or "/yangdo"),
            "platform_host": _safe_str(service_copy_summary.get("platform_host") or "seoulmna.kr"),
            "listing_host": _safe_str(service_copy_summary.get("listing_host") or "seoulmna.co.kr"),
            "primary_market_bridge_cta": _safe_str(primary_market_bridge.get("label")),
            "primary_market_bridge_target": _safe_str(primary_market_bridge.get("target")),
            "secondary_consult_cta": _safe_str(secondary_consult.get("label")),
            "secondary_consult_target": _safe_str(secondary_consult.get("target")),
        },
        "current_state": {
            "yangdo_prompt_loop_execution_lane": _safe_str(
                ops_decisions.get("yangdo_prompt_loop_execution_lane") or brainstorm_summary.get("execution_lane")
            ),
            "yangdo_prompt_loop_parallel_lane": _safe_str(
                ops_decisions.get("yangdo_prompt_loop_parallel_lane") or brainstorm_summary.get("parallel_lane")
            ),
            "global_next_execution_track": _safe_str(
                ops_decisions.get("next_execution_track") or next_execution_summary.get("selected_track")
            ),
            "global_next_execution_lane_id": _safe_str(
                ops_decisions.get("next_execution_lane_id") or next_execution_summary.get("selected_lane_id")
            ),
            "founder_execution_converged": bool(founder_summary.get("focus_matches_execution")),
            "yangdo_public_language_ready": bool(
                ops_decisions.get("yangdo_public_language_ready") or public_language_summary.get("public_language_ready")
            ),
            "yangdo_zero_display_guard_ok": bool(
                ops_decisions.get("yangdo_zero_display_guard_ok") or zero_display_summary.get("zero_display_guard_ok")
            ),
            "yangdo_autoloop_ready": bool(brainstorm_summary.get("autoloop_ready")),
            "yangdo_public_language_remaining_phrase_count": int(
                ops_decisions.get("yangdo_public_language_remaining_phrase_count")
                or public_language_summary.get("remaining_phrase_count", 0)
                or 0
            ),
            "yangdo_one_or_less_display_total": int(brainstorm_summary.get("one_or_less_display_total", 0) or 0),
            "yangdo_zero_display_total": int(
                zero_display_summary.get("zero_display_total")
                or brainstorm_summary.get("zero_display_total", 0)
                or 0
            ),
            "yangdo_avg_display_neighbors": round(_safe_float(brainstorm_summary.get("avg_display_neighbors")), 4),
            "yangdo_special_sector_scenario_total": int(brainstorm_summary.get("special_sector_scenario_total", 0) or 0),
        },
        "implemented_rules": _implemented_rules(),
        "active_artifacts": {
            "operations_packet": str(operations_path.resolve()),
            "brainstorm_packet": str(brainstorm_path.resolve()),
            "zero_display_audit": str(zero_display_path.resolve()),
            "public_language_audit": str(public_language_path.resolve()),
            "founder_execution_chain": str(founder_chain_path.resolve()),
            "next_execution_packet": str(next_execution_path.resolve()),
            "kr_bridge_log": str(bridge_path.resolve()),
            "service_copy_packet": str(service_copy_path.resolve()),
            "critical_prompt_doc": str((ROOT / "docs" / "yangdo_critical_thinking_prompt.md").resolve()),
            "main_ui_source": str((ROOT / "yangdo_calculator.py").resolve()),
            "recommendation_engine_source": str((ROOT / "core_engine" / "yangdo_listing_recommender.py").resolve()),
        },
        "thread_boot_prompt": (
            "이 스레드는 양도양수 테스트 전용이다. "
            "현재 양도양수는 parallel lane `prompt_loop_operationalization`으로 유지 중이며, "
            "전기·정보통신·소방 특수 규칙, 0건/1건 autoloop, 추천 정렬 가드, 공개 문구 평문화 상태를 기준으로 이어간다. "
            "permit lane으로 확장하지 말고, 양도양수 테스트·QA·정밀도·CTA 복구율 개선에만 집중한다."
        ),
        "next_work": [
            {
                "priority": "P1",
                "lane": "prompt_loop_operationalization",
                "title": "0건 / 1건 보강 버튼 이후 실제 후보 복구율 usage log 추적",
                "why": "현재 autoloop는 작동하지만, 어떤 보강이 실제로 후보 복구에 가장 잘 먹히는지 운영 로그로 아직 닫지 못했다.",
            },
            {
                "priority": "P2",
                "lane": "prompt_loop_operationalization",
                "title": "저표본 CTA 우선순위의 업종별 정밀 조정",
                "why": "일반 업종과 전기·정보통신·소방의 보강 우선순위가 더 세밀하게 나뉠 여지가 있다.",
            },
            {
                "priority": "P3",
                "lane": "prompt_loop_operationalization",
                "title": "추천 카드와 결과 카드 사이 공개 문구 drift 재감시",
                "why": "현재 public language는 green이지만, 다음 UI 수정 때 사무식 표현이 재유입될 수 있다.",
            },
        ],
        "service_story": {
            "hero_title": _safe_str(service_copy_hero.get("title")),
            "hero_body": _safe_str(service_copy_hero.get("body")),
            "service_copy_ready": bool(service_copy_summary.get("service_copy_ready")),
            "market_bridge_story_ready": bool(service_copy_summary.get("market_bridge_story_ready")),
            "market_fit_interpretation_ready": bool(service_copy_summary.get("market_fit_interpretation_ready")),
            "lane_stories_ready": bool(service_copy_summary.get("lane_stories_ready")),
        },
        "inheritance_note": "직접 다른 스레드에 메모리를 주입하는 기능 대신, 이 handoff packet과 메모리 관찰값을 다음 양도양수 테스트 스레드의 단일 기준으로 사용한다.",
    }
    return packet


def render_markdown(packet: Dict[str, Any]) -> str:
    workspace = _safe_dict(packet.get("workspace"))
    live_service = _safe_dict(packet.get("live_service"))
    current_state = _safe_dict(packet.get("current_state"))
    service_story = _safe_dict(packet.get("service_story"))

    lines: List[str] = []
    lines.append("# Yangdo Test Thread Handoff")
    lines.append("")
    lines.append(f"- target_thread: {packet.get('target_thread')}")
    lines.append(f"- generated_at: {packet.get('generated_at')}")
    lines.append(f"- purpose: {packet.get('purpose')}")
    lines.append("")
    lines.append("## Workspace")
    lines.append(f"- primary_path: {workspace.get('primary_path')}")
    lines.append(f"- tool_compatible_alias: {workspace.get('tool_compatible_alias')}")
    lines.append(f"- note: {workspace.get('note')}")
    lines.append("")
    lines.append("## Live Service")
    lines.append(f"- customer_url: {live_service.get('customer_url')}")
    lines.append(f"- service_slug: {live_service.get('service_slug')}")
    lines.append(f"- platform_host: {live_service.get('platform_host')}")
    lines.append(f"- listing_host: {live_service.get('listing_host')}")
    lines.append(f"- primary_market_bridge_cta: {live_service.get('primary_market_bridge_cta')}")
    lines.append(f"- secondary_consult_cta: {live_service.get('secondary_consult_cta')}")
    lines.append("")
    lines.append("## Current State")
    for key in (
        "yangdo_prompt_loop_execution_lane",
        "yangdo_prompt_loop_parallel_lane",
        "global_next_execution_track",
        "global_next_execution_lane_id",
        "founder_execution_converged",
        "yangdo_public_language_ready",
        "yangdo_zero_display_guard_ok",
        "yangdo_autoloop_ready",
        "yangdo_public_language_remaining_phrase_count",
        "yangdo_one_or_less_display_total",
        "yangdo_zero_display_total",
        "yangdo_avg_display_neighbors",
        "yangdo_special_sector_scenario_total",
    ):
        lines.append(f"- {key}: {current_state.get(key)}")
    lines.append("")
    lines.append("## Implemented Rules")
    for item in packet.get("implemented_rules") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('title')}: {item.get('detail')}")
    lines.append("")
    lines.append("## Service Story")
    lines.append(f"- hero_title: {service_story.get('hero_title')}")
    lines.append(f"- service_copy_ready: {service_story.get('service_copy_ready')}")
    lines.append(f"- market_bridge_story_ready: {service_story.get('market_bridge_story_ready')}")
    lines.append(f"- market_fit_interpretation_ready: {service_story.get('market_fit_interpretation_ready')}")
    lines.append(f"- lane_stories_ready: {service_story.get('lane_stories_ready')}")
    lines.append("")
    lines.append("## Next Work")
    for item in packet.get("next_work") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('priority')} / {item.get('lane')}: {item.get('title')} ({item.get('why')})")
    lines.append("")
    lines.append("## Thread Boot Prompt")
    lines.append(packet.get("thread_boot_prompt") or "")
    lines.append("")
    lines.append("## Active Artifacts")
    for key, value in _safe_dict(packet.get("active_artifacts")).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append(f"- inheritance_note: {packet.get('inheritance_note')}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the canonical handoff packet for the Yangdo test thread")
    parser.add_argument("--operations", default=str(DEFAULT_OPERATIONS))
    parser.add_argument("--brainstorm", default=str(DEFAULT_BRAINSTORM))
    parser.add_argument("--zero-display", default=str(DEFAULT_ZERO_DISPLAY))
    parser.add_argument("--public-language", default=str(DEFAULT_PUBLIC_LANGUAGE))
    parser.add_argument("--founder-chain", default=str(DEFAULT_FOUNDER_CHAIN))
    parser.add_argument("--next-execution", default=str(DEFAULT_NEXT_EXECUTION))
    parser.add_argument("--bridge", default=str(DEFAULT_BRIDGE))
    parser.add_argument("--service-copy", default=str(DEFAULT_SERVICE_COPY))
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--md", default=str(DEFAULT_MD))
    args = parser.parse_args()

    packet = build_packet(
        operations_path=Path(str(args.operations)).resolve(),
        brainstorm_path=Path(str(args.brainstorm)).resolve(),
        zero_display_path=Path(str(args.zero_display)).resolve(),
        public_language_path=Path(str(args.public_language)).resolve(),
        founder_chain_path=Path(str(args.founder_chain)).resolve(),
        next_execution_path=Path(str(args.next_execution)).resolve(),
        bridge_path=Path(str(args.bridge)).resolve(),
        service_copy_path=Path(str(args.service_copy)).resolve(),
    )

    json_path = Path(str(args.json)).resolve()
    md_path = Path(str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "packet_id": packet.get("packet_id"),
                "json": str(json_path),
                "md": str(md_path),
                "target_thread": packet.get("target_thread"),
                "customer_url": _safe_dict(packet.get("live_service")).get("customer_url"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
