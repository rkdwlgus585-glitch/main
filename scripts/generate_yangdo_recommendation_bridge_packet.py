#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_BRIDGE_POLICY = ROOT / "logs" / "listing_platform_bridge_policy_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_PRECISION = ROOT / "logs" / "yangdo_recommendation_precision_matrix_latest.json"
DEFAULT_CONTRACT = ROOT / "logs" / "yangdo_recommendation_contract_audit_latest.json"
DEFAULT_JSON = ROOT / "logs" / "yangdo_recommendation_bridge_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_recommendation_bridge_packet_latest.md"


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


def build_yangdo_recommendation_bridge_packet(
    *,
    ia_path: Path,
    bridge_policy_path: Path,
    rental_path: Path,
    precision_path: Path,
    contract_path: Path,
) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    bridge_policy = _load_json(bridge_policy_path)
    rental = _load_json(rental_path)
    precision = _load_json(precision_path)
    contract = _load_json(contract_path)

    topology = ia.get("topology") if isinstance(ia.get("topology"), dict) else {}
    pages = ia.get("pages") if isinstance(ia.get("pages"), list) else []
    yangdo_page = next((row for row in pages if isinstance(row, dict) and row.get("page_id") == "yangdo"), {})
    bridge_summary = bridge_policy.get("summary") if isinstance(bridge_policy.get("summary"), dict) else {}
    bridge_ctas = bridge_policy.get("ctas") if isinstance(bridge_policy.get("ctas"), list) else []
    rental_summary = rental.get("summary") if isinstance(rental.get("summary"), dict) else {}
    rental_packaging = rental.get("packaging") if isinstance(rental.get("packaging"), dict) else {}
    recommendation_packaging = (
        rental_packaging.get("partner_rental", {}).get("yangdo_recommendation")
        if isinstance(rental_packaging.get("partner_rental"), dict)
        else {}
    )
    precision_summary = precision.get("summary") if isinstance(precision.get("summary"), dict) else {}
    contract_summary = contract.get("summary") if isinstance(contract.get("summary"), dict) else {}

    platform_host = str(topology.get("platform_host") or bridge_summary.get("platform_host") or "seoulmna.kr")
    listing_host = str(topology.get("listing_host") or bridge_summary.get("listing_host") or "seoulmna.co.kr")
    service_slug = str(yangdo_page.get("slug") or "/yangdo")
    service_url = f"https://{platform_host}{service_slug}"
    market_bridge_url = f"https://{platform_host}/mna-market"
    consult_url = "https://{host}/consult?intent=yangdo".format(host=platform_host)
    gate_shortcode = str(yangdo_page.get("primary_cta") or "")
    public_cta = next((row for row in bridge_ctas if row.get("placement") == "listing_detail_primary"), {})

    primary_cta_label = str(recommendation_packaging.get("service_primary_cta") or "추천 매물 흐름 보기")
    secondary_cta_label = str(recommendation_packaging.get("service_secondary_cta") or "상담형 상세 요청")
    service_flow_policy = str(recommendation_packaging.get("service_flow_policy") or "public_summary_then_market_or_consult")
    service_market_bridge_target = market_bridge_url

    public_card_fields = [
        "display_low_eok",
        "display_high_eok",
        "recommendation_label",
        "recommendation_focus",
        "reasons",
        "url",
    ]
    detail_card_fields = [
        "precision_tier",
        "fit_summary",
        "matched_axes",
        "mismatch_flags",
    ]
    operator_only_fields = [
        "recommendation_score",
        "similarity",
        "duplicate_cluster_adjusted",
    ]

    packet_ready = bool(yangdo_page) and bool(gate_shortcode) and bool(precision_summary.get("precision_ok")) and bool(contract_summary.get("contract_ok"))
    market_bridge_ready = bridge_summary.get("listing_runtime_policy") == "listing_domain_links_only_no_tool_embed"
    rental_ready = bool(recommendation_packaging.get("summary_offerings")) and bool(recommendation_packaging.get("detail_offerings"))

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "packet_ready": packet_ready,
            "platform_host": platform_host,
            "listing_host": listing_host,
            "service_slug": service_slug,
            "precision_ok": bool(precision_summary.get("precision_ok")),
            "contract_ok": bool(contract_summary.get("contract_ok")),
            "market_bridge_ready": market_bridge_ready,
            "rental_ready": rental_ready,
            "supported_precision_labels": _as_list(recommendation_packaging.get("supported_precision_labels")),
        },
        "service_surface": {
            "page_title": str(yangdo_page.get("title") or "AI 양도가 산정 · 유사매물 추천"),
            "service_url": service_url,
            "gate_shortcode": gate_shortcode,
            "ui_rules": [
                "홈에서는 계산기를 열지 않고 /yangdo에서만 lazy gate를 연다.",
                "가격 범위를 먼저 보여주고 추천 라벨과 추천 이유를 이어서 설명한다.",
                "실제 매물 탐색은 .co.kr 또는 추천 카드의 매물 링크로 분기한다.",
                "상담형 상세는 .kr에서 유지하고, 원시 추천 점수는 운영 검수 레이어에만 둔다.",
            ],
        },
        "public_summary_contract": {
            "fields": public_card_fields,
            "story": str(recommendation_packaging.get("public_story") or "공개 화면은 가격 범위, 추천 라벨, 추천 이유만 노출합니다."),
            "primary_cta": {
                "label": primary_cta_label,
                "target": service_market_bridge_target,
                "placement": "service_market_bridge",
            },
            "secondary_cta": {
                "label": secondary_cta_label,
                "target": consult_url,
            },
        },
        "detail_contract": {
            "fields": detail_card_fields,
            "story": str(recommendation_packaging.get("detail_story") or "상담형 상세는 추천 정밀도와 일치축을 설명합니다."),
            "operator_only_fields": operator_only_fields,
        },
        "market_bridge_policy": {
            "service_flow_policy": service_flow_policy,
            "listing_runtime_policy": str(bridge_summary.get("listing_runtime_policy") or ""),
            "market_bridge_url": market_bridge_url,
            "listing_detail_cta_url": str(public_cta.get("target_url") or ""),
            "notes": [
                "추천 결과는 .kr 서비스 페이지에서 해석하고, 실제 매물 확인은 .co.kr 또는 추천 매물 링크로만 넘긴다.",
                ".co.kr에는 계산기를 다시 심지 않고 CTA-only bridge를 유지한다.",
            ],
        },
        "rental_packaging": {
            "summary_offerings": _as_list(recommendation_packaging.get("summary_offerings")),
            "detail_offerings": _as_list(recommendation_packaging.get("detail_offerings")),
            "internal_offerings": _as_list(recommendation_packaging.get("internal_offerings")),
            "summary_policy": str(recommendation_packaging.get("summary_policy") or ""),
            "detail_policy": str(recommendation_packaging.get("detail_policy") or ""),
            "internal_policy": str(recommendation_packaging.get("internal_policy") or ""),
            "precision_scenario_count": int(precision_summary.get("scenario_count", 0) or 0),
            "contract_backed": bool(contract_summary.get("contract_ok")),
        },
        "brainstorm_extensions": [
            {
                "idea": "추천 매물 카드에 적합도 축 배지를 노출",
                "impact": "추천 이유를 읽지 않아도 왜 추천됐는지 빠르게 이해할 수 있습니다.",
            },
            {
                "idea": "추천 결과에서 바로 .co.kr 상세나 /consult로 분기하는 이중 CTA 유지",
                "impact": "즉시 매물 확인형 사용자와 상담 우선형 사용자를 분리해 전환 효율을 높입니다.",
            },
            {
                "idea": "파트너 Standard는 추천 요약까지만, Pro는 정밀도/일치축까지",
                "impact": "임대형 상품의 차등 가치를 분명히 하면서 원시 추천 점수는 보호합니다.",
            },
        ],
        "next_actions": [
            "WordPress /yangdo 페이지에서 추천 라벨, 추천 정밀도, 추천 이유, 매물 이동 CTA를 한 흐름으로 설명합니다.",
            "추천 카드의 공개 필드와 상담형 상세 필드를 현재 contract audit 기준으로 유지합니다.",
            "추천 결과를 .co.kr 계산기 재실행으로 보내지 말고 .kr 상담 또는 .co.kr 매물 확인으로만 연결합니다.",
        ],
        "artifacts": {
            "ia": str(ia_path.resolve()),
            "bridge_policy": str(bridge_policy_path.resolve()),
            "rental_catalog": str(rental_path.resolve()),
            "precision_matrix": str(precision_path.resolve()),
            "contract_audit": str(contract_path.resolve()),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    public_contract = payload.get("public_summary_contract") if isinstance(payload.get("public_summary_contract"), dict) else {}
    detail_contract = payload.get("detail_contract") if isinstance(payload.get("detail_contract"), dict) else {}
    rental_packaging = payload.get("rental_packaging") if isinstance(payload.get("rental_packaging"), dict) else {}
    lines = [
        "# Yangdo Recommendation Bridge Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- platform_host: {summary.get('platform_host')}",
        f"- listing_host: {summary.get('listing_host')}",
        f"- service_slug: {summary.get('service_slug')}",
        f"- precision_ok: {summary.get('precision_ok')}",
        f"- contract_ok: {summary.get('contract_ok')}",
        f"- market_bridge_ready: {summary.get('market_bridge_ready')}",
        f"- rental_ready: {summary.get('rental_ready')}",
        "",
        "## Public Summary",
        f"- fields: {', '.join(public_contract.get('fields') or [])}",
        f"- story: {public_contract.get('story') or ''}",
        "",
        "## Detail",
        f"- fields: {', '.join(detail_contract.get('fields') or [])}",
        f"- operator_only: {', '.join(detail_contract.get('operator_only_fields') or [])}",
        "",
        "## Rental",
        f"- summary_offerings: {', '.join(rental_packaging.get('summary_offerings') or []) or '(none)'}",
        f"- detail_offerings: {', '.join(rental_packaging.get('detail_offerings') or []) or '(none)'}",
        f"- internal_offerings: {', '.join(rental_packaging.get('internal_offerings') or []) or '(none)'}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the canonical bridge packet for yangdo recommendation UX, market routing, and rental exposure.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--bridge-policy", type=Path, default=DEFAULT_BRIDGE_POLICY)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--precision", type=Path, default=DEFAULT_PRECISION)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_recommendation_bridge_packet(
        ia_path=args.ia,
        bridge_policy_path=args.bridge_policy,
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
