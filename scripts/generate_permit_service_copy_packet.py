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
    ux_summary = ux.get("summary") if isinstance(ux.get("summary"), dict) else {}
    rental_summary = rental.get("summary") if isinstance(rental.get("summary"), dict) else {}
    packaging = rental.get("packaging") if isinstance(rental.get("packaging"), dict) else {}
    partner_rental = packaging.get("partner_rental") if isinstance(packaging.get("partner_rental"), dict) else {}
    permit_precheck = partner_rental.get("permit_precheck") if isinstance(partner_rental.get("permit_precheck"), dict) else {}
    lane_positioning = permit_precheck.get("lane_positioning") if isinstance(permit_precheck.get("lane_positioning"), dict) else {}
    package_matrix = permit_precheck.get("package_matrix") if isinstance(permit_precheck.get("package_matrix"), dict) else {}

    platform_host = str(topology.get("platform_host") or "seoulmna.kr")
    service_slug = str(permit_page.get("slug") or "/permit")
    consult_target = "/consult?intent=permit"
    knowledge_target = "/knowledge"
    gate_shortcode = str(permit_page.get("primary_cta") or '[seoulmna_calc_gate type="permit"]')

    summary_self_check_offerings = _as_list(((package_matrix.get("summary_self_check") or {}).get("offering_ids")))
    detail_checklist_offerings = _as_list(((package_matrix.get("detail_checklist") or {}).get("offering_ids")))
    manual_review_assist_offerings = _as_list(((package_matrix.get("manual_review_assist") or {}).get("offering_ids")))
    internal_offerings = _as_list(((package_matrix.get("internal_full") or {}).get("offering_ids")))

    # This packet defines the canonical service copy contract and should be
    # generatable before the downstream UX audit runs in the refresh chain.
    packet_ready = bool(service_slug)
    checklist_story_ready = bool(detail_checklist_offerings)
    manual_review_story_ready = bool(manual_review_assist_offerings or lane_positioning.get("manual_review_assist"))
    document_story_ready = int(rental_summary.get("permit_selector_entry_total", 0) or 0) > 0
    lane_ladder_ready = bool(summary_self_check_offerings) and checklist_story_ready and manual_review_story_ready
    service_flow_ready = packet_ready and lane_ladder_ready

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_service_copy_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "service_copy_ready": packet_ready,
            "checklist_story_ready": checklist_story_ready,
            "manual_review_story_ready": manual_review_story_ready,
            "document_story_ready": document_story_ready,
            "lane_ladder_ready": lane_ladder_ready,
            "service_flow_ready": service_flow_ready,
            "service_slug": service_slug,
            "platform_host": platform_host,
            "consult_target": consult_target,
            "knowledge_target": knowledge_target,
        },
        "hero": {
            "kicker": "AI 인허가 사전검토",
            "title": "등록기준 부족 항목과 다음 조치를 단계별로 보여주는 인허가 플랫폼",
            "body": "기본 자가진단으로 시작하고, 필요할 때만 상세 체크리스트와 수동 검토 보조 단계로 올라가 책임과 운영비를 함께 관리합니다.",
            "gate_shortcode": gate_shortcode,
        },
        "explanation_cards": [
            {
                "title": "자가진단 요약",
                "body": "현재 입력만으로 통과 가능 여부와 부족 항목을 빠르게 요약합니다.",
            },
            {
                "title": "상세 체크리스트",
                "body": "기준 항목별 판정 결과, 증빙 체크리스트, 다음 조치를 구조화해 보여줍니다.",
            },
            {
                "title": "수동 검토 보조",
                "body": "기준 해석이 복잡하거나 예외가 많은 경우 수동 검토 보조 단계로 올려 책임 범위를 분리합니다.",
            },
        ],
        "decision_paths": [
            {
                "when": "기본 등록기준이 명확하고 입력이 충분한 경우",
                "route": "summary_self_check",
                "decision": "즉시 자가진단 결과와 체크리스트를 확인",
            },
            {
                "when": "추가 기준이 많거나 해석이 복잡한 경우",
                "route": "manual_review_assist",
                "decision": "수동 검토 보조와 상담형 후속 조치로 전환",
            },
        ],
        "lane_ladder": {
            "summary_self_check": {
                "label": "자가진단 요약",
                "offering_ids": summary_self_check_offerings,
                "upgrade_target": str(((lane_positioning.get("summary_self_check") or {}).get("upgrade_target")) or "detail_checklist"),
                "story": "기본 입력만으로 pass/fail 요약과 부족 항목을 빠르게 확인합니다.",
            },
            "detail_checklist": {
                "label": "상세 체크리스트",
                "offering_ids": detail_checklist_offerings,
                "upgrade_target": str(((lane_positioning.get("detail_checklist") or {}).get("upgrade_target")) or "manual_review_assist"),
                "story": "기준 항목별 판정, 증빙 체크리스트, 다음 조치를 함께 보여줍니다.",
            },
            "manual_review_assist": {
                "label": "수동 검토 보조",
                "offering_ids": manual_review_assist_offerings,
                "upgrade_target": str(((lane_positioning.get("manual_review_assist") or {}).get("upgrade_target")) or "internal_full"),
                "story": "복잡한 기준과 추가 등록기준은 수동 검토 보조 lane으로 올려 처리합니다.",
            },
            "internal_full": {
                "label": "내부 운영",
                "offering_ids": internal_offerings,
                "upgrade_target": "",
                "story": "내부 운영은 pending criteria와 registry 정렬까지 직접 봅니다.",
            },
        },
        "lane_compare_table": [
            {
                "lane": "summary_self_check",
                "label": "자가진단 요약",
                "best_for": "빠르게 통과 가능성만 확인하려는 첫 진입 사용자",
                "primary_output": "pass/fail 요약, 부족 항목 요약",
                "upgrade_reason": "부족 항목의 정확한 준비 순서와 증빙까지 보려면 다음 단계가 필요합니다.",
            },
            {
                "lane": "detail_checklist",
                "label": "상세 체크리스트",
                "best_for": "기준별 준비 수준과 증빙 목록을 구조적으로 확인하려는 사용자",
                "primary_output": "기준 항목별 판정, 증빙 체크리스트, 다음 조치",
                "upgrade_reason": "예외 해석, 수동 판단, 업종별 특례가 많으면 수동 검토 보조가 필요합니다.",
            },
            {
                "lane": "manual_review_assist",
                "label": "수동 검토 보조",
                "best_for": "기준 해석이 어렵거나 예외가 많은 케이스를 다루는 사용자",
                "primary_output": "manual-review gate, 보조 의견, 후속 상담 동선",
                "upgrade_reason": "내부 운영에서는 registry 정렬과 QA까지 함께 봐야 합니다.",
            },
        ],
        "upgrade_reasons": {
            "summary_to_detail": "부족 항목을 실제 준비 항목과 증빙 기준으로 바꿔 읽어야 할 때",
            "detail_to_assist": "예외, 추가 기준, 특례 해석 때문에 자동 판정만으로 책임 있게 안내하기 어려울 때",
            "assist_to_internal": "내부 운영 수준의 pending criteria 정렬과 QA 검토가 같이 필요할 때",
        },
        "cta_ladder": {
            "primary_self_check": {
                "label": "사전검토 시작",
                "target": service_slug,
            },
            "secondary_consult": {
                "label": "수동 검토 요청",
                "target": consult_target,
            },
            "supporting_knowledge": {
                "label": "등록기준 안내 보기",
                "target": knowledge_target,
            },
        },
        "copy_guardrails": [
            "홈과 지식 페이지에서는 계산기를 자동 실행하지 않는다.",
            "서비스 페이지에서만 lazy gate를 열고 클릭 전에는 iframe을 만들지 않는다.",
            "자가진단과 수동 검토 보조를 같은 문구로 섞어 쓰지 않는다.",
            "복잡한 기준을 즉시 확정 판정처럼 보이게 표현하지 않는다.",
        ],
        "proof_points": {
            "ux_ok": bool(ux_summary.get("ux_ok")),
            "service_pages_ok": bool(ux_summary.get("service_pages_ok")),
            "market_bridge_ok": bool(ux_summary.get("market_bridge_ok")),
            "permit_selector_entry_total": int(rental_summary.get("permit_selector_entry_total", 0) or 0),
            "permit_platform_industry_total": int(rental_summary.get("permit_platform_industry_total", 0) or 0),
        },
        "offering_matrix": {
            "summary_self_check": summary_self_check_offerings,
            "detail_checklist": detail_checklist_offerings,
            "manual_review_assist": manual_review_assist_offerings,
            "internal_full": internal_offerings,
        },
        "next_actions": [
            "WordPress /permit 페이지에서 자가진단, 상세 체크리스트, 수동 검토 보조의 순서를 더 선명하게 고정합니다.",
            "상세 체크리스트 lane과 수동 검토 보조 lane의 CTA와 설명 문구를 계속 분리합니다.",
            "permit 상품을 summary -> detail -> assist 사다리로 판매할 수 있도록 운영 산출물과 카탈로그를 계속 맞춥니다.",
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
        f"- lane_ladder_ready: {summary.get('lane_ladder_ready')}",
        f"- service_flow_ready: {summary.get('service_flow_ready')}",
        f"- service_slug: {summary.get('service_slug')}",
        "",
        "## Hero",
        f"- kicker: {hero.get('kicker')}",
        f"- title: {hero.get('title')}",
        f"- body: {hero.get('body')}",
        "",
        "## Lane Ladder",
    ]
    for key, row in (payload.get("lane_ladder") or {}).items():
        if isinstance(row, dict):
            lines.append(f"- {key}: {row.get('label')} / offerings={', '.join(row.get('offering_ids') or []) or '(none)'} / upgrade={row.get('upgrade_target') or '(none)'}")
    lines.extend(["", "## Lane Compare"])
    for row in payload.get("lane_compare_table", []):
        if isinstance(row, dict):
            lines.append(
                f"- {row.get('lane')}: {row.get('label')} / best_for={row.get('best_for')} / output={row.get('primary_output')} / upgrade_reason={row.get('upgrade_reason')}"
            )
    upgrade_reasons = payload.get("upgrade_reasons") if isinstance(payload.get("upgrade_reasons"), dict) else {}
    if upgrade_reasons:
        lines.extend(["", "## Upgrade Reasons"])
        for key, value in upgrade_reasons.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## CTA Ladder"])
    for key, row in (payload.get("cta_ladder") or {}).items():
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

    payload = build_permit_service_copy_packet(ia_path=args.ia, ux_path=args.ux, rental_path=args.rental)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("packet_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
