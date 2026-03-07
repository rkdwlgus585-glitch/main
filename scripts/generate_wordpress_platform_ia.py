#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STRATEGY = ROOT / "logs" / "wordpress_platform_strategy_latest.json"
DEFAULT_SURFACE_AUDIT = ROOT / "logs" / "surface_stack_audit_latest.json"
DEFAULT_WP_ASSETS = ROOT / "logs" / "wp_platform_assets_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _page(
    page_id: str,
    slug: str,
    title: str,
    *,
    wordpress_page_slug: str,
    goal: str,
    calculator_policy: str,
    sections: List[str],
    primary_cta: str,
    secondary_cta: str = "",
) -> Dict[str, Any]:
    return {
        "page_id": page_id,
        "slug": slug,
        "wordpress_page_slug": wordpress_page_slug,
        "title": title,
        "goal": goal,
        "calculator_policy": calculator_policy,
        "sections": sections,
        "primary_cta": primary_cta,
        "secondary_cta": secondary_cta,
    }


def build_wordpress_platform_ia(
    *,
    strategy_path: Path,
    surface_audit_path: Path,
    wp_assets_path: Path,
) -> Dict[str, Any]:
    strategy = _load_json(strategy_path)
    surface = _load_json(surface_audit_path)
    wp_assets = _load_json(wp_assets_path)

    kr_host = str(strategy.get("current_live_stack", {}).get("kr_host") or surface.get("surfaces", {}).get("kr", {}).get("host") or "seoulmna.kr")
    co_host = str(strategy.get("current_live_stack", {}).get("co_host") or surface.get("surfaces", {}).get("co", {}).get("host") or "seoulmna.co.kr")
    public_mount = str(strategy.get("calculator_mount_decision", {}).get("private_engine_public_mount") or f"https://{kr_host}/_calc/<type>?embed=1")
    theme_slug = str(wp_assets.get("theme", {}).get("slug") or "seoulmna-platform-child")
    plugin_slug = str(wp_assets.get("plugin", {}).get("slug") or "seoulmna-platform-bridge")

    pages = [
        _page(
            "home",
            "/",
            "서울건설정보 메인 플랫폼",
            wordpress_page_slug="home",
            goal="split_public_intent_before_tool_use",
            calculator_policy="cta_only_no_iframe",
            sections=[
                "platform_hero",
                "service_split_cards",
                "trust_metrics",
                "listing_market_bridge",
                "knowledge_entry_strip",
                "consult_cta_band",
            ],
            primary_cta="/yangdo",
            secondary_cta="/permit",
        ),
        _page(
            "yangdo",
            "/yangdo",
            "AI 양도가 산정 · 유사매물 추천",
            wordpress_page_slug="yangdo",
            goal="qualify_mna_buyers_with_estimate_and_listing_recommendation_before_human_consult",
            calculator_policy="lazy_gate_shortcode",
            sections=[
                "yangdo_service_hero",
                "valuation_method_strip",
                "recommendation_precision_strip",
                "recommendation_reason_grid",
                "calculator_gate",
                "proof_notes",
                "case_loop",
                "consult_cta_band",
            ],
            primary_cta='[seoulmna_calc_gate type="yangdo"]',
            secondary_cta="/consult?intent=yangdo",
        ),
        _page(
            "permit",
            "/permit",
            "AI 인허가 사전검토",
            wordpress_page_slug="permit",
            goal="qualify_registration_readiness_before_operator_touch",
            calculator_policy="lazy_gate_shortcode",
            sections=[
                "permit_service_hero",
                "criteria_overview",
                "calculator_gate",
                "document_checklist_explainer",
                "knowledge_crosslinks",
                "consult_cta_band",
            ],
            primary_cta='[seoulmna_calc_gate type="permit"]',
            secondary_cta="/consult?intent=permit",
        ),
        _page(
            "knowledge",
            "/knowledge",
            "등록기준 · 양도양수 지식베이스",
            wordpress_page_slug="knowledge",
            goal="capture_search_intent_and_feed_service_pages",
            calculator_policy="cta_only_no_iframe",
            sections=[
                "knowledge_hub_hero",
                "topic_grid",
                "industry_guides",
                "case_studies",
                "service_return_strip",
            ],
            primary_cta="/permit",
            secondary_cta="/yangdo",
        ),
        _page(
            "consult",
            "/consult",
            "상담 접수",
            wordpress_page_slug="consult",
            goal="route_users_into_yangdo_or_permit_lane",
            calculator_policy="no_calculator_inline",
            sections=[
                "consult_router_hero",
                "intent_split_form",
                "response_time_promise",
                "faq",
            ],
            primary_cta="/consult?lane=form",
            secondary_cta="/knowledge",
        ),
        _page(
            "market_bridge",
            "/mna-market",
            "양도양수 매물 보기",
            wordpress_page_slug="mna-market",
            goal="bridge_platform_to_listing_market_without_mixing_runtime",
            calculator_policy="cta_only_no_iframe",
            sections=[
                "listing_bridge_hero",
                "market_explainer",
                "co_listing_redirect",
                "return_to_yangdo_strip",
            ],
            primary_cta=f"https://{co_host}",
            secondary_cta="/yangdo",
        ),
    ]

    lazy_pages = [row["page_id"] for row in pages if row["calculator_policy"] == "lazy_gate_shortcode"]
    cta_only_pages = [row["page_id"] for row in pages if row["calculator_policy"] == "cta_only_no_iframe"]
    nav = {
        "primary": [
            {"label": "플랫폼 소개", "href": "/"},
            {"label": "양도가", "href": "/yangdo"},
            {"label": "인허가", "href": "/permit"},
            {"label": "지식베이스", "href": "/knowledge"},
            {"label": "상담", "href": "/consult"},
        ],
        "utility": [
            {"label": "매물 사이트", "href": f"https://{co_host}"},
            {"label": "플랫폼 상태", "href": f"https://{kr_host}/_calc/health"},
        ],
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topology": {
            "platform_host": kr_host,
            "listing_host": co_host,
            "public_mount": public_mount,
            "theme_slug": theme_slug,
            "bridge_plugin_slug": plugin_slug,
        },
        "navigation": nav,
        "pages": pages,
        "summary": {
            "page_count": len(pages),
            "service_page_count": len([row for row in pages if row["page_id"] in {"yangdo", "permit"}]),
            "front_page_id": "home",
            "front_page_slug": "home",
            "lazy_gate_pages_count": len(lazy_pages),
            "cta_only_pages_count": len(cta_only_pages),
            "lazy_gate_pages": lazy_pages,
            "cta_only_pages": cta_only_pages,
        },
        "design_direction": {
            "theme": "editorial_platform_with_gated_tools",
            "rationale": "홈은 신뢰와 분기 역할을 맡고, 무거운 계산기 런타임은 사용자가 명시적으로 의도를 보인 서비스 페이지에서만 연다.",
            "guardrails": [
                "초기 페이지 렌더에서 계산기 iframe을 자동 생성하지 않는다.",
                ".co.kr는 매물 중심으로 유지하고 계산기 세션을 직접 섞지 않는다.",
                "사람 상담으로 넘어가기 전에 양도가/인허가 의도를 먼저 분기한다.",
            ],
        },
        "next_actions": [
            "WordPress staging에 home, yangdo, permit, knowledge, consult, market bridge 페이지를 생성한다.",
            "live 편집 전에 child theme와 bridge plugin을 staging에서 먼저 활성화한다.",
            "계산기 런타임은 seoulmna.kr/_calc/* 뒤에만 마운트하고 원점 upstream은 공개하지 않는다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# WordPress Platform IA",
        "",
        "## Topology",
        f"- platform_host: {payload.get('topology', {}).get('platform_host')}",
        f"- listing_host: {payload.get('topology', {}).get('listing_host')}",
        f"- public_mount: {payload.get('topology', {}).get('public_mount')}",
        "",
        "## Navigation",
    ]
    for row in payload.get("navigation", {}).get("primary", []):
        lines.append(f"- primary: {row.get('label')} -> {row.get('href')}")
    for row in payload.get("navigation", {}).get("utility", []):
        lines.append(f"- utility: {row.get('label')} -> {row.get('href')}")
    lines.extend(["", "## Pages"])
    for row in payload.get("pages", []):
        lines.append(f"- {row.get('slug')} [{row.get('calculator_policy')}]: {row.get('title')}")
        lines.append(f"  - wordpress_page_slug: {row.get('wordpress_page_slug')}")
        lines.append(f"  - goal: {row.get('goal')}")
        lines.append(f"  - sections: {', '.join(row.get('sections') or [])}")
        lines.append(f"  - primary_cta: {row.get('primary_cta')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the WordPress-first IA for seoulmna.kr.")
    parser.add_argument("--strategy", type=Path, default=DEFAULT_STRATEGY)
    parser.add_argument("--surface-audit", type=Path, default=DEFAULT_SURFACE_AUDIT)
    parser.add_argument("--wp-assets", type=Path, default=DEFAULT_WP_ASSETS)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wordpress_platform_ia_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wordpress_platform_ia_latest.md")
    args = parser.parse_args()

    payload = build_wordpress_platform_ia(
        strategy_path=args.strategy,
        surface_audit_path=args.surface_audit,
        wp_assets_path=args.wp_assets,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
