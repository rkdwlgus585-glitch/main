from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]

OFFICIAL_SOURCES = [
    {
        "label": "KIPO AI 발명 심사/기재요건",
        "url": "https://www.kipo.go.kr/ko/kpoContentView.do?menuCd=SCD0201244",
        "why": "AI 명칭보다 구체적 처리수단, 상세 기재, 재현 가능한 단계가 중요하다는 공식 기준",
    },
    {
        "label": "KIPO BM 특허 길라잡이(2025 개정판) 안내",
        "url": "https://www.kipo.go.kr/club/front/menu/common/print.do?clubId=bm&curPage=1&menuId=3&messageId=30232&searchField=&searchQuery=",
        "why": "BM 특허의 최신 심사 경향과 청구항 설계 방향의 공식 기준",
    },
    {
        "label": "특허 명세서/청구범위 작성방법 서식",
        "url": "https://www.law.go.kr/LSW/flDownload.do?bylClsCd=110202&flSeq=117336377&gubun=",
        "why": "실시 가능성과 구체 기재 요건의 직접 근거",
    },
]

TRACKS = [
    {
        "track_id": "A",
        "system_id": "yangdo",
        "title": "비교거래 정규화 및 공개제어 기반 건설업 면허 양도가 산정",
        "scope": "건설업 면허 양도거래의 가격범위 산정과 공개 제어",
        "system_boundary": {
            "in_scope": ["yangdo API", "yangdo calculator", "duplicate cluster core"],
            "out_of_scope": ["permit rule catalog", "permit typed criteria", "shared billing internals"],
        },
        "core_steps": [
            "면허/실적/재무 입력 정규화",
            "유사 비교군 점수화 및 오염 제거",
            "앵커/분위수 기반 범위 산정",
            "입력 프로필 적합도 기반 유사 매물 추천",
            "신뢰도와 공개수준 제어",
            "중복 매물 군집화 및 가중 제한",
        ],
        "claim_focus": [
            "비교군 오염 제거가 포함된 범위 산정 흐름",
            "입력 프로필 적합도에 따른 유사 매물 추천과 추천 이유 생성",
            "추천 정밀도 라벨과 일치축·비일치축 요약 생성",
            "추천 0건일 때 입력 보강, 시장 브리지, 상담형 상세의 공개 순서를 제어하는 fallback 계약",
            "추천 상위 결과에서 top1 안정성을 유지하면서 가격대·추천축 편중을 완화하는 다양성 제어",
            "전기·정보통신·소방 업종군에서 정산 방식과 재편 유형에 따라 추천 축과 공개정책을 다르게 유지하는 특수 업종 정밀화",
            "공개 등급에 따른 추천 요약 필드와 상담형 상세 설명 필드 분리",
            "중복 매물 군집화와 cluster-weight 제한",
            "신뢰도에 따른 공개수준 제어",
        ],
        "avoid_in_claims": [
            "특정 사이트명/크롤링 방식",
            "LLM 설명문 생성",
            "UI 문구/상담 폼 세부 표현",
            "WordPress/Astra child theme, Gutenberg blueprint, lazy gate UI, .kr 공개 마운트 같은 배포 구현 세부",
        ],
        "commercial_positioning": [
            "건설정보 업체용 양도가 산정 및 유사 매물 추천 엔진 공급",
            "파트너에는 range/meta만 제공하고 비교군 원본은 비노출",
            "표준형 위젯은 가격범위와 추천 요약만, Pro/API는 추천 정밀도와 추천 이유까지 제공",
            "공개 위젯은 safe-summary, 운영자/Pro는 detail-explainable 정책으로 차등 공급",
            "공개 플랫폼은 .kr에서 추천을 해석하고 실제 매물 확인은 별도 매물 사이트 또는 상담형 상세로만 분기",
            "추천 0건 또는 저정밀 상황에서는 입력 보강·시장 확인·상담형 상세의 순서를 계약으로 고정해 오판 리스크를 낮춤",
        ],
        "claim_draft_outline": {
            "independent": "면허/재무 입력을 정규화하고 비교군 오염을 제거한 뒤 양도가 범위를 산정하고 입력 프로필 적합도에 따라 유사 매물을 추천하며 신뢰도 기반 공개제어와 중복 매물 군집화 제한을 포함하는 양도가 산정 방법",
            "dependents": [
                "면허명 별칭 정규화",
                "복합면허 과대매칭 감점",
                "가중 분위수 또는 강건 통계값 사용",
                "유사 매물 추천 이유, 정밀도 라벨, 일치축·비일치축 요약 생성",
                "공개 등급에 따라 추천 요약 필드와 상담형 상세 설명 필드를 분리",
                "cluster-weight 제한",
            ],
        },
        "patterns": [
            {"label": "요청 투영/응답 tier", "file": "yangdo_blackbox_api.py", "pattern": r"def _project_estimate_result\("},
            {"label": "유사 매물 추천 코어", "file": "core_engine/yangdo_listing_recommender.py", "pattern": r"def build_recommendation_bundle\("},
            {"label": "추천 정밀도 QA 매트릭스", "file": "scripts/generate_yangdo_recommendation_precision_matrix.py", "pattern": r"def build_yangdo_recommendation_precision_matrix\("},
            {"label": "추천 다양성 감사", "file": "scripts/generate_yangdo_recommendation_diversity_audit.py", "pattern": r"def build_yangdo_recommendation_diversity_audit\("},
            {"label": "특수 업종 정밀화 packet", "file": "scripts/generate_yangdo_special_sector_packet.py", "pattern": r"def build_yangdo_special_sector_packet\("},
            {"label": "추천 서비스 카피/시장 브리지", "file": "scripts/generate_yangdo_service_copy_packet.py", "pattern": r"def build_yangdo_service_copy_packet\("},
            {"label": "추천 UX/공개등급 계약", "file": "scripts/generate_yangdo_recommendation_ux_packet.py", "pattern": r"def build_yangdo_recommendation_ux_packet\("},
            {"label": "중복 매물 군집화 적용", "file": "yangdo_blackbox_api.py", "pattern": r"collapse_duplicate_neighbors\("},
            {"label": "산정 엔진 진입점", "file": "yangdo_blackbox_api.py", "pattern": r"def estimate\(self, payload"},
            {"label": "사용량/과금 적재", "file": "yangdo_blackbox_api.py", "pattern": r"def insert_estimate_usage\("},
            {"label": "채널/시스템 차단", "file": "yangdo_blackbox_api.py", "pattern": r"def _require_system\("},
            {"label": "로컬 계산기 공용 로직", "file": "yangdo_calculator.py", "pattern": r"collapseDuplicateClusters"},
            {"label": "중복 매물 코어", "file": "core_engine/yangdo_duplicate_cluster.py", "pattern": r"def collapse_duplicate_clusters\("},
        ],
    },
    {
        "track_id": "B",
        "system_id": "permit",
        "title": "출처검증된 등록기준 카탈로그 매핑 및 판정보류 제어 기반 인허가 사전검토",
        "scope": "등록기준이 있는 인허가 업종의 사전검토와 증빙 체크리스트 생성",
        "system_boundary": {
            "in_scope": ["permit API", "typed criteria evaluator", "criteria collection/mapping"],
            "out_of_scope": ["yangdo estimate logic", "shared pricing/billing internals"],
        },
        "core_steps": [
            "객관 출처 규칙카탈로그 적재",
            "업종/서비스코드/별칭 매핑",
            "typed criteria 기반 기준항목 판정",
            "manual review / coverage gate",
            "증빙 체크리스트와 다음 조치 생성",
        ],
        "claim_focus": [
            "객관 출처 기반 규칙카탈로그 매핑",
            "typed criteria와 coverage/manual-review gate 결합",
            "기준항목별 증빙 체크리스트 생성",
        ],
        "avoid_in_claims": [
            "단순 체크리스트 UI",
            "특정 업종 하나에만 묶인 표현",
            "서류 파일 저장소 자체",
            "WordPress/Astra child theme, Gutenberg blueprint, lazy gate UI, .kr 공개 마운트 같은 배포 구현 세부",
        ],
        "commercial_positioning": [
            "인허가/신규등록 사전검토 API 공급",
            "표준 자가진단 -> 상세 체크리스트 -> manual-review assist lane으로 임대형 상품을 계단화",
            "업종별 추가 기준은 manual-review gate로 책임성 유지",
        ],
        "claim_draft_outline": {
            "independent": "객관 출처 규칙카탈로그와 typed criteria를 이용해 등록기준 항목군을 판정하고 coverage/manual-review gate와 증빙 체크리스트를 출력하는 인허가 사전검토 방법",
            "dependents": [
                "업종코드/서비스코드/별칭 매핑",
                "typed criteria category별 판정",
                "manual review gate",
                "증빙 체크리스트 생성",
            ],
        },
        "patterns": [
            {"label": "typed criteria evaluator", "file": "core_engine/permit_criteria_schema.py", "pattern": r"def evaluate_typed_criteria\("},
            {"label": "규칙 병합 및 typed criteria 연결", "file": "permit_diagnosis_calculator.py", "pattern": r"typed_criteria"},
            {"label": "permit API usage 적재", "file": "permit_precheck_api.py", "pattern": r"service='permit_precheck'"},
            {"label": "permit 시스템 차단", "file": "permit_precheck_api.py", "pattern": r"def _require_system\("},
            {"label": "permit precheck 엔드포인트", "file": "permit_precheck_api.py", "pattern": r"/v1/permit/precheck"},
            {"label": "확장 기준 수집", "file": "scripts/collect_permit_extended_criteria.py", "pattern": r"additional_criteria|pending_criteria"},
            {"label": "법령 매핑 파이프라인", "file": "core_engine/permit_mapping_pipeline.py", "pattern": r"def |class "},
        ],
    },
    {
        "track_id": "P",
        "system_id": "platform",
        "title": "독립 시스템을 공유 인프라로 공급하는 멀티테넌트 계산 플랫폼",
        "scope": "yangdo/permit 독립 시스템을 tenant/channel/billing/activation으로 공급",
        "system_boundary": {
            "in_scope": ["tenant/channel gating", "response contract", "usage billing", "activation flow"],
            "out_of_scope": ["track A/B 독립 청구항 본체"],
        },
        "core_steps": [
            "tenant allowed_systems / feature gate",
            "channel exposed_systems / host routing",
            "response envelope / tier 분기",
            "usage billing / rate / monthly counters",
            "template -> scaffold -> validate -> activate -> smoke",
        ],
        "claim_focus": [
            "track A/B의 공유 인프라 설명",
            "시스템 분리와 공급 구조의 사업화 근거",
        ],
        "avoid_in_claims": [
            "track P를 A/B 독립항 본체로 과도하게 확장",
        ],
        "commercial_positioning": [
            "파트너 온보딩/활성화 자동화",
            "widget/API 공급의 운영 비용 절감 구조",
            ".kr 공개 플랫폼과 .co.kr 매물 사이트를 분리하는 공급 구조",
        ],
        "claim_draft_outline": {
            "independent": "별도 청구항 본체가 아니라 A/B 실시예 및 사업화 구조 설명에 사용",
            "dependents": [
                "tenant/channel system gate",
                "response tier",
                "activation and smoke rollback",
            ],
        },
        "patterns": [
            {"label": "tenant system gate", "file": "core_engine/tenant_gateway.py", "pattern": r"def check_system\("},
            {"label": "channel system gate", "file": "core_engine/channel_profiles.py", "pattern": r"def check_system\("},
            {"label": "공통 응답 envelope", "file": "core_engine/api_response.py", "pattern": r"def build_response_envelope\("},
            {"label": "공통 요청 contract", "file": "core_engine/api_contract.py", "pattern": r"def normalize_request_contract\("},
            {"label": "파트너 활성화", "file": "scripts/activate_partner_tenant.py", "pattern": r"def main\("},
            {"label": "파트너 scaffold", "file": "scripts/scaffold_partner_offering.py", "pattern": r"def build_partner_scaffold\("},
            {"label": "서울 widget release", "file": "scripts/deploy_seoul_widget_embed_release.py", "pattern": r"def build_release_plan\("},
        ],
    },
]


def find_line(path: Path, pattern: str) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return 0
    return text.count("\n", 0, match.start()) + 1


def build_ref(file_rel: str, line: int) -> str:
    path = (ROOT / file_rel).resolve()
    return f"{path}:{line}" if line > 0 else str(path)


def build_track_evidence() -> List[Dict[str, object]]:
    tracks_out: List[Dict[str, object]] = []
    for track in TRACKS:
        evidence = []
        for item in track["patterns"]:
            path = (ROOT / str(item["file"])).resolve()
            if not path.exists():
                continue
            line = find_line(path, str(item["pattern"]))
            evidence.append(
                {
                    "label": item["label"],
                    "file": str(path),
                    "line": line,
                    "ref": build_ref(str(item["file"]), line),
                }
            )
        tracks_out.append(
            {
                "track_id": track["track_id"],
                "system_id": track["system_id"],
                "title": track["title"],
                "scope": track["scope"],
                "system_boundary": dict(track.get("system_boundary") or {}),
                "core_steps": list(track["core_steps"]),
                "claim_focus": list(track.get("claim_focus") or []),
                "avoid_in_claims": list(track.get("avoid_in_claims") or []),
                "commercial_positioning": list(track.get("commercial_positioning") or []),
                "claim_draft_outline": dict(track.get("claim_draft_outline") or {}),
                "evidence": evidence,
            }
        )
    return tracks_out


def build_summary() -> Dict[str, object]:
    return {
        "independent_systems": ["yangdo", "permit"],
        "shared_platform": ["tenant_gateway", "channel_router", "response_envelope", "usage_billing", "activation_gate"],
        "claim_strategy": [
            "A와 B는 별개 시스템/별개 특허로 유지",
            "플랫폼은 공유 인프라로만 설명하고, 특허 본체는 각 시스템 코어 흐름에 집중",
            "generic AI가 아니라 입력 정규화/오염 제어/공개 제어/판정보류 제어를 청구항 축으로 사용",
        ],
        "attorney_handoff": [
            "A/B는 독립 명세서와 독립 청구항으로 유지",
            "P는 별도 플랫폼 특허보다 A/B 사업화 배경과 실시예로 제한",
            "청구항에는 사이트명/크롤링/UI 표현을 넣지 말고 처리 흐름 중심으로 압축",
            "WordPress/Astra, lazy gate, reverse proxy mount는 구현 실시예와 운영 구조로만 사용하고 독립항 본체에는 넣지 않음",
        ],
    }
