#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_JSON = ROOT / "logs" / "attorney_handoff_latest.json"
DEFAULT_MD = ROOT / "logs" / "attorney_handoff_latest.md"
LEGACY_JSON = ROOT / "logs" / "patent_system_brief_latest.json"
LEGACY_MD = ROOT / "logs" / "patent_system_brief_latest.md"

from scripts.attorney_handoff_core import OFFICIAL_SOURCES, build_summary, build_track_evidence


def _build_claim_sentence_draft(track_id: str) -> Dict[str, Any]:
    key = str(track_id or "").strip().upper()
    if key == "A":
        return {
            "independent": (
                "건설업 면허 양도거래 대상의 면허명, 면허구성 및 재무정보를 포함하는 대상정보와 복수의 "
                "양도거래 기준정보를 수신하고, 상기 대상정보 및 기준정보에 포함된 이종 표기 면허명을 정규화한 후, "
                "대상정보로부터 생성된 특징 앵커에 부합하지 않는 기준정보를 제외 또는 감가하고, 잔여 기준정보에 "
                "기초하여 양도가 기준값 또는 범위를 산정하며, 상기 대상정보와 기준정보의 적합도에 따라 유사 매물 "
                "후보를 추천하고, 근거밀도 및 분산에 따라 신뢰도를 산출하며, 상기 신뢰도에 따라 가격범위, 추천 "
                "결과 또는 검증필요 상태를 출력하는 컴퓨터 구현 양도가 산정 방법."
            ),
            "dependents": [
                "청구항 1에 있어서, 상기 면허명 정규화는 별칭 사전 및 문자단위 유사도 계산을 조합하여 수행되는 방법.",
                "청구항 1에 있어서, 상기 기준정보의 제외 또는 감가는 복합면허 구성의 불일치 여부를 반영하여 수행되는 방법.",
                "청구항 1에 있어서, 상기 양도가 기준값 또는 범위의 산정은 가중 분위수 또는 강건 통계값을 이용하는 방법.",
                "청구항 1에 있어서, 상기 유사 매물 후보의 추천은 면허 일치도, 실적 규모 적합도, 가격대 적합도 및 연도별 실적 흐름 적합도를 결합한 추천 점수와 추천 사유, 추천 정밀도 라벨 및 일치축·비일치축 요약을 생성하는 방법.",
                "청구항 1에 있어서, 상기 추천 결과는 공개 등급에 따라 가격 범위, 추천 라벨 및 추천 이유를 포함하는 요약 추천 필드와, 추천 정밀도, 일치축, 비일치축 및 주의 신호를 포함하는 상담형 상세 설명 필드로 분리되어 출력되는 방법.",
                "청구항 1에 있어서, 동일한 기초거래로 판정된 복수의 기준정보를 하나의 군집으로 묶고 군집별 최대 가중치를 제한하여 산정에 반영하는 방법.",
            ],
        }
    if key == "B":
        return {
            "independent": (
                "등록기준이 설정된 인허가 업종에 대한 업종 식별정보와 신청인 정보를 수신하고, 객관 출처로 검증된 "
                "규칙카탈로그에서 대응 규칙군을 매핑하며, 상기 규칙군에 포함된 복수의 등록기준 항목군에 대하여 "
                "충족여부 및 부족항목을 산정하고, 규칙군 매핑 신뢰도 또는 카탈로그 커버리지가 기준 미만인 경우 "
                "판정결과를 기준확정 필요 상태로 전환하여 제한 공개하며, 부족항목, 근거 법령 및 후속 조치를 "
                "출력하는 컴퓨터 구현 인허가 사전검토 방법."
            ),
            "dependents": [
                "청구항 1에 있어서, 상기 규칙군 매핑은 업종코드, 서비스코드 및 별칭 정규화를 조합하여 수행되는 방법.",
                "청구항 1에 있어서, 상기 등록기준 항목군은 자본금, 기술인력, 사무실 또는 영업소, 장비 또는 시설, 예치 또는 보증, 자격 또는 경력, 기간요건 중 하나 이상을 포함하는 방법.",
                "청구항 1에 있어서, 하위 법령 또는 별표·별지 문서로부터 추출된 추가 등록기준이 정형화된 기준항목으로 변환되어 상기 산정에 포함되는 방법.",
                "청구항 1에 있어서, 부족항목별로 필요한 증빙서류 유형과 부족사유를 연결한 증빙 체크리스트를 함께 생성하는 방법.",
            ],
        }
    return {
        "independent": "플랫폼 트랙은 독립항 본체가 아니라 A/B 실시예와 사업화 구조 설명으로 제한.",
        "dependents": [
            "tenant/channel system gate",
            "response tier",
            "activation and smoke rollback",
        ],
    }


def build_attorney_handoff() -> Dict[str, Any]:
    brief = {
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(ROOT),
        "official_sources": OFFICIAL_SOURCES,
        "tracks": build_track_evidence(),
        "summary": build_summary(),
    }
    tracks: List[Dict[str, Any]] = []
    for track in brief.get("tracks", []):
        if not isinstance(track, dict):
            continue
        claim_outline = track.get("claim_draft_outline") if isinstance(track.get("claim_draft_outline"), dict) else {}
        claim_sentence_draft = _build_claim_sentence_draft(str(track.get("track_id") or ""))
        systems_in = ((track.get("system_boundary") or {}) if isinstance(track.get("system_boundary"), dict) else {}).get("in_scope", [])
        systems_out = ((track.get("system_boundary") or {}) if isinstance(track.get("system_boundary"), dict) else {}).get("out_of_scope", [])
        tracks.append(
            {
                "track_id": track.get("track_id"),
                "system_id": track.get("system_id"),
                "title": track.get("title"),
                "scope": track.get("scope"),
                "attorney_position": {
                    "in_scope": list(systems_in or []),
                    "out_of_scope": list(systems_out or []),
                    "claim_focus": list(track.get("claim_focus") or []),
                    "avoid_in_claims": list(track.get("avoid_in_claims") or []),
                    "commercial_positioning": list(track.get("commercial_positioning") or []),
                },
                "claim_draft_outline": {
                    "independent": str(claim_outline.get("independent") or "").strip(),
                    "dependents": [str(x or "").strip() for x in (claim_outline.get("dependents") or []) if str(x or "").strip()],
                },
                "claim_sentence_draft": {
                    "independent": str(claim_sentence_draft.get("independent") or "").strip(),
                    "dependents": [str(x or "").strip() for x in (claim_sentence_draft.get("dependents") or []) if str(x or "").strip()],
                },
                "core_steps": list(track.get("core_steps") or []),
                "evidence": list(track.get("evidence") or []),
            }
        )

    summary = brief.get("summary") if isinstance(brief.get("summary"), dict) else {}
    packet = {
        "generated_at": brief.get("generated_at"),
        "root": brief.get("root"),
        "packet_id": "attorney_handoff_latest",
        "purpose": "변리사 전달용 단일 기준 문서",
        "official_sources": list(brief.get("official_sources") or []),
        "executive_summary": {
            "independent_systems": list(summary.get("independent_systems") or []),
            "shared_platform": list(summary.get("shared_platform") or []),
            "claim_strategy": list(summary.get("claim_strategy") or []),
            "attorney_handoff": list(summary.get("attorney_handoff") or []),
            "update_rule": [
                "변리사 전달 관련 내용은 이 attorney_handoff_latest만 기준으로 갱신",
                "A=양도가, B=인허가, P=공유 플랫폼 설명으로 역할 고정",
                "사이트명/크롤링/UI 표현은 청구항 본체에서 배제",
            ],
        },
        "tracks": tracks,
        "delivery_checklist": [
            "A와 B를 독립 출원으로 유지",
            "P는 사업화 구조/실시예로만 제한",
            "독립항은 처리 흐름 중심으로 압축",
            "종속항은 오염 제거, gate, checklist, cluster-weight 제한 중심으로 구성",
            "공식 출처는 KIPO/법령 링크만 우선 제시",
        ],
        "canonical_artifacts": {
            "json": str(DEFAULT_JSON.resolve()),
            "md": str(DEFAULT_MD.resolve()),
        },
        "legacy_references": {
            "patent_system_brief_json": str(LEGACY_JSON.resolve()),
            "patent_system_brief_md": str(LEGACY_MD.resolve()),
        },
    }
    return packet


def _to_markdown(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Attorney Handoff")
    lines.append("")
    lines.append("## Purpose")
    lines.append(f"- {data.get('purpose', '')}")
    lines.append("- 앞으로 변리사 전달 기준은 이 문서 한 개로 고정")
    lines.append("")
    lines.append("## Executive Summary")
    for item in (data.get("executive_summary") or {}).get("claim_strategy", []):
        lines.append(f"- {item}")
    for item in (data.get("executive_summary") or {}).get("attorney_handoff", []):
        lines.append(f"- {item}")
    for item in (data.get("executive_summary") or {}).get("update_rule", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Official Sources")
    for src in data.get("official_sources", []):
        lines.append(f"- {src['label']}: {src['url']} ({src['why']})")
    lines.append("")
    for track in data.get("tracks", []):
        lines.append(f"## Track {track.get('track_id')} - {track.get('title')}")
        lines.append(f"- Scope: {track.get('scope')}")
        position = track.get("attorney_position") if isinstance(track.get("attorney_position"), dict) else {}
        lines.append(f"- In scope: {', '.join(position.get('in_scope', []))}")
        lines.append(f"- Out of scope: {', '.join(position.get('out_of_scope', []))}")
        lines.append("- Claim focus:")
        for item in position.get("claim_focus", []):
            lines.append(f"  - {item}")
        lines.append("- Avoid in claims:")
        for item in position.get("avoid_in_claims", []):
            lines.append(f"  - {item}")
        lines.append("- Commercial positioning:")
        for item in position.get("commercial_positioning", []):
            lines.append(f"  - {item}")
        draft = track.get("claim_draft_outline") if isinstance(track.get("claim_draft_outline"), dict) else {}
        lines.append(f"- Independent claim outline: {draft.get('independent', '')}")
        lines.append("- Dependent claim candidates:")
        for item in draft.get("dependents", []):
            lines.append(f"  - {item}")
        sentence = track.get("claim_sentence_draft") if isinstance(track.get("claim_sentence_draft"), dict) else {}
        lines.append("- Claim sentence draft:")
        lines.append(f"  - Independent: {sentence.get('independent', '')}")
        for item in sentence.get("dependents", []):
            lines.append(f"  - Dependent: {item}")
        lines.append("- Code evidence:")
        for ev in track.get("evidence", []):
            lines.append(f"  - {ev['label']}: {ev['ref']}")
        lines.append("")
    lines.append("## Delivery Checklist")
    for item in data.get("delivery_checklist", []):
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the single canonical attorney handoff packet")
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--md", default=str(DEFAULT_MD))
    args = parser.parse_args()

    data = build_attorney_handoff()
    json_path = Path(str(args.json)).resolve()
    md_path = Path(str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(data), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "json": str(json_path),
        "md": str(md_path),
        "track_count": len(data.get("tracks", [])),
        "packet_id": data.get("packet_id"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
