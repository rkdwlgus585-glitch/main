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
DEFAULT_COPY = ROOT / "logs" / "permit_service_copy_packet_latest.json"
DEFAULT_ALIGNMENT = ROOT / "logs" / "permit_service_alignment_audit_latest.json"
DEFAULT_RENTAL_LANE = ROOT / "logs" / "permit_rental_lane_packet_latest.json"
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_service_ux_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_service_ux_packet_latest.md"


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


def build_permit_service_ux_packet(
    *,
    ia_path: Path,
    ux_audit_path: Path,
    copy_path: Path,
    alignment_path: Path,
    rental_lane_path: Path,
    rental_path: Path,
) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    ux_audit = _load_json(ux_audit_path)
    copy_packet = _load_json(copy_path)
    alignment = _load_json(alignment_path)
    rental_lane = _load_json(rental_lane_path)
    rental_catalog = _load_json(rental_path)

    topology = ia.get("topology") if isinstance(ia.get("topology"), dict) else {}
    pages = ia.get("pages") if isinstance(ia.get("pages"), list) else []
    permit_page = next((row for row in pages if isinstance(row, dict) and row.get("page_id") == "permit"), {})
    ux_summary = ux_audit.get("summary") if isinstance(ux_audit.get("summary"), dict) else {}
    copy_summary = copy_packet.get("summary") if isinstance(copy_packet.get("summary"), dict) else {}
    copy_hero = copy_packet.get("hero") if isinstance(copy_packet.get("hero"), dict) else {}
    copy_cta = copy_packet.get("cta_ladder") if isinstance(copy_packet.get("cta_ladder"), dict) else {}
    copy_lanes = copy_packet.get("lane_ladder") if isinstance(copy_packet.get("lane_ladder"), dict) else {}
    alignment_summary = alignment.get("summary") if isinstance(alignment.get("summary"), dict) else {}
    rental_lane_summary = rental_lane.get("summary") if isinstance(rental_lane.get("summary"), dict) else {}
    rental_lane_matrix = rental_lane.get("lane_matrix") if isinstance(rental_lane.get("lane_matrix"), dict) else {}
    rental_summary = rental_catalog.get("summary") if isinstance(rental_catalog.get("summary"), dict) else {}
    permit_precheck = (((rental_catalog.get("packaging") or {}).get("partner_rental") or {}).get("permit_precheck") or {})
    permit_precheck = permit_precheck if isinstance(permit_precheck, dict) else {}

    platform_host = str(copy_summary.get("platform_host") or topology.get("platform_host") or "seoulmna.kr")
    service_slug = str(copy_summary.get("service_slug") or permit_page.get("slug") or "/permit")
    consult_target = str(copy_summary.get("consult_target") or "/consult?intent=permit")
    knowledge_target = str(copy_summary.get("knowledge_target") or "/knowledge")
    gate_shortcode = str(copy_hero.get("gate_shortcode") or permit_page.get("primary_cta") or '[seoulmna_calc_gate type="permit"]')

    summary_fields = [
        "overall_status",
        "required_summary",
        "next_actions",
    ]
    detail_fields = [
        "criterion_results",
        "evidence_checklist",
        "document_templates",
        "legal_basis",
    ]
    assist_fields = [
        "criterion_results",
        "evidence_checklist",
        "document_templates",
        "legal_basis",
        "manual_review_required",
        "coverage_status",
    ]
    internal_fields = assist_fields + ["pending_criteria_lines", "mapping_confidence"]

    # This packet defines the intended service UX contract and should be
    # generatable before the downstream page/UX audit runs in refresh.
    packet_ready = all(
        [
            bool(copy_summary.get("packet_ready")),
            bool(copy_summary.get("service_flow_ready")),
            bool(alignment_summary.get("alignment_ok")),
            bool(rental_lane_summary.get("packet_ready")),
            bool(service_slug),
            bool(gate_shortcode),
        ]
    )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_service_ux_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "service_surface_ready": bool(service_slug) and bool(gate_shortcode),
            "lane_exposure_ready": bool(rental_lane_summary.get("lane_ladder_ready")),
            "alignment_ready": bool(alignment_summary.get("alignment_ok")),
            "service_flow_policy": "public_summary_then_checklist_or_manual_review",
            "platform_host": platform_host,
            "service_slug": service_slug,
            "consult_target": consult_target,
        },
        "service_surface": {
            "page_title": str(copy_hero.get("title") or permit_page.get("title") or "AI 인허가 사전검토"),
            "service_url": f"https://{platform_host}{service_slug}",
            "gate_shortcode": gate_shortcode,
            "hero_kicker": str(copy_hero.get("kicker") or ""),
            "hero_body": str(copy_hero.get("body") or ""),
            "required_sections": [
                "등록기준 요약",
                "부족 항목 설명",
                "상세 체크리스트",
                "수동 검토 보조",
                "다음 조치",
            ],
        },
        "public_summary_experience": {
            "audience": "public_platform_user",
            "visible_fields": summary_fields,
            "story": str(permit_precheck.get("public_story") or "기본 자가진단 결과와 부족 항목 요약만 먼저 보여줍니다."),
            "cta_primary_label": str(((copy_cta.get("primary_self_check") or {}).get("label")) or "사전검토 시작"),
            "cta_primary_target": service_slug,
            "cta_secondary_label": str(((copy_cta.get("supporting_knowledge") or {}).get("label")) or "등록기준 안내 보기"),
            "cta_secondary_target": knowledge_target,
            "allowed_offerings": _as_list(((rental_lane_matrix.get("summary_self_check") or {}).get("offerings"))),
            "notes": [
                "공개 화면에서는 빠른 자가진단과 부족 항목 요약만 보여줍니다.",
                "복잡한 해석과 수동 판단은 공개 요약에서 약속하지 않습니다.",
            ],
        },
        "detail_checklist_experience": {
            "audience": "partner_detail_checklist",
            "visible_fields": detail_fields,
            "story": str(permit_precheck.get("detail_story") or "기준별 판정과 증빙 체크리스트를 구조화해 제공합니다."),
            "cta_primary_label": "상세 체크리스트 보기",
            "cta_primary_target": service_slug,
            "allowed_offerings": _as_list(((rental_lane_matrix.get("detail_checklist") or {}).get("offerings"))),
            "notes": [
                "기준별 결과와 증빙 체크리스트를 보되, 상담 전환은 기본 포함하지 않습니다.",
                "explainable lane으로서 자동 판정의 한계와 범위를 분명히 유지합니다.",
            ],
        },
        "manual_review_assist_experience": {
            "audience": "partner_manual_review_assist",
            "visible_fields": assist_fields,
            "story": str(permit_precheck.get("assist_story") or "예외와 추가 기준이 많은 케이스를 수동 검토 보조로 연결합니다."),
            "cta_primary_label": str(((copy_cta.get("secondary_consult") or {}).get("label")) or "수동 검토 요청"),
            "cta_primary_target": consult_target,
            "allowed_offerings": _as_list(((rental_lane_matrix.get("manual_review_assist") or {}).get("offerings"))),
            "notes": [
                "수동 검토 보조는 자동 판정 결과를 덮어쓰는 기능이 아니라, 복잡한 예외를 안전하게 넘기는 lane입니다.",
                "책임 있는 안내가 어려운 구간만 상담형 흐름으로 분리합니다.",
            ],
        },
        "internal_review_experience": {
            "audience": "internal_operator",
            "visible_fields": internal_fields,
            "story": "내부 운영은 pending criteria와 mapping confidence까지 직접 검토합니다.",
            "allowed_offerings": _as_list(((rental_lane_matrix.get("internal_full") or {}).get("offerings"))),
        },
        "lane_ladder": {
            "summary_self_check": {
                "label": str(((copy_lanes.get("summary_self_check") or {}).get("label")) or "자가진단 요약"),
                "offering_ids": _as_list(((copy_lanes.get("summary_self_check") or {}).get("offering_ids"))),
                "upgrade_target": str(((copy_lanes.get("summary_self_check") or {}).get("upgrade_target")) or "detail_checklist"),
            },
            "detail_checklist": {
                "label": str(((copy_lanes.get("detail_checklist") or {}).get("label")) or "상세 체크리스트"),
                "offering_ids": _as_list(((copy_lanes.get("detail_checklist") or {}).get("offering_ids"))),
                "upgrade_target": str(((copy_lanes.get("detail_checklist") or {}).get("upgrade_target")) or "manual_review_assist"),
            },
            "manual_review_assist": {
                "label": str(((copy_lanes.get("manual_review_assist") or {}).get("label")) or "수동 검토 보조"),
                "offering_ids": _as_list(((copy_lanes.get("manual_review_assist") or {}).get("offering_ids"))),
                "upgrade_target": str(((copy_lanes.get("manual_review_assist") or {}).get("upgrade_target")) or "internal_full"),
            },
        },
        "proof_points": {
            "ux_ok": bool(ux_summary.get("ux_ok")),
            "service_pages_ok": bool(ux_summary.get("service_pages_ok")),
            "permit_selector_entry_total": int(rental_summary.get("permit_selector_entry_total", 0) or 0),
            "permit_offering_count": int(rental_summary.get("permit_offering_count", 0) or 0),
        },
        "brainstorm_backlog": [
            {
                "idea": "수동 검토 보조 진입 조건을 실제 예외 케이스 예시와 함께 보여주기",
                "expected_impact": "사용자가 왜 자동 판정에서 상담형 흐름으로 넘어가는지 더 쉽게 납득할 수 있습니다.",
                "status": "planned",
            },
            {
                "idea": "상세 체크리스트와 수동 검토 보조 사이의 책임 차이를 CTA 옆에 짧게 표기",
                "expected_impact": "detail 상품과 assist 상품의 업셀 이유가 더 선명해집니다.",
                "status": "planned",
            },
        ],
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Permit Service UX Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- service_surface_ready: {summary.get('service_surface_ready')}",
        f"- lane_exposure_ready: {summary.get('lane_exposure_ready')}",
        f"- alignment_ready: {summary.get('alignment_ready')}",
        f"- service_flow_policy: {summary.get('service_flow_policy')}",
        "",
        "## Lanes",
    ]
    for key, row in (payload.get("lane_ladder") or {}).items():
        if isinstance(row, dict):
            lines.append(f"- {key}: {row.get('label')} / offerings={', '.join(row.get('offering_ids') or []) or '(none)'} / upgrade={row.get('upgrade_target') or '(none)'}")
    lines.extend(["", "## Experiences"])
    for key in ["public_summary_experience", "detail_checklist_experience", "manual_review_assist_experience"]:
        row = payload.get(key) if isinstance(payload.get(key), dict) else {}
        if row:
            lines.append(f"- {key}: offerings={', '.join(row.get('allowed_offerings') or []) or '(none)'} / cta={row.get('cta_primary_label') or '(none)'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate canonical permit service UX packet for the .kr platform.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--ux-audit", type=Path, default=DEFAULT_UX_AUDIT)
    parser.add_argument("--copy", type=Path, default=DEFAULT_COPY)
    parser.add_argument("--alignment", type=Path, default=DEFAULT_ALIGNMENT)
    parser.add_argument("--rental-lane", type=Path, default=DEFAULT_RENTAL_LANE)
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_permit_service_ux_packet(
        ia_path=args.ia,
        ux_audit_path=args.ux_audit,
        copy_path=args.copy,
        alignment_path=args.alignment,
        rental_lane_path=args.rental_lane,
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
