#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_STRATEGY = ROOT / "logs" / "wordpress_platform_strategy_latest.json"
DEFAULT_PROXY_SPEC = ROOT / "logs" / "private_engine_proxy_spec_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _utm_url(base: str, *, source: str, medium: str, campaign: str, content: str, intent: str = "") -> str:
    params = {
        "utm_source": source,
        "utm_medium": medium,
        "utm_campaign": campaign,
        "utm_content": content,
    }
    if intent:
        params["intent"] = intent
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{urlencode(params)}"


def build_listing_platform_bridge_policy(*, ia_path: Path, strategy_path: Path, proxy_spec_path: Path) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    strategy = _load_json(strategy_path)
    proxy = _load_json(proxy_spec_path)

    platform_host = str(ia.get("topology", {}).get("platform_host") or proxy.get("topology", {}).get("main_platform_host") or "seoulmna.kr")
    listing_host = str(ia.get("topology", {}).get("listing_host") or proxy.get("topology", {}).get("listing_market_host") or "seoulmna.co.kr")

    yangdo_path = f"https://{platform_host}/yangdo"
    permit_path = f"https://{platform_host}/permit"
    consult_path = f"https://{platform_host}/consult"
    market_path = f"https://{platform_host}/mna-market"

    ctas = [
        {
            "placement": "listing_detail_primary",
            "target_service": "yangdo",
            "target_url": _utm_url(yangdo_path, source="co_listing", medium="detail_cta", campaign="listing_to_platform", content="detail_primary", intent="yangdo"),
            "copy": "이 매물 기준 양도가 범위 먼저 보기",
            "reason": "매물 상세에서 바로 양도가 산정 서비스로 보내 가장 강한 전환 흐름을 만든다.",
        },
        {
            "placement": "listing_detail_secondary",
            "target_service": "consult",
            "target_url": _utm_url(consult_path, source="co_listing", medium="detail_cta", campaign="listing_to_platform", content="detail_secondary", intent="yangdo"),
            "copy": "양도양수 상담 바로 연결",
            "reason": "즉시 계산보다 상담을 원하는 사용자를 별도 lane으로 분기한다.",
        },
        {
            "placement": "listing_nav_service",
            "target_service": "yangdo",
            "target_url": _utm_url(yangdo_path, source="co_listing", medium="global_nav", campaign="listing_to_platform", content="nav_yangdo", intent="yangdo"),
            "copy": "AI 양도가",
            "reason": "매물 사이트 전체에서 반복 노출 가능한 전역 서비스 진입 링크다.",
        },
        {
            "placement": "listing_nav_permit",
            "target_service": "permit",
            "target_url": _utm_url(permit_path, source="co_listing", medium="global_nav", campaign="listing_to_platform", content="nav_permit", intent="permit"),
            "copy": "AI 인허가 사전검토",
            "reason": "양도양수와 신규등록·인허가 준비 수요를 별도 lane으로 분기한다.",
        },
        {
            "placement": "listing_empty_state",
            "target_service": "market_bridge",
            "target_url": _utm_url(market_path, source="co_listing", medium="empty_state", campaign="listing_to_platform", content="empty_state_bridge"),
            "copy": "양도양수 플랫폼 안내 보기",
            "reason": "매물 검색 실패 사용자에게도 플랫폼 설명 페이지로 이어지는 복귀 경로를 준다.",
        },
    ]

    routing_rules = [
        {
            "rule_id": "co_detail_to_yangdo",
            "when": "매물 상세 페이지에서 가격 범위 판단이 먼저 필요한 경우",
            "send_to": ctas[0]["target_url"],
            "notes": "계산기는 .co.kr에 직접 임베드하지 않고 .kr 서비스 페이지로만 보낸다.",
        },
        {
            "rule_id": "co_detail_to_consult",
            "when": "사용자가 바로 상담을 원하거나 계산기 입력을 부담스러워하는 경우",
            "send_to": ctas[1]["target_url"],
            "notes": "상담 접수에서는 yangdo/permit intent를 유지한다.",
        },
        {
            "rule_id": "co_global_to_permit",
            "when": "사용자가 신규등록 또는 인허가 준비를 병행하는 경우",
            "send_to": ctas[3]["target_url"],
            "notes": "매물 사이트라도 permit lane은 .kr 서비스 페이지에서만 처리한다.",
        },
    ]

    tracking_contract = {
        "required_query_keys": ["utm_source", "utm_medium", "utm_campaign", "utm_content"],
        "recommended_values": {
            "utm_source": ["co_listing"],
            "utm_medium": ["detail_cta", "global_nav", "empty_state", "sidebar_banner"],
            "utm_campaign": ["listing_to_platform"],
            "utm_content": ["detail_primary", "detail_secondary", "nav_yangdo", "nav_permit", "empty_state_bridge"],
        },
        "intent_passthrough": ["yangdo", "permit"],
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "platform_host": platform_host,
            "listing_host": listing_host,
            "cta_count": len(ctas),
            "routing_rule_count": len(routing_rules),
            "listing_runtime_policy": "listing_domain_links_only_no_tool_embed",
        },
        "policy": {
            "listing_role": "listing_market_only",
            "platform_role": "brand_platform_and_service_entry",
            "calculator_runtime_policy": "never_embed_tools_on_listing_domain",
            "service_entry_policy": f"Route service demand from {listing_host} to {platform_host}/yangdo, /permit, or /consult with UTM tracking.",
        },
        "ctas": ctas,
        "routing_rules": routing_rules,
        "tracking_contract": tracking_contract,
        "brainstorm_extensions": [
            {
                "idea": "매물 상세 하단 인허가 체크리스트 배너",
                "impact": "permit lane 전환을 늘리면서도 매물 페이지 체류는 유지한다.",
            },
            {
                "idea": "매물 없음 상태의 2차 CTA",
                "impact": "즉시 전환하지 않은 사용자를 /yangdo 또는 /permit으로 다시 유도한다.",
            },
            {
                "idea": "상담 intent 자동 주입",
                "impact": "상담 접수에서 운영자가 수동으로 lane을 재분류하는 비용을 줄인다.",
            },
        ],
        "next_actions": [
            "Add listing detail and global navigation links on .co.kr that point back to the .kr service pages with UTM tags.",
            "Do not embed the calculator iframe on .co.kr pages; keep the listing domain lightweight and listing-focused.",
            "Pass intent=yangdo or intent=permit through the bridge so consult routing remains structured.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# Listing Platform Bridge Policy",
        "",
        f"- platform_host: {payload.get('summary', {}).get('platform_host')}",
        f"- listing_host: {payload.get('summary', {}).get('listing_host')}",
        f"- listing_runtime_policy: {payload.get('summary', {}).get('listing_runtime_policy')}",
        "",
        "## Policy",
    ]
    policy = payload.get("policy", {}) if isinstance(payload.get("policy"), dict) else {}
    for key, value in policy.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## CTAs"])
    for row in payload.get("ctas", []):
        lines.append(f"- {row.get('placement')} -> {row.get('target_service')}: {row.get('target_url')}")
        lines.append(f"  - copy: {row.get('copy')}")
    lines.extend(["", "## Routing Rules"])
    for row in payload.get("routing_rules", []):
        lines.append(f"- {row.get('rule_id')}: {row.get('when')}")
        lines.append(f"  - send_to: {row.get('send_to')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the .co.kr to .kr bridge policy and UTM contract.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--strategy", type=Path, default=DEFAULT_STRATEGY)
    parser.add_argument("--proxy-spec", type=Path, default=DEFAULT_PROXY_SPEC)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "listing_platform_bridge_policy_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "listing_platform_bridge_policy_latest.md")
    args = parser.parse_args()

    payload = build_listing_platform_bridge_policy(
        ia_path=args.ia,
        strategy_path=args.strategy,
        proxy_spec_path=args.proxy_spec,
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
