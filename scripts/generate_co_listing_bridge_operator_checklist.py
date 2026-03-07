#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "logs" / "listing_platform_bridge_policy_latest.json"
DEFAULT_SNIPPETS = ROOT / "logs" / "co_listing_bridge_snippets_latest.json"
DEFAULT_JSON = ROOT / "logs" / "co_listing_bridge_operator_checklist_latest.json"
DEFAULT_MD = ROOT / "logs" / "co_listing_bridge_operator_checklist_latest.md"

PLACEMENT_HINTS: Dict[str, Dict[str, str]] = {
    "listing_detail_primary": {
        "location": "매물 상세 상단의 첫 번째 주요 CTA 영역",
        "validation": "상세 첫 화면에서 '이 매물 기준 양도가 범위 먼저 보기' 버튼이 노출되고 .kr/yangdo로 이동해야 한다.",
    },
    "listing_detail_secondary": {
        "location": "매물 상세 하단 또는 상담 유도 보조 CTA 영역",
        "validation": "보조 CTA가 /consult?intent=yangdo 로 이동하고, 계산기 iframe은 .co.kr에 생성되지 않아야 한다.",
    },
    "listing_nav_service": {
        "location": "전역 네비게이션 또는 헤더 서비스 메뉴",
        "validation": "전역 메뉴에서 AI 양도가를 눌렀을 때 .kr/yangdo로 이동해야 한다.",
    },
    "listing_nav_permit": {
        "location": "전역 네비게이션의 인허가/신규등록 진입 슬롯",
        "validation": "전역 메뉴에서 AI 인허가 사전검토를 눌렀을 때 .kr/permit로 이동해야 한다.",
    },
    "listing_empty_state": {
        "location": "검색 결과 없음 또는 빈 상태 카드",
        "validation": "빈 상태에서도 플랫폼 안내 페이지로 이동하는 CTA가 보여야 한다.",
    },
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_co_listing_bridge_operator_checklist(*, policy_path: Path, snippets_path: Path) -> Dict[str, Any]:
    policy = _load_json(policy_path)
    snippets = _load_json(snippets_path)
    summary = policy.get("summary") if isinstance(policy.get("summary"), dict) else {}
    ctas = policy.get("ctas") if isinstance(policy.get("ctas"), list) else []
    files = snippets.get("files") if isinstance(snippets.get("files"), list) else []
    file_map = {
        str(row.get("placement") or "").strip(): str(row.get("path") or "").strip()
        for row in files
        if isinstance(row, dict)
    }

    placement_items: List[Dict[str, str]] = []
    for row in ctas:
        if not isinstance(row, dict):
            continue
        placement = str(row.get("placement") or "").strip()
        hint = PLACEMENT_HINTS.get(placement, {})
        placement_items.append(
            {
                "placement": placement,
                "target_service": str(row.get("target_service") or ""),
                "copy": str(row.get("copy") or ""),
                "target_url": str(row.get("target_url") or ""),
                "snippet_file": file_map.get(placement, ""),
                "location_hint": hint.get("location", "적절한 노출 위치를 운영자가 지정"),
                "validation_hint": hint.get("validation", "클릭 시 .kr 서비스 페이지로 이동하는지 확인"),
            }
        )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "listing_host": str(summary.get("listing_host") or "seoulmna.co.kr"),
            "platform_host": str(summary.get("platform_host") or "seoulmna.kr"),
            "placement_count": len(placement_items),
            "checklist_ready": len(placement_items) > 0 and bool(file_map.get("styles")),
            "css_file": file_map.get("styles", ""),
            "combined_file": str((snippets.get("summary") or {}).get("combined_file") or ""),
        },
        "steps": [
            {
                "step": 1,
                "action": "bridge-snippets.css를 .co.kr 테마 또는 공통 배너 주입 경로에 추가한다.",
                "asset": file_map.get("styles", ""),
            },
            {
                "step": 2,
                "action": "placement별 HTML 스니펫을 해당 위치에만 삽입한다.",
                "asset": str((snippets.get("summary") or {}).get("combined_file") or ""),
            },
            {
                "step": 3,
                "action": ".co.kr 페이지 어디에도 계산기 iframe 또는 /_calc 직접 링크를 넣지 않는다.",
                "asset": "",
            },
            {
                "step": 4,
                "action": "모든 CTA 링크가 .kr 서비스 페이지와 UTM 파라미터를 유지하는지 확인한다.",
                "asset": "",
            },
        ],
        "placements": placement_items,
        "validation": {
            "must_not_embed_iframe": True,
            "must_target_platform_host": str(summary.get("platform_host") or "seoulmna.kr"),
            "required_query_keys": ["utm_source", "utm_medium", "utm_campaign", "utm_content"],
        },
        "next_actions": [
            "매물 상세 상단/하단, 전역 네비게이션, 빈 상태 카드에 placement별 스니펫만 삽입한다.",
            "계산기는 .co.kr에서 열지 않고 항상 .kr 서비스 페이지로만 보낸다.",
            "삽입 후 각 CTA가 의도한 .kr URL과 UTM을 유지하는지 브라우저에서 확인한다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# CO Listing Bridge Operator Checklist",
        "",
        f"- listing_host: {summary.get('listing_host') or '(none)'}",
        f"- platform_host: {summary.get('platform_host') or '(none)'}",
        f"- placement_count: {summary.get('placement_count')}",
        f"- checklist_ready: {summary.get('checklist_ready')}",
        f"- css_file: {summary.get('css_file') or '(none)'}",
        "",
        "## Steps",
    ]
    for row in payload.get("steps", []):
        lines.append(f"- [{row.get('step')}] {row.get('action')}")
    lines.extend(["", "## Placements"])
    for row in payload.get("placements", []):
        lines.append(f"- {row.get('placement')}: {row.get('copy')} -> {row.get('target_url')}")
        lines.append(f"  - location_hint: {row.get('location_hint')}")
        lines.append(f"  - snippet_file: {row.get('snippet_file')}")
        lines.append(f"  - validation_hint: {row.get('validation_hint')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the live operator checklist for .co.kr -> .kr bridge insertions.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--snippets", type=Path, default=DEFAULT_SNIPPETS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_co_listing_bridge_operator_checklist(policy_path=args.policy, snippets_path=args.snippets)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("checklist_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
