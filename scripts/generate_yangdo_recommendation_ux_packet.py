#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_UX_AUDIT = ROOT / "logs" / "wordpress_platform_ux_audit_latest.json"
DEFAULT_BRIDGE = ROOT / "logs" / "yangdo_recommendation_bridge_packet_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_PRECISION = ROOT / "logs" / "yangdo_recommendation_precision_matrix_latest.json"
DEFAULT_CONTRACT = ROOT / "logs" / "yangdo_recommendation_contract_audit_latest.json"
DEFAULT_JSON = ROOT / "logs" / "yangdo_recommendation_ux_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_recommendation_ux_packet_latest.md"


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


def build_yangdo_recommendation_ux_packet(
    *,
    ia_path: Path,
    ux_audit_path: Path,
    bridge_path: Path,
    rental_path: Path,
    precision_path: Path,
    contract_path: Path,
) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    ux_audit = _load_json(ux_audit_path)
    bridge_packet = _load_json(bridge_path)
    rental_catalog = _load_json(rental_path)
    precision = _load_json(precision_path)
    contract = _load_json(contract_path)

    pages = ia.get("pages") if isinstance(ia.get("pages"), list) else []
    yangdo_page = next((row for row in pages if isinstance(row, dict) and row.get("page_id") == "yangdo"), {})
    ux_summary = ux_audit.get("summary") if isinstance(ux_audit.get("summary"), dict) else {}
    bridge_summary = bridge_packet.get("summary") if isinstance(bridge_packet.get("summary"), dict) else {}
    bridge_surface = bridge_packet.get("service_surface") if isinstance(bridge_packet.get("service_surface"), dict) else {}
    public_contract = bridge_packet.get("public_summary_contract") if isinstance(bridge_packet.get("public_summary_contract"), dict) else {}
    detail_contract = bridge_packet.get("detail_contract") if isinstance(bridge_packet.get("detail_contract"), dict) else {}
    market_bridge = bridge_packet.get("market_bridge_policy") if isinstance(bridge_packet.get("market_bridge_policy"), dict) else {}
    rental_packaging = bridge_packet.get("rental_packaging") if isinstance(bridge_packet.get("rental_packaging"), dict) else {}
    rental_summary = rental_catalog.get("summary") if isinstance(rental_catalog.get("summary"), dict) else {}
    partner_recommendation = (
        rental_catalog.get("packaging", {}).get("partner_rental", {}).get("yangdo_recommendation")
        if isinstance(rental_catalog.get("packaging"), dict)
        and isinstance(rental_catalog.get("packaging", {}).get("partner_rental"), dict)
        else {}
    )
    precision_summary = precision.get("summary") if isinstance(precision.get("summary"), dict) else {}
    contract_summary = contract.get("summary") if isinstance(contract.get("summary"), dict) else {}
    recommendation_package_matrix = (
        partner_recommendation.get("package_matrix") if isinstance(partner_recommendation.get("package_matrix"), dict) else {}
    )

    gate_shortcode = str(bridge_surface.get("gate_shortcode") or yangdo_page.get("primary_cta") or "")
    service_slug = str(bridge_summary.get("service_slug") or yangdo_page.get("slug") or "/yangdo")
    platform_host = str(bridge_summary.get("platform_host") or ia.get("topology", {}).get("platform_host") or "seoulmna.kr")
    listing_host = str(bridge_summary.get("listing_host") or ia.get("topology", {}).get("listing_host") or "seoulmna.co.kr")
    market_cta = public_contract.get("primary_cta") if isinstance(public_contract.get("primary_cta"), dict) else {}
    consult_cta = public_contract.get("secondary_cta") if isinstance(public_contract.get("secondary_cta"), dict) else {}

    public_fields = _as_list(public_contract.get("fields"))
    detail_fields = _as_list(detail_contract.get("fields"))
    internal_fields = _as_list(detail_contract.get("operator_only_fields"))

    packet_ready = all(
        [
            bool(ux_summary.get("ux_ok")),
            bool(ux_summary.get("yangdo_recommendation_surface_ok")),
            bool(bridge_summary.get("packet_ready")),
            bool(precision_summary.get("precision_ok")),
            bool(contract_summary.get("contract_ok")),
            bool(public_fields),
            bool(detail_fields),
            bool(gate_shortcode),
        ]
    )

    public_story = str(partner_recommendation.get("public_story") or public_contract.get("story") or "")
    detail_story = str(partner_recommendation.get("detail_story") or detail_contract.get("story") or "")
    operator_story = str(partner_recommendation.get("operator_story") or "")
    service_flow_policy = str(partner_recommendation.get("service_flow_policy") or market_bridge.get("service_flow_policy") or "")

    public_summary_experience = {
        "audience": "public_platform_user",
        "visible_fields": public_fields,
        "story": public_story,
        "cta_primary_label": str(market_cta.get("label") or partner_recommendation.get("service_primary_cta") or "추천 매물 흐름 보기"),
        "cta_primary_target": str(market_cta.get("target") or market_bridge.get("market_bridge_url") or ""),
        "cta_secondary_label": str(consult_cta.get("label") or partner_recommendation.get("service_secondary_cta") or "상담형 상세 요청"),
        "cta_secondary_target": str(consult_cta.get("target") or ""),
        "allowed_offerings": _as_list(rental_packaging.get("summary_offerings")),
        "policy": str(rental_packaging.get("summary_policy") or ""),
        "explanation_points": [
            "가격 범위, 추천 라벨, 추천 이유만 공개 화면에 남긴다.",
            "실제 매물 확인은 별도 매물 흐름으로 보내고, 계산기 자체를 .co.kr에 다시 심지 않는다.",
            "공개 화면은 추천을 해석하는 역할만 맡고 상세 분해는 상담형 상세로 보낸다.",
        ],
    }

    detail_explainable_experience = {
        "audience": "partner_detail_explainable",
        "visible_fields": detail_fields,
        "story": detail_story,
        "allowed_offerings": _as_list(
            ((recommendation_package_matrix.get("detail_explainable") or {}).get("offering_ids"))
        ),
        "policy": str(((recommendation_package_matrix.get("detail_explainable") or {}).get("policy")) or ""),
        "detail_axes": ["precision_tier", "matched_axes", "mismatch_flags"],
        "notes": [
            "상담 연동 없이도 설명 가능한 추천 근거를 제공하는 lane이다.",
            "raw score와 내부 신호는 숨기고 설명 가능한 추천 결과만 남긴다.",
        ],
    }

    consult_detail_experience = {
        "audience": "consult_detail_owner",
        "visible_fields": detail_fields,
        "story": detail_story,
        "allowed_offerings": _as_list(
            ((recommendation_package_matrix.get("consult_assist") or {}).get("offering_ids"))
        ),
        "policy": str(rental_packaging.get("detail_policy") or ""),
        "detail_axes": ["precision_tier", "matched_axes", "mismatch_flags"],
        "notes": [
            "추천 정밀도, 일치축, 비일치축, 주의 신호를 같이 설명한다.",
            "공개 화면에서 숨긴 근거를 상담 단계에서만 풀어 설명한다.",
        ],
    }

    internal_review_experience = {
        "audience": "internal_review",
        "visible_fields": internal_fields,
        "story": operator_story,
        "allowed_offerings": _as_list(
            ((recommendation_package_matrix.get("internal_full") or {}).get("offering_ids"))
        ),
        "policy": str(rental_packaging.get("internal_policy") or ""),
        "notes": [
            "중복 매물 보정과 추천 점수는 운영 검수 lane에서만 본다.",
            "파트너 공개 계약에는 raw similarity와 internal review signals를 내리지 않는다.",
        ],
    }

    brainstorm_backlog = [
        {
            "idea": "추천 카드에 일치축 배지를 요약 표시",
            "expected_impact": "사용자가 추천 이유를 더 짧은 시간에 읽고, 저정밀 추천과 고정밀 추천을 혼동하지 않게 한다.",
            "status": "planned",
        },
        {
            "idea": "정밀도 낮음일 때 매물 바로가기보다 상담형 상세 CTA를 먼저 강조",
            "expected_impact": "낮은 적합도의 오인 클릭을 줄이고, 잘못된 기대 가격으로 이어지는 리스크를 줄인다.",
            "status": "planned",
        },
        {
            "idea": "추천 결과를 저장하는 대신 세션형 비교 패널 제공",
            "expected_impact": "개인정보나 운영비 부담을 늘리지 않으면서 사용자가 추천 카드 2~3개를 상대 비교하게 만든다.",
            "status": "backlog",
        },
        {
            "idea": "양도 추천 적합도 부족 시 인허가 자동 전환이 아니라 기업진단/상담 lane 제안",
            "expected_impact": "permit와 yangdo의 시스템 분리를 유지하면서도 사용자의 다음 액션을 놓치지 않는다.",
            "status": "backlog",
        },
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "packet_ready": packet_ready,
            "service_surface_ready": bool(ux_summary.get("yangdo_recommendation_surface_ok")) and bool(gate_shortcode),
            "market_bridge_ready": bool(bridge_summary.get("market_bridge_ready")),
            "rental_exposure_ready": bool(rental_packaging.get("summary_offerings")) and bool(rental_packaging.get("detail_offerings")),
            "precision_ready": bool(precision_summary.get("precision_ok")),
            "detail_explainability_ready": bool(precision_summary.get("detail_explainability_ok")),
            "service_flow_policy": service_flow_policy,
            "platform_host": platform_host,
            "listing_host": listing_host,
            "service_slug": service_slug,
        },
        "service_surface": {
            "page_title": str(bridge_surface.get("page_title") or yangdo_page.get("title") or "AI 양도가 산정 · 유사매물 추천"),
            "service_url": str(bridge_surface.get("service_url") or f"https://{platform_host}{service_slug}"),
            "gate_shortcode": gate_shortcode,
            "ui_rules": _as_list(bridge_surface.get("ui_rules")),
            "required_sections": [
                "가격 범위",
                "추천 라벨",
                "추천 정밀도",
                "추천 이유",
                "공개 요약",
                "상담형 상세",
                "운영 검수",
                "매물 흐름 CTA",
            ],
        },
        "public_summary_experience": public_summary_experience,
        "detail_explainable_experience": detail_explainable_experience,
        "consult_detail_experience": consult_detail_experience,
        "internal_review_experience": internal_review_experience,
        "rental_exposure_matrix": {
            "standard": {
                "offerings": _as_list(
                    ((recommendation_package_matrix.get("summary_market_bridge") or {}).get("offering_ids"))
                ),
                "visible_fields": public_fields,
                "policy": str(rental_packaging.get("summary_policy") or ""),
                "story": public_story,
            },
            "pro_detail": {
                "offerings": _as_list(
                    ((recommendation_package_matrix.get("detail_explainable") or {}).get("offering_ids"))
                ),
                "visible_fields": detail_fields,
                "policy": str(((recommendation_package_matrix.get("detail_explainable") or {}).get("policy")) or ""),
                "story": detail_story,
            },
            "pro_consult": {
                "offerings": _as_list(
                    ((recommendation_package_matrix.get("consult_assist") or {}).get("offering_ids"))
                ),
                "visible_fields": detail_fields,
                "policy": str(rental_packaging.get("detail_policy") or ""),
                "story": detail_story,
            },
            "internal": {
                "offerings": _as_list(
                    ((recommendation_package_matrix.get("internal_full") or {}).get("offering_ids"))
                ),
                "visible_fields": internal_fields,
                "policy": str(rental_packaging.get("internal_policy") or ""),
                "story": operator_story,
            },
        },
        "qa_contract": {
            "ux_ok": bool(ux_summary.get("ux_ok")),
            "yangdo_surface_ok": bool(ux_summary.get("yangdo_recommendation_surface_ok")),
            "precision_ok": bool(precision_summary.get("precision_ok")),
            "contract_ok": bool(contract_summary.get("contract_ok")),
            "supported_precision_labels": _as_list(bridge_summary.get("supported_precision_labels")),
            "precision_scenario_count": int(precision_summary.get("scenario_count", 0) or 0),
            "rental_offering_count": int(rental_summary.get("yangdo_recommendation_offering_count", 0) or 0),
        },
        "brainstorm_backlog": brainstorm_backlog,
        "next_actions": [
            "WordPress /yangdo 페이지는 공개 요약과 상담형 상세의 차이를 같은 화면에서 읽히게 유지합니다.",
            "표준형 임대는 추천 요약과 매물 흐름 CTA만, Pro는 추천 정밀도와 일치축·비일치축 설명까지 제공합니다.",
            "낮은 정밀도 추천은 매물 확인보다 상담형 상세 CTA를 먼저 보이도록 다음 배치에서 강화합니다.",
        ],
        "artifacts": {
            "ia": str(ia_path.resolve()),
            "ux_audit": str(ux_audit_path.resolve()),
            "bridge_packet": str(bridge_path.resolve()),
            "rental_catalog": str(rental_path.resolve()),
            "precision_matrix": str(precision_path.resolve()),
            "contract_audit": str(contract_path.resolve()),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    public_summary = (
        payload.get("public_summary_experience")
        if isinstance(payload.get("public_summary_experience"), dict)
        else {}
    )
    consult_detail = (
        payload.get("consult_detail_experience")
        if isinstance(payload.get("consult_detail_experience"), dict)
        else {}
    )
    detail_explainable = (
        payload.get("detail_explainable_experience")
        if isinstance(payload.get("detail_explainable_experience"), dict)
        else {}
    )
    internal_review = (
        payload.get("internal_review_experience")
        if isinstance(payload.get("internal_review_experience"), dict)
        else {}
    )
    lines = [
        "# Yangdo Recommendation UX Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- service_surface_ready: {summary.get('service_surface_ready')}",
        f"- market_bridge_ready: {summary.get('market_bridge_ready')}",
        f"- rental_exposure_ready: {summary.get('rental_exposure_ready')}",
        f"- precision_ready: {summary.get('precision_ready')}",
        f"- detail_explainability_ready: {summary.get('detail_explainability_ready')}",
        f"- service_flow_policy: {summary.get('service_flow_policy') or '(none)'}",
        "",
        "## Public Summary Experience",
        f"- visible_fields: {', '.join(public_summary.get('visible_fields') or []) or '(none)'}",
        f"- primary_cta: {public_summary.get('cta_primary_label') or '(none)'}",
        f"- secondary_cta: {public_summary.get('cta_secondary_label') or '(none)'}",
        f"- offerings: {', '.join(public_summary.get('allowed_offerings') or []) or '(none)'}",
        "",
        "## Detail Explainable Experience",
        f"- visible_fields: {', '.join(detail_explainable.get('visible_fields') or []) or '(none)'}",
        f"- offerings: {', '.join(detail_explainable.get('allowed_offerings') or []) or '(none)'}",
        "",
        "## Consult Detail Experience",
        f"- visible_fields: {', '.join(consult_detail.get('visible_fields') or []) or '(none)'}",
        f"- offerings: {', '.join(consult_detail.get('allowed_offerings') or []) or '(none)'}",
        "",
        "## Internal Review Experience",
        f"- visible_fields: {', '.join(internal_review.get('visible_fields') or []) or '(none)'}",
        f"- offerings: {', '.join(internal_review.get('allowed_offerings') or []) or '(none)'}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the canonical UX packet for yangdo recommendation service storytelling and rental exposure.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--ux-audit", type=Path, default=DEFAULT_UX_AUDIT)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--precision", type=Path, default=DEFAULT_PRECISION)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_recommendation_ux_packet(
        ia_path=args.ia,
        ux_audit_path=args.ux_audit,
        bridge_path=args.bridge,
        rental_path=args.rental,
        precision_path=args.precision,
        contract_path=args.contract,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("packet_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
