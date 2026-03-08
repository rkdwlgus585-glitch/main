#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_BRIDGE = ROOT / "logs" / "yangdo_recommendation_bridge_packet_latest.json"
DEFAULT_UX = ROOT / "logs" / "yangdo_recommendation_ux_packet_latest.json"
DEFAULT_PRECISION = ROOT / "logs" / "yangdo_recommendation_precision_matrix_latest.json"
DEFAULT_DIVERSITY = ROOT / "logs" / "yangdo_recommendation_diversity_audit_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_JSON = ROOT / "logs" / "yangdo_service_copy_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_service_copy_packet_latest.md"


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


def _resolve_service_market_target(
    *,
    bridge_public_target: str,
    market_bridge_url: str,
    platform_host: str,
    service_slug: str,
) -> str:
    candidate = (bridge_public_target or "").strip()
    fallback = (market_bridge_url or "").strip() or "/mna-market"
    service_slug = (service_slug or "").strip() or "/yangdo"
    if not candidate:
        return fallback
    if candidate == service_slug:
        return fallback
    if f"https://{platform_host}{service_slug}" in candidate:
        return fallback
    if candidate.rstrip("/") == f"https://{platform_host}{service_slug}".rstrip("/"):
        return fallback
    if candidate.rstrip("/") == service_slug.rstrip("/"):
        return fallback
    return candidate


def build_yangdo_service_copy_packet(
    *,
    ia_path: Path,
    bridge_path: Path,
    ux_path: Path,
    precision_path: Path,
    diversity_path: Path,
    rental_path: Path,
) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    bridge = _load_json(bridge_path)
    ux = _load_json(ux_path)
    precision = _load_json(precision_path)
    diversity = _load_json(diversity_path)
    rental = _load_json(rental_path)

    ia_topology = ia.get("topology") if isinstance(ia.get("topology"), dict) else {}
    pages = ia.get("pages") if isinstance(ia.get("pages"), list) else []
    yangdo_page = next((row for row in pages if isinstance(row, dict) and row.get("page_id") == "yangdo"), {})
    bridge_summary = bridge.get("summary") if isinstance(bridge.get("summary"), dict) else {}
    bridge_public = bridge.get("public_summary_contract") if isinstance(bridge.get("public_summary_contract"), dict) else {}
    bridge_detail = bridge.get("detail_contract") if isinstance(bridge.get("detail_contract"), dict) else {}
    bridge_market = bridge.get("market_bridge_policy") if isinstance(bridge.get("market_bridge_policy"), dict) else {}
    bridge_surface = bridge.get("service_surface") if isinstance(bridge.get("service_surface"), dict) else {}
    ux_summary = ux.get("summary") if isinstance(ux.get("summary"), dict) else {}
    ux_public = ux.get("public_summary_experience") if isinstance(ux.get("public_summary_experience"), dict) else {}
    ux_detail = ux.get("consult_detail_experience") if isinstance(ux.get("consult_detail_experience"), dict) else {}
    ux_matrix = ux.get("rental_exposure_matrix") if isinstance(ux.get("rental_exposure_matrix"), dict) else {}
    precision_summary = precision.get("summary") if isinstance(precision.get("summary"), dict) else {}
    diversity_summary = diversity.get("summary") if isinstance(diversity.get("summary"), dict) else {}
    rental_summary = rental.get("summary") if isinstance(rental.get("summary"), dict) else {}
    rental_package = (
        rental.get("packaging", {}).get("partner_rental", {}).get("yangdo_recommendation")
        if isinstance(rental.get("packaging"), dict)
        and isinstance(rental.get("packaging", {}).get("partner_rental"), dict)
        else {}
    )
    rental_package_matrix = rental_package.get("package_matrix") if isinstance(rental_package.get("package_matrix"), dict) else {}
    rental_lane_positioning = rental_package.get("lane_positioning") if isinstance(rental_package.get("lane_positioning"), dict) else {}

    platform_host = str(bridge_summary.get("platform_host") or ia_topology.get("platform_host") or "seoulmna.kr")
    listing_host = str(bridge_summary.get("listing_host") or ia_topology.get("listing_host") or "seoulmna.co.kr")
    service_slug = str(bridge_summary.get("service_slug") or yangdo_page.get("slug") or "/yangdo")
    primary_cta = str(((bridge_public.get("primary_cta") or {}).get("label")) or ux_public.get("cta_primary_label") or "추천 매물 흐름 보기")
    secondary_cta = str(((bridge_public.get("secondary_cta") or {}).get("label")) or ux_public.get("cta_secondary_label") or "상담형 상세 요청")
    primary_target = _resolve_service_market_target(
        bridge_public_target=str(((bridge_public.get("primary_cta") or {}).get("target")) or ""),
        market_bridge_url=str(bridge_market.get("market_bridge_url") or "/mna-market"),
        platform_host=platform_host,
        service_slug=service_slug,
    )
    secondary_target = str(((bridge_public.get("secondary_cta") or {}).get("target")) or "/consult?intent=yangdo")
    precision_labels = _as_list(bridge_summary.get("supported_precision_labels")) or ["우선 추천", "조건 유사", "보조 검토"]

    packet_ready = all(
        [
            bool(bridge_summary.get("packet_ready")),
            bool(precision_summary.get("precision_ok")),
            bool(diversity_summary.get("diversity_ok")),
            bool(primary_cta),
            bool(secondary_cta),
        ]
    )
    low_precision_consult_first_ready = precision_labels[-1] == "보조 검토" and bool(secondary_cta)
    market_bridge_story_ready = bool(primary_target) and "mna-market" in primary_target
    market_fit_interpretation_ready = bool(precision_summary.get("precision_ok")) and bool(diversity_summary.get("diversity_ok"))
    lane_stories_ready = all(
        bool(rental_lane_positioning.get(key))
        for key in ("summary_market_bridge", "detail_explainable", "consult_assist")
    )
    zero_display_recovery_ready = bool(primary_target) and bool(secondary_target) and low_precision_consult_first_ready

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_service_copy_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "service_copy_ready": packet_ready,
            "low_precision_consult_first_ready": low_precision_consult_first_ready,
            "market_bridge_story_ready": market_bridge_story_ready,
            "market_fit_interpretation_ready": market_fit_interpretation_ready,
            "lane_stories_ready": lane_stories_ready,
            "zero_display_recovery_ready": zero_display_recovery_ready,
            "service_slug": service_slug,
            "platform_host": platform_host,
            "listing_host": listing_host,
            "precision_label_count": len(precision_labels),
            "recommendation_offering_count": int(rental_summary.get("yangdo_recommendation_offering_count", 0) or 0),
        },
        "hero": {
            "kicker": "AI 양도가 산정 시스템",
            "title": "가격 범위만 보여주지 않고, 지금 시장에서 어떤 매물이 맞는지 해석해 주는 서비스로 설계합니다.",
            "body": "이 페이지는 단순 시세 계산기가 아니라 입력 프로필 적합도, 추천 정밀도, 일치축·비일치축, 시장 확인 CTA를 한 흐름으로 설명하고 다음 행동까지 분기합니다.",
            "gate_shortcode": str(bridge_surface.get("gate_shortcode") or yangdo_page.get("primary_cta") or '[seoulmna_calc_gate type=\"yangdo\"]'),
        },
        "market_fit_interpretation": {
            "framing_title": "시장 적합도 해석",
            "primary_question": "이 입력 조건이 지금 시장에 나온 후보군과 얼마나 맞는지, 그리고 바로 매물 확인으로 갈지 상담형 상세가 먼저 필요한지를 해석합니다.",
            "interpretation_axes": [
                {
                    "axis": "match_strength",
                    "label": "일치 강도",
                    "story": "면허 정합도, 실적 규모, 가격대가 같이 맞는 경우를 우선 추천으로 분류합니다.",
                },
                {
                    "axis": "mismatch_signal",
                    "label": "비일치 신호",
                    "story": "규모 차이, 가격대 차이, 부정합 축이 보이면 공개 요약만으로 확정하지 않고 설명형 상세 또는 상담으로 넘깁니다.",
                },
                {
                    "axis": "market_action",
                    "label": "다음 행동",
                    "story": "요약 결과는 시장 확인으로, 불일치가 크면 상담형 상세로 분기해 잘못된 확정 해석을 줄입니다.",
                },
            ],
        },
        "explanation_cards": [
            {
                "title": "가격 범위",
                "body": "비교거래 정규화와 중복 매물 보정 이후의 기준 범위를 먼저 보여줍니다.",
            },
            {
                "title": "추천 라벨과 정밀도",
                "body": "우선 추천, 조건 유사, 보조 검토로 추천 강도를 나누고 공개 요약과 상담형 상세의 설명 범위를 구분합니다.",
            },
            {
                "title": "시장 확인과 상담 분기",
                "body": "메인 플랫폼에서 추천을 해석하고, 실제 매물 확인은 별도 매물 사이트나 상담형 상세로만 분기합니다.",
            },
        ],
        "lane_stories": {
            "summary_market_bridge": {
                "label": "요약+시장 브리지",
                "role": str(((rental_lane_positioning.get("summary_market_bridge") or {}).get("role")) or ""),
                "who_its_for": str(((rental_lane_positioning.get("summary_market_bridge") or {}).get("who_its_for")) or ""),
                "cta_bias": str(((rental_lane_positioning.get("summary_market_bridge") or {}).get("cta_bias")) or "market_first"),
                "story": "공개 화면은 가격 범위와 추천 이유만 보여주고, 실제 후보 확인은 매물 흐름 보기로 넘깁니다.",
            },
            "detail_explainable": {
                "label": "설명 가능한 상세",
                "role": str(((rental_lane_positioning.get("detail_explainable") or {}).get("role")) or ""),
                "who_its_for": str(((rental_lane_positioning.get("detail_explainable") or {}).get("who_its_for")) or ""),
                "cta_bias": str(((rental_lane_positioning.get("detail_explainable") or {}).get("cta_bias")) or "explanation_first"),
                "story": "추천을 바로 확정하지 않고 왜 맞는지와 어디가 어긋나는지를 먼저 읽는 lane입니다.",
            },
            "consult_assist": {
                "label": "상담 연결 상세",
                "role": str(((rental_lane_positioning.get("consult_assist") or {}).get("role")) or ""),
                "who_its_for": str(((rental_lane_positioning.get("consult_assist") or {}).get("who_its_for")) or ""),
                "cta_bias": str(((rental_lane_positioning.get("consult_assist") or {}).get("cta_bias")) or "consult_first_when_precision_is_low"),
                "story": "보조 검토나 비일치 신호가 크면 매물 확인보다 상담형 상세를 먼저 여는 lane입니다.",
            },
        },
        "precision_sections": [
            {
                "label": precision_labels[0],
                "description": "면허 정합도, 실적 규모, 가격대, 최근 흐름이 강하게 맞는 경우의 추천입니다.",
                "preferred_cta": primary_cta,
                "preferred_lane": "summary_market_bridge",
                "escalation_lane": "detail_explainable",
            },
            {
                "label": precision_labels[1] if len(precision_labels) > 1 else "조건 유사",
                "description": "주요 축은 맞지만 일부 규모 차이나 주의 신호가 있어 비교 해석이 필요한 추천입니다.",
                "preferred_cta": secondary_cta,
                "preferred_lane": "detail_explainable",
                "escalation_lane": "consult_assist",
            },
            {
                "label": precision_labels[2] if len(precision_labels) > 2 else "보조 검토",
                "description": "공개 요약만으로 확정 판단하지 않고 상담형 상세나 추가 검토로 넘겨야 하는 추천입니다.",
                "preferred_cta": secondary_cta,
                "preferred_lane": "consult_assist",
                "escalation_lane": "internal_full",
            },
        ],
        "decision_paths": [
            {
                "when": "우선 추천",
                "route": "summary_market_bridge",
                "decision": "매물 흐름 보기 우선",
                "why": "정합도가 높고 추천 이유가 명확하므로 시장 확인 CTA를 먼저 열어도 해석 손실이 작습니다.",
            },
            {
                "when": "조건 유사",
                "route": "detail_explainable",
                "decision": "설명형 상세 우선",
                "why": "추천 이유를 읽어야 실제 시장 후보와의 차이를 오해하지 않습니다.",
            },
            {
                "when": "보조 검토",
                "route": "consult_assist",
                "decision": "상담형 상세 우선",
                "why": "공개 요약만으로 확정하면 오판 가능성이 커져 상담형 설명이 더 중요합니다.",
            },
        ],
        "cta_ladder": {
            "primary_market_bridge": {
                "label": primary_cta,
                "target": primary_target,
                "story": "추천 매물 흐름을 보고 실제 매물은 별도 매물 사이트에서 확인합니다.",
            },
            "secondary_consult": {
                "label": secondary_cta,
                "target": secondary_target,
                "story": "추천 이유와 불일치 축이 더 중요하면 상담형 상세로 먼저 분기합니다.",
            },
        },
        "zero_display_recovery_policy": {
            "trigger": "recommended_count == 0",
            "policy_ready": zero_display_recovery_ready,
            "first_action": {
                "label": "입력 보강 후 다시 계산",
                "reason": "비교 가능한 후보가 하나도 없을 때는 입력 축을 먼저 보강해야 잘못된 시장 해석을 줄일 수 있습니다.",
            },
            "second_action": {
                "label": primary_cta,
                "target": primary_target,
                "reason": "핵심 입력은 유지한 채 시장 흐름을 먼저 확인해야 하는 경우를 위해 시장 브리지를 남깁니다.",
            },
            "third_action": {
                "label": secondary_cta,
                "target": secondary_target,
                "reason": "특수 업종 또는 불일치 신호가 큰 경우에는 상담형 상세가 더 안전한 다음 행동입니다.",
            },
            "guardrails": [
                "추천 0건에서는 매물 확정처럼 읽히는 표현을 금지합니다.",
                "입력 보강, 시장 확인, 상담형 상세의 순서를 공개 계약으로 고정합니다.",
                "보조 검토 또는 특수 업종 신호가 겹치면 상담형 상세를 더 앞세웁니다.",
            ],
        },
        "public_detail_split": {
            "public_fields": _as_list(bridge_public.get("fields")),
            "detail_fields": _as_list(bridge_detail.get("fields")),
            "public_story": str(ux_public.get("story") or bridge_public.get("story") or rental_package.get("public_story") or ""),
            "detail_story": str(ux_detail.get("story") or bridge_detail.get("story") or rental_package.get("detail_story") or ""),
        },
        "offering_matrix": {
            "summary_market_bridge": _as_list(((ux_matrix.get("standard") or {}).get("offerings"))) or _as_list(((rental_package_matrix.get("summary_market_bridge") or {}).get("offering_ids"))),
            "detail_explainable": _as_list(((ux_matrix.get("pro_detail") or {}).get("offerings"))) or _as_list(((rental_package_matrix.get("detail_explainable") or {}).get("offering_ids"))),
            "consult_assist": _as_list(((ux_matrix.get("pro_consult") or {}).get("offerings"))) or _as_list(((rental_package_matrix.get("consult_assist") or {}).get("offering_ids"))),
            "internal_full": _as_list(((ux_matrix.get("internal") or {}).get("offerings"))) or _as_list(((rental_package_matrix.get("internal_full") or {}).get("offering_ids"))),
        },
        "proof_points": {
            "precision_scenario_count": int(precision_summary.get("scenario_count", 0) or 0),
            "diversity_scenario_count": int(diversity_summary.get("scenario_count", 0) or 0),
            "detail_explainability_ok": bool(precision_summary.get("detail_explainability_ok")),
            "diversity_ok": bool(diversity_summary.get("diversity_ok")),
            "listing_bridge_policy": str(rental_package.get("listing_runtime_policy") or ""),
            "service_flow_policy": str(bridge_market.get("service_flow_policy") or ux_summary.get("service_flow_policy") or ""),
        },
        "copy_guardrails": [
            "홈에서는 계산기를 직접 띄우지 않는다.",
            "서비스 페이지에서만 lazy gate를 사용한다.",
            ".co.kr를 계산기 실행면으로 소개하지 않는다.",
            "추천은 가격 맞추기가 아니라 시장 적합도 해석으로 설명한다.",
            "보조 검토는 시장 브리지보다 상담 CTA를 먼저 강조한다.",
        ],
        "brainstorm_backlog": [
            {
                "idea": "추천 결과에 일치축과 비일치축 배지를 동시에 표시",
                "expected_impact": "사용자가 추천 이유를 더 빠르게 이해하고 잘못된 확정 해석을 줄일 수 있습니다.",
            },
            {
                "idea": "보조 검토 결과에서는 매물 브리지보다 상담형 상세 CTA를 더 크게 노출",
                "expected_impact": "낮은 정밀도 추천을 과도하게 매물 확인으로 보내는 것을 줄입니다.",
            },
            {
                "idea": "추천 결과 하단에 실제 시장 확인과 계산 결과의 역할 차이를 명시",
                "expected_impact": "플랫폼(.kr)과 매물(.co.kr)의 역할 분리가 더 선명해집니다.",
            },
            {
                "idea": "detail_explainable lane에서 설명 우선 CTA와 상담 전환 CTA를 분리 운영",
                "expected_impact": "중간 tier 상품의 가치가 더 명확해지고, 상담 lane과의 구분도 쉬워집니다.",
            },
        ],
        "next_actions": [
            "WordPress /yangdo 페이지는 이 packet의 hero, precision_sections, CTA ladder를 기준으로 유지합니다.",
            "추천 상품 lane은 summary_market_bridge, detail_explainable, consult_assist 기준으로 계속 분리합니다.",
            "보조 검토 비중이 높아지면 상담형 상세 CTA를 먼저 강조하는 UX 실험을 다음 배치에서 진행합니다.",
            "가격 계산기라는 표현보다 시장 적합도 해석 서비스라는 표현을 우선 사용하고, 각 lane의 역할 차이를 카피에서 더 분명히 나눕니다.",
        ],
        "artifacts": {
            "ia": str(ia_path.resolve()),
            "bridge_packet": str(bridge_path.resolve()),
            "ux_packet": str(ux_path.resolve()),
            "precision_matrix": str(precision_path.resolve()),
            "diversity_audit": str(diversity_path.resolve()),
            "rental_catalog": str(rental_path.resolve()),
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    hero = payload.get("hero") if isinstance(payload.get("hero"), dict) else {}
    interpretation = payload.get("market_fit_interpretation") if isinstance(payload.get("market_fit_interpretation"), dict) else {}
    lines = [
        "# Yangdo Service Copy Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- service_copy_ready: {summary.get('service_copy_ready')}",
        f"- low_precision_consult_first_ready: {summary.get('low_precision_consult_first_ready')}",
        f"- market_bridge_story_ready: {summary.get('market_bridge_story_ready')}",
        f"- market_fit_interpretation_ready: {summary.get('market_fit_interpretation_ready')}",
        f"- lane_stories_ready: {summary.get('lane_stories_ready')}",
        f"- service_slug: {summary.get('service_slug')}",
        "",
        "## Hero",
        f"- kicker: {hero.get('kicker')}",
        f"- title: {hero.get('title')}",
        f"- body: {hero.get('body')}",
        "",
        "## Market Fit Interpretation",
        f"- framing_title: {interpretation.get('framing_title')}",
        f"- primary_question: {interpretation.get('primary_question')}",
    ]
    for row in interpretation.get("interpretation_axes", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"- {row.get('label')}: {row.get('story')}")
    lines.extend([
        "",
        "## CTA Ladder",
    ])
    cta_ladder = payload.get("cta_ladder") if isinstance(payload.get("cta_ladder"), dict) else {}
    for key, value in cta_ladder.items():
        if not isinstance(value, dict):
            continue
        lines.append(f"- {key}: {value.get('label')} -> {value.get('target')}")
    lines.extend(["", "## Lane Stories"])
    lane_stories = payload.get("lane_stories") if isinstance(payload.get("lane_stories"), dict) else {}
    for key, value in lane_stories.items():
        if not isinstance(value, dict):
            continue
        lines.append(f"- {key}: {value.get('label')} / {value.get('cta_bias')}")
        lines.append(f"  - story: {value.get('story')}")
        if value.get("who_its_for"):
            lines.append(f"  - who_its_for: {value.get('who_its_for')}")
    lines.extend(["", "## Decision Paths"])
    for row in payload.get("decision_paths", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"- {row.get('when')}: {row.get('decision')} ({row.get('route')})")
        lines.append(f"  - why: {row.get('why')}")
    lines.extend(["", "## Guardrails"])
    for item in payload.get("copy_guardrails", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate canonical service copy packet for the Yangdo service page.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--precision", type=Path, default=DEFAULT_PRECISION)
    parser.add_argument("--diversity", type=Path, default=DEFAULT_DIVERSITY)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_service_copy_packet(
        ia_path=args.ia,
        bridge_path=args.bridge,
        ux_path=args.ux,
        precision_path=args.precision,
        diversity_path=args.diversity,
        rental_path=args.rental,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("packet_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
