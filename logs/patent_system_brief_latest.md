# Patent System Brief

## Official Sources
- KIPO AI 발명 심사/기재요건: https://www.kipo.go.kr/ko/kpoContentView.do?menuCd=SCD0201244 (AI 명칭보다 구체적 처리수단, 상세 기재, 재현 가능한 단계가 중요하다는 공식 기준)
- KIPO BM 특허 길라잡이(2025 개정판) 안내: https://www.kipo.go.kr/club/front/menu/common/print.do?clubId=bm&curPage=1&menuId=3&messageId=30232&searchField=&searchQuery= (BM 특허의 최신 심사 경향과 청구항 설계 방향의 공식 기준)
- 특허 명세서/청구범위 작성방법 서식: https://www.law.go.kr/LSW/flDownload.do?bylClsCd=110202&flSeq=117336377&gubun= (실시 가능성과 구체 기재 요건의 직접 근거)

## System Split
- Independent systems: `yangdo`, `permit`
- Shared platform: `tenant_gateway`, `channel_router`, `response_envelope`, `usage_billing`, `activation_gate`

## Track A - 비교거래 정규화 및 공개제어 기반 건설업 면허 양도가 산정
- Scope: 건설업 면허 양도거래의 가격범위 산정과 공개 제어
- System boundary / in: yangdo API, yangdo calculator, duplicate cluster core
- System boundary / out: permit rule catalog, permit typed criteria, shared billing internals
- Core steps:
  - 면허/실적/재무 입력 정규화
  - 유사 비교군 점수화 및 오염 제거
  - 앵커/분위수 기반 범위 산정
  - 신뢰도와 공개수준 제어
  - 중복 매물 군집화 및 가중 제한
- Claim focus:
  - 비교군 오염 제거가 포함된 범위 산정 흐름
  - 입력 프로필 적합도에 따른 유사 매물 추천과 추천 이유 생성
  - 추천 정밀도 라벨과 일치축·비일치축 요약 생성
  - 추천 0건일 때 입력 보강, 시장 브리지, 상담형 상세의 공개 순서를 제어하는 fallback 계약
  - 전기·정보통신·소방 업종군 특수 정밀화
  - 공개 등급에 따른 추천 요약 필드와 상담형 상세 설명 필드 분리
  - 중복 매물 군집화와 cluster-weight 제한
  - 신뢰도에 따른 공개수준 제어
- Avoid in claims:
  - 특정 사이트명/크롤링 방식
  - LLM 설명문 생성
  - UI 문구/상담 폼 세부 표현
- Commercial positioning:
  - 건설정보 업체용 양도가 산정 엔진 공급
  - 파트너에는 range/meta만 제공하고 비교군 원본은 비노출
- Claim draft / independent: 면허/재무 입력을 정규화하고 비교군 오염을 제거한 뒤 양도가 범위를 산정하고 입력 프로필 적합도에 따라 유사 매물을 추천하며 신뢰도 기반 공개제어와 중복 매물 군집화 제한을 포함하는 양도가 산정 방법
- Claim draft / dependents:
  - 면허명 별칭 정규화
  - 복합면허 과대매칭 감점
  - 가중 분위수 또는 강건 통계값 사용
  - 유사 매물 추천 이유, 정밀도 라벨, 일치축·비일치축 요약 생성
  - 공개 등급에 따라 추천 요약 필드와 상담형 상세 설명 필드를 분리
  - cluster-weight 제한
- Evidence:
  - 요청 투영/응답 tier: H:\auto\yangdo_blackbox_api.py:786
  - 유사 매물 추천 코어: H:\auto\core_engine\yangdo_listing_recommender.py:496
  - 추천 정밀도 QA 매트릭스: H:\auto\scripts\generate_yangdo_recommendation_precision_matrix.py:384
  - 추천 다양성 감사: H:\auto\scripts\generate_yangdo_recommendation_diversity_audit.py:407
  - 특수 업종 정밀화 packet: H:\auto\scripts\generate_yangdo_special_sector_packet.py:130
  - 중복 매물 군집화 적용: H:\auto\yangdo_blackbox_api.py
  - 산정 엔진 진입점: H:\auto\yangdo_blackbox_api.py:1175
  - 사용량/과금 적재: H:\auto\yangdo_blackbox_api.py:1094
  - 채널/시스템 차단: H:\auto\yangdo_blackbox_api.py
  - 로컬 계산기 공용 로직: H:\auto\yangdo_calculator.py
  - 중복 매물 코어: H:\auto\core_engine\yangdo_duplicate_cluster.py

## Track B - 출처검증된 등록기준 카탈로그 매핑 및 판정보류 제어 기반 인허가 사전검토
- Scope: 등록기준이 있는 인허가 업종의 사전검토와 증빙 체크리스트 생성
- System boundary / in: permit API, typed criteria evaluator, criteria collection/mapping
- System boundary / out: yangdo estimate logic, shared pricing/billing internals
- Core steps:
  - 객관 출처 규칙카탈로그 적재
  - 업종/서비스코드/별칭 매핑
  - typed criteria 기반 기준항목 판정
  - manual review / coverage gate
  - 증빙 체크리스트와 다음 조치 생성
- Claim focus:
  - 객관 출처 기반 규칙카탈로그 매핑
  - typed criteria와 coverage/manual-review gate 결합
  - 기준항목별 증빙 체크리스트 생성
- Avoid in claims:
  - 단순 체크리스트 UI
  - 특정 업종 하나에만 묶인 표현
  - 서류 파일 저장소 자체
- Commercial positioning:
  - 인허가/신규등록 사전검토 API 공급
  - 업종별 추가 기준은 manual-review gate로 책임성 유지
- Claim draft / independent: 객관 출처 규칙카탈로그와 typed criteria를 이용해 등록기준 항목군을 판정하고 coverage/manual-review gate와 증빙 체크리스트를 출력하는 인허가 사전검토 방법
- Claim draft / dependents:
  - 업종코드/서비스코드/별칭 매핑
  - typed criteria category별 판정
  - manual review gate
  - 증빙 체크리스트 생성
- Evidence:
  - typed criteria evaluator: H:\auto\core_engine\permit_criteria_schema.py:196
  - 규칙 병합 및 typed criteria 연결: H:\auto\permit_diagnosis_calculator.py:521
  - permit API usage 적재: H:\auto\permit_precheck_api.py:572
  - permit 시스템 차단: H:\auto\permit_precheck_api.py:267
  - permit precheck 엔드포인트: H:\auto\permit_precheck_api.py:1342
  - 확장 기준 수집: H:\auto\scripts\collect_permit_extended_criteria.py:390
  - 법령 매핑 파이프라인: H:\auto\core_engine\permit_mapping_pipeline.py:40

## Track P - 독립 시스템을 공유 인프라로 공급하는 멀티테넌트 계산 플랫폼
- Scope: yangdo/permit 독립 시스템을 tenant/channel/billing/activation으로 공급
- System boundary / in: tenant/channel gating, response contract, usage billing, activation flow
- System boundary / out: track A/B 독립 청구항 본체
- Core steps:
  - tenant allowed_systems / feature gate
  - channel exposed_systems / host routing
  - response envelope / tier 분기
  - usage billing / rate / monthly counters
  - template -> scaffold -> validate -> activate -> smoke
- Claim focus:
  - track A/B의 공유 인프라 설명
  - 시스템 분리와 공급 구조의 사업화 근거
- Avoid in claims:
  - track P를 A/B 독립항 본체로 과도하게 확장
- Commercial positioning:
  - 파트너 온보딩/활성화 자동화
  - widget/API 공급의 운영 비용 절감 구조
- Claim draft / independent: 별도 청구항 본체가 아니라 A/B 실시예 및 사업화 구조 설명에 사용
- Claim draft / dependents:
  - tenant/channel system gate
  - response tier
  - activation and smoke rollback
- Evidence:
  - tenant system gate: H:\auto\core_engine\tenant_gateway.py:38
  - channel system gate: H:\auto\core_engine\channel_profiles.py:47
  - 공통 응답 envelope: H:\auto\core_engine\api_response.py:35
  - 공통 요청 contract: H:\auto\core_engine\api_contract.py
  - 파트너 활성화: H:\auto\scripts\activate_partner_tenant.py:170
  - 파트너 scaffold: H:\auto\scripts\scaffold_partner_offering.py:51
  - 서울 widget release: H:\auto\scripts\deploy_seoul_widget_embed_release.py:52

## Track C - Production Resilience (Cross-cutting)
- Scope: A/B/P 전체에 걸친 운영 안정성 인프라
- Not a separate patent — A/B 명세서의 실시예 및 사업화 배경으로 사용
- Core steps:
  - SIGTERM graceful shutdown (3 API 서버)
  - Infrastructure consistency 자동 검증 (7-file synchronization)
  - Production smoke test (9 endpoint checks)
- Evidence:
  - yangdo SIGTERM handler: H:\auto\yangdo_blackbox_api.py:1457
  - permit SIGTERM handler: H:\auto\permit_precheck_api.py:1523
  - consult SIGTERM handler: H:\auto\yangdo_consult_api.py:1075
  - 인프라 일관성 검증: H:\auto\tests\test_deploy_infrastructure.py:21
  - consult smoke test: H:\auto\deploy\smoke_test.py:149

## Claim Strategy
- A와 B는 별개 시스템/별개 특허로 유지
- 플랫폼은 공유 인프라로만 설명하고, 특허 본체는 각 시스템 코어 흐름에 집중
- generic AI가 아니라 입력 정규화/오염 제어/공개 제어/판정보류 제어를 청구항 축으로 사용

## Attorney Handoff
- A/B는 독립 명세서와 독립 청구항으로 유지
- P는 별도 플랫폼 특허보다 A/B 사업화 배경과 실시예로 제한
- 청구항에는 사이트명/크롤링/UI 표현을 넣지 말고 처리 흐름 중심으로 압축
