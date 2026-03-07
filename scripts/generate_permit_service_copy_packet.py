#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_UX = ROOT / "logs" / "wordpress_platform_ux_audit_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_service_copy_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_service_copy_packet_latest.md"


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


def build_permit_service_copy_packet(*, ia_path: Path, ux_path: Path, rental_path: Path) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    ux = _load_json(ux_path)
    rental = _load_json(rental_path)

    topology = ia.get("topology") if isinstance(ia.get("topology"), dict) else {}
    pages = ia.get("pages") if isinstance(ia.get("pages"), list) else []
    permit_page = next((row for row in pages if isinstance(row, dict) and row.get("page_id") == "permit"), {})
    summary = ux.get("summary") if isinstance(ux.get("summary"), dict) else {}
    rental_summary = rental.get("summary") if isinstance(rental.get("summary"), dict) else {}

    platform_host = str(topology.get("platform_host") or "seoulmna.kr")
    service_slug = str(permit_page.get("slug") or "/permit")
    consult_target = "/consult?intent=permit"
    knowledge_target = "/knowledge"
    gate_shortcode = str(permit_page.get("primary_cta") or '[seoulmna_calc_gate type="permit"]')

    packet_ready = bool(summary.get("ux_ok")) and bool(service_slug)
    checklist_story_ready = True
    manual_review_story_ready = True
    document_story_ready = int(rental_summary.get("permit_selector_entry_total", 0) or 0) > 0

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_service_copy_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "service_copy_ready": packet_ready,
            "checklist_story_ready": checklist_story_ready,
            "manual_review_story_ready": manual_review_story_ready,
            "document_story_ready": document_story_ready,
            "service_slug": service_slug,
            "platform_host": platform_host,
            "consult_target": consult_target,
            "knowledge_target": knowledge_target,
        },
        "hero": {
            "kicker": "AI 인허가 사전검토",
            "title": "등록기준을 즉시 판정하기보다, 부족 항목과 다음 조치를 먼저 분리해 주는 서비스로 정리합니다.",
            "body": "자본금, 기술인력, 사무실, 장비, 추가 등록기준을 한 번에 확인하고 즉시 통과/실패로 몰지 않고 증빙 체크리스트와 수동 검토 지점을 함께 안내합니다.",
            "gate_shortcode": gate_shortcode,
        },
        "explanation_cards": [
            {
                "title": "등록기준 부족 항목",
                "body": "자본금, 기술인력, 사무실, 장비와 같은 핵심 기준에서 무엇이 부족한지 먼저 보여줍니다.",
            },
            {
                "title": "증빙 체크리스트",
                "body": "부족 항목마다 어떤 서류와 준비가 필요한지 단계별 체크리스트로 이어집니다.",
            },
            {
                "title": "수동 검토 게이트",
                "body": "법령 추가 기준이 복잡하거나 업종 매핑 신뢰도가 낮으면 자동 판정 대신 수동 검토로 안전하게 전환합니다.",
            },
        ],
        "decision_paths": [
            {
                "when": "핵심 등록기준이 명확한 경우",
                "route": "self_check",
                "decision": "사전검토 결과와 체크리스트를 바로 확인",
            },
            {
                "when": "추가 기준이 많거나 업종 해석이 필요한 경우",
                "route": "manual_review",
                "decision": "상담/수동 검토로 즉시 전환",
            },
        ],
        "cta_ladder": {
            "primary_self_check": {
                "label": "사전검토 시작",
                "target": service_slug,
            },
            "secondary_consult": {
                "label": "인허가 상담 연결",
                "target": consult_target,
            },
            "supporting_knowledge": {
                "label": "등록기준 안내 보기",
                "target": knowledge_target,
            },
        },
        "copy_guardrails": [
            "홈과 지식 페이지에서는 계산기를 자동 실행하지 않는다.",
            "서비스 페이지에서만 lazy gate를 열고 클릭 전에는 iframe을 생성하지 않는다.",
            "자동 판정이 불충분하면 수동 검토와 증빙 체크리스트를 먼저 보여준다.",
            "등록기준이 복잡한 업종은 즉시 승인처럼 보이게 표현하지 않는다.",
        ],
        "proof_points": {
            "ux_ok": bool(summary.get("ux_ok")),
            "service_pages_ok": bool(summary.get("service_pages_ok")),
            "market_bridge_ok": bool(summary.get("market_bridge_ok")),
            "permit_selector_entry_total": int(rental_summary.get("permit_selector_entry_total", 0) or 0),
            "permit_platform_industry_total": int(rental_summary.get("permit_platform_industry_total", 0) or 0),
        },
        "next_actions": [
            "WordPress /permit 페이지에서 gate shortcode와 체크리스트 설명 카피를 기준으로 서비스면을 고정합니다.",
            "자동 판정과 수동 검토를 혼동하지 않도록 CTA와 설명 문구를 계속 분리합니다.",
            "임대형 permit widget/API도 공개 요약과 상세 체크리스트 노출 수준을 계속 분리합니다.",
        ],
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    hero = payload.get("hero") if isinstance(payload.get("hero"), dict) else {}
    lines = [
        "# Permit Service Copy Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- service_copy_ready: {summary.get('service_copy_ready')}",
        f"- checklist_story_ready: {summary.get('checklist_story_ready')}",
        f"- manual_review_story_ready: {summary.get('manual_review_story_ready')}",
        f"- document_story_ready: {summary.get('document_story_ready')}",
        f"- service_slug: {summary.get('service_slug')}",
        "",
        "## Hero",
        f"- kicker: {hero.get('kicker')}",
        f"- title: {hero.get('title')}",
        f"- body: {hero.get('body')}",
        "",
        "## CTA Ladder",
    ]
    ctas = payload.get("cta_ladder") if isinstance(payload.get("cta_ladder"), dict) else {}
    for key, row in ctas.items():
        if isinstance(row, dict):
            lines.append(f"- {key}: {row.get('label')} -> {row.get('target')}")
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate canonical permit service copy for the .kr platform.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--ux", type=Path, default=DEFAULT_UX)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_permit_service_copy_packet(
        ia_path=args.ia,
        ux_path=args.ux,
        rental_path=args.rental,
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
