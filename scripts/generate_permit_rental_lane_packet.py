#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RENTAL = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_COPY = ROOT / "logs" / "permit_service_copy_packet_latest.json"
DEFAULT_ALIGNMENT = ROOT / "logs" / "permit_service_alignment_audit_latest.json"
DEFAULT_ATTORNEY = ROOT / "logs" / "attorney_handoff_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_rental_lane_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_rental_lane_packet_latest.md"


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


def _track_b(payload: Dict[str, Any]) -> Dict[str, Any]:
    tracks = payload.get("tracks") if isinstance(payload.get("tracks"), list) else []
    for row in tracks:
        if isinstance(row, dict) and row.get("track_id") == "B":
            return row
    return {}


def build_permit_rental_lane_packet(
    *,
    rental_path: Path,
    copy_path: Path,
    alignment_path: Path,
    attorney_path: Path,
) -> Dict[str, Any]:
    rental = _load_json(rental_path)
    copy_packet = _load_json(copy_path)
    alignment = _load_json(alignment_path)
    attorney = _load_json(attorney_path)

    packaging = rental.get("packaging") if isinstance(rental.get("packaging"), dict) else {}
    partner_rental = packaging.get("partner_rental") if isinstance(packaging.get("partner_rental"), dict) else {}
    permit_precheck = partner_rental.get("permit_precheck") if isinstance(partner_rental.get("permit_precheck"), dict) else {}
    package_matrix = permit_precheck.get("package_matrix") if isinstance(permit_precheck.get("package_matrix"), dict) else {}
    lane_positioning = permit_precheck.get("lane_positioning") if isinstance(permit_precheck.get("lane_positioning"), dict) else {}
    copy_summary = copy_packet.get("summary") if isinstance(copy_packet.get("summary"), dict) else {}
    copy_hero = copy_packet.get("hero") if isinstance(copy_packet.get("hero"), dict) else {}
    copy_ctas = copy_packet.get("cta_ladder") if isinstance(copy_packet.get("cta_ladder"), dict) else {}
    alignment_summary = alignment.get("summary") if isinstance(alignment.get("summary"), dict) else {}
    rental_summary = rental.get("summary") if isinstance(rental.get("summary"), dict) else {}
    track_b = _track_b(attorney)
    attorney_position = track_b.get("attorney_position") if isinstance(track_b.get("attorney_position"), dict) else {}

    summary_offerings = _as_list(((package_matrix.get("summary_self_check") or {}).get("offering_ids")))
    detail_offerings = _as_list(((package_matrix.get("detail_checklist") or {}).get("offering_ids")))
    assist_offerings = _as_list(((package_matrix.get("manual_review_assist") or {}).get("offering_ids")))
    internal_offerings = _as_list(((package_matrix.get("internal_full") or {}).get("offering_ids")))

    packet_ready = (
        bool(copy_summary.get("service_flow_ready"))
        and bool(alignment_summary.get("alignment_ok"))
        and bool(summary_offerings)
        and bool(detail_offerings)
        and bool(assist_offerings)
    )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_rental_lane_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "lane_ladder_ready": bool(copy_summary.get("lane_ladder_ready")),
            "commercial_story_ready": bool(copy_summary.get("service_flow_ready")) and bool(alignment_summary.get("alignment_ok")),
            "detail_checklist_lane_ready": bool(detail_offerings),
            "manual_review_assist_lane_ready": bool(assist_offerings),
            "permit_offering_count": int(rental_summary.get("permit_offering_count", 0) or 0),
        },
        "lane_matrix": {
            "summary_self_check": {
                "label": "자가진단 요약",
                "offerings": summary_offerings,
                "upgrade_target": str(((lane_positioning.get("summary_self_check") or {}).get("upgrade_target")) or "detail_checklist"),
                "sales_story": "공개 위젯이나 기본 패키지에서 빠른 pass/fail 요약과 부족 항목 요약만 제공하는 진입 lane입니다.",
            },
            "detail_checklist": {
                "label": "상세 체크리스트",
                "offerings": detail_offerings,
                "upgrade_target": str(((lane_positioning.get("detail_checklist") or {}).get("upgrade_target")) or "manual_review_assist"),
                "sales_story": "항목별 판정과 증빙 체크리스트를 제공하되, 수동 검토 단계는 기본 포함하지 않는 explainable lane입니다.",
            },
            "manual_review_assist": {
                "label": "수동 검토 보조",
                "offerings": assist_offerings,
                "upgrade_target": str(((lane_positioning.get("manual_review_assist") or {}).get("upgrade_target")) or "internal_full"),
                "sales_story": "복잡한 등록기준과 예외를 상담 또는 수동 검토 흐름으로 연결하는 assist lane입니다.",
            },
            "internal_full": {
                "label": "내부 운영",
                "offerings": internal_offerings,
                "upgrade_target": "",
                "sales_story": "pending criteria, registry 정렬, QA 내부 검토까지 포함하는 운영 전용 lane입니다.",
            },
        },
        "sales_ladder": [
            {
                "from": "summary_self_check",
                "to": "detail_checklist",
                "trigger": "부족 항목 요약만으로는 증빙 준비와 다음 조치를 판단하기 어려울 때",
            },
            {
                "from": "detail_checklist",
                "to": "manual_review_assist",
                "trigger": "예외와 추가 기준 때문에 자동 판정만으로 책임 있게 안내하기 어려울 때",
            },
            {
                "from": "manual_review_assist",
                "to": "internal_full",
                "trigger": "내부 검수와 pending criteria 정렬까지 함께 필요한 운영 상황일 때",
            },
        ],
        "cta_contract": {
            "primary_self_check": str(((copy_ctas.get("primary_self_check") or {}).get("label")) or "사전검토 시작"),
            "secondary_consult": str(((copy_ctas.get("secondary_consult") or {}).get("label")) or "수동 검토 요청"),
            "knowledge": str(((copy_ctas.get("supporting_knowledge") or {}).get("label")) or "등록기준 안내 보기"),
        },
        "service_story": {
            "hero_title": str(copy_hero.get("title") or ""),
            "hero_body": str(copy_hero.get("body") or ""),
            "platform_host": str(copy_summary.get("platform_host") or "seoulmna.kr"),
            "service_slug": str(copy_summary.get("service_slug") or "/permit"),
            "consult_target": str(copy_summary.get("consult_target") or "/consult?intent=permit"),
        },
        "attorney_alignment": {
            "claim_focus": _as_list(attorney_position.get("claim_focus")),
            "commercial_positioning": _as_list(attorney_position.get("commercial_positioning")),
        },
        "next_actions": [
            "permit 상품 설명은 summary -> detail -> assist 사다리를 기준으로 일관되게 유지합니다.",
            "detail_checklist lane은 설명 가능한 체크리스트에 집중하고, 상담 전환은 manual_review_assist lane에서만 강조합니다.",
            "서비스 카피와 임대 상품 설명은 같은 CTA 계약과 같은 upgrade target을 유지합니다.",
        ],
        "artifacts": {
            "rental_catalog": str(rental_path.resolve()),
            "service_copy_packet": str(copy_path.resolve()),
            "alignment_audit": str(alignment_path.resolve()),
            "attorney_handoff": str(attorney_path.resolve()),
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Permit Rental Lane Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- lane_ladder_ready: {summary.get('lane_ladder_ready')}",
        f"- commercial_story_ready: {summary.get('commercial_story_ready')}",
        f"- detail_checklist_lane_ready: {summary.get('detail_checklist_lane_ready')}",
        f"- manual_review_assist_lane_ready: {summary.get('manual_review_assist_lane_ready')}",
        "",
        "## Lane Matrix",
    ]
    for key, row in (payload.get("lane_matrix") or {}).items():
        if isinstance(row, dict):
            lines.append(
                f"- {key}: {row.get('label')} / offerings={', '.join(row.get('offerings') or []) or '(none)'} / upgrade={row.get('upgrade_target') or '(none)'}"
            )
    lines.extend(["", "## Sales Ladder"])
    for row in payload.get("sales_ladder", []):
        if isinstance(row, dict):
            lines.append(f"- {row.get('from')} -> {row.get('to')}: {row.get('trigger')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate permit rental lane positioning packet.")
    parser.add_argument("--rental", type=Path, default=DEFAULT_RENTAL)
    parser.add_argument("--copy", type=Path, default=DEFAULT_COPY)
    parser.add_argument("--alignment", type=Path, default=DEFAULT_ALIGNMENT)
    parser.add_argument("--attorney", type=Path, default=DEFAULT_ATTORNEY)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_permit_rental_lane_packet(
        rental_path=args.rental,
        copy_path=args.copy,
        alignment_path=args.alignment,
        attorney_path=args.attorney,
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
