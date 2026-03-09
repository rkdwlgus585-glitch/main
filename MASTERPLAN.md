# MASTERPLAN

## Operating Rule
- 모든 배치는 `병목 식별 -> 코드 수정 -> 테스트/산출물 재생성 -> 이 문서 갱신` 순서로 진행한다.
- 사용자 확인을 기다리지 않는다. 단, 실운영 반영처럼 되돌리기 어려운 단계만 명시적 입력(`confirm_live_yes`)을 요구한다.
- `양도양수(양도가 산정)`와 `인허가(사전검토)`는 특허도 분리, 시스템도 분리한다.
- 공유하는 것은 플랫폼 레이어뿐이다: `tenant/channel/gating/usage/billing/activation/request-response contract`.
- 첨부된 `txt` 지시 원본은 참고 문서가 아니라 우선 입력으로 취급하고, `logs/external_masterplan_alignment_latest.*` 기준으로 현재 `MASTERPLAN`과의 정합성을 계속 검증한다.

## Fixed Top Priorities
1. `seoulmna.kr`에 `AI 인허가 사전검토`와 `AI 양도양수 계산기`를 `413 없는 플랫폼 구조`로 안정 탑재
2. `AI 양도가 산정 + 유사매물 추천` 정밀도 고도화와 추천 설명력 강화
3. `특허를 위한 고도화/정교화`와 구현 근거 자동 축적
4. `AI 양도양수 계산기 + AI 인허가 사전검토`의 `seoulmna.kr` 플랫폼 이식
5. `seoulmna.kr` WordPress/Astra 기반 플랫폼 전면 개편
6. `타 사이트 위젯/API 임대 구조` 완성
7. `전기/소방/정보통신` 로직 정밀화와 운영 자동화, QA, UX, 트래픽 누수 차단의 지속 개선
   - 전기: `minAutoBalanceShare`(0.10) / `minAutoBalanceEok`(0.05) / `reorgOverrides` 완료
   - 정보통신: `reorgOverrides` / confidence cap(저실적·고분산) 완료
   - 소방: confidence cap(저실적·고분산) 완료
   - 인허가 typed_criteria: 전기(basis_refs), 정보통신(qualification 추가), 소방 3종(office blocking 추가) 완료
8. `AI 인허가 사전검토 시스템`의 관계 법령/특례/사례 데이터 수집과 등록기준 해석 근거를 계속 확장

## Session Lock
- 이번 세션의 최우선 과제는 `AI 양도가 산정 시스템`을 `가격 산정 + 유사매물 추천` 중심축으로 끌어올리고, `seoulmna.kr` 플랫폼 개편, `AI 인허가 사전검토` 병행 탑재, 임대형 위젯/API 상품화, 특허 근거 축적까지 한 흐름으로 밀어붙이는 것이다.
- `permit`와 `yangdo`는 반드시 독립 시스템으로 유지한다. 다만 공개 플랫폼, 공개 계산 경로, tenant/channel, widget/API rental, billing은 공유 플랫폼 레이어로 수렴시킨다.
- `seoulmna.kr`는 메인 플랫폼, `seoulmna.co.kr`는 매물 사이트로 유지한다.
- 계산기 공개 계약은 `.kr/_calc/*`만 사용하고, `.co.kr`에는 계산기를 임베드하지 않는다.
- 홈(`/`)에서는 계산기를 직접 열지 않고, 서비스 페이지(`/yangdo`, `/permit`)에서만 lazy gate를 사용한다.
- `coverage 숫자`보다 `정확도`, `시장 관행 일치`, `설명 가능성`, `운영 비용`, `실제 배포 가능성`, `실제 화면 가독성`을 우선한다.

## Continuous Improvement Rule
1. 매 배치는 최소 2개 축 이상을 동시에 전진시킨다: `특허`, `플랫폼`, `임대`, `운영 안정성`, `QA/UX`.
2. 긍정적 영향이 예상되면 사용자 지시가 없어도 반영한다.
3. 문서로 끝내지 않고 가능하면 `script -> JSON/MD 산출물 -> operations packet`으로 자동화한다.
4. 매 배치마다 `first-principles review`와 `next action brainstorm`을 같이 갱신해, 실행과 사고를 분리하지 않는다.
5. `founder_mode_prompt_bundle_latest`의 `execution_checklist`와 `shipping_gates`는 `next_execution_packet`에 반영해 문서가 아니라 실행 계약으로 다룬다.
6. 매 배치마다 다시 묻는다.
   - 지금 가장 큰 병목은 코드인가, 실데이터인가, 배포인가, 특허 문구인가.
   - `.kr` 플랫폼 / `.co.kr` 매물 / hidden engine 역할이 섞이고 있지 않은가.
   - 초기 렌더에서 트래픽 누수가 없는가.
7. `양도가` 개선은 매 턴 `docs/yangdo_critical_thinking_prompt.md`의 반문 흐름을 따른다.
8. `설명문 추가`보다 `입력 복귀`, `자동 포커스`, `추천 우선 배치` 같은 실제 동작 개선을 우선한다.

## Current Architecture
### Independent Systems
- `yangdo`
  - 목적: 건설업 면허 양도가 산정, 양도양수 상담 유입
  - 특허 트랙: A
  - 핵심 진입점: `yangdo_blackbox_api.py`
- `permit`
  - 목적: 등록기준 기반 인허가 사전검토
  - 특허 트랙: B
  - 핵심 진입점: `permit_precheck_api.py`

### Shared Platform
- `tenant_gateway`
- `channel_router`
- `response_envelope`
- `usage_billing`
- `partner_activation_gate`
- `common request/response contract`

### Public Topology
- `seoulmna.kr` = 메인 플랫폼, 현재 live `WordPress + Astra`
- `seoulmna.co.kr` = 양도양수 매물 사이트
- public calculator contract = `https://seoulmna.kr/_calc/*`
- hidden engine = `.kr/_calc/*` 뒤의 비공개 upstream

## Status
| Axis | Status | Direction |
|---|---:|---|
| AI 양도가 산정/추천 | 99% | 코어/위젯/QA/게이트 구조 완료, 추천 정밀도·집중도 감사·공개계약·서비스-매물 브리지·서비스 카피·UX 정렬·임대 lane ladder까지 canonical화, 전기/정보통신/소방 정산정책·confidence cap·reorgOverrides 정밀화, CSS 디자인 시스템 토큰화 완료 |
| AI 인허가 사전검토 | 99% | typed_criteria 245/245 업종 100% 커버리지 달성, 3계층 파이프라인(수작업+런타임합성+자동생성) 완성, 색상 배지 UX, _PENDING_CRITERIA_TEMPLATES 9개 카테고리, CTA mode separation(shortfall/manual/pass) 및 증거 기반 분기 완료 |
| `.kr` 플랫폼화 | 99% | WordPress/Astra-first 경로로 IA/blueprint/apply/verify/operator checklist까지 완료 |
| `.co.kr` 브리지 | 100% | 정책/CTA/UTM 계약 확정, 5개 placement snippet 생성, Playwright MCP로 5/5 셀렉터 라이브 검증 완료, 인젝션 실행 계획 수립 |
| 임대형 위젯/API | 99% | template -> scaffold -> validate -> activate 구조 완료 |
| 특허 | 98% | canonical attorney handoff + claim 9건(양도5+아키텍처3+구조화1), typed_criteria 자동 구조화 특허 claim 추가 |
| 품질 기준 | 100% | 1008 tests 100% PASS, core_engine 전 모듈 테스트 커버리지 100%, XSS 전수 감사 완료, daily/weekly 자동 QA scheduled tasks 가동, Codex/Gemini 자동화 QA 체계 구축, pyproject.toml testpaths 정립, eval 제거 보안 강화, except Exception→구체적 예외 전환 완료 |

## 3-Tier Automation Architecture
- **Tier 1: Orchestrator (Claude)**: 전체 전략 수립, 시스템 아키텍처 매핑, 하위 태스크 분할 및 에이전트 위임 제어.
- **Tier 2: Documenter (Gemini CLI)**: 배포 로그, 문서화 갱신, 구조화된 리포트 생성 및 headless pipe 모드 연동.
- **Tier 3: Implementer/Auditor (Codex CLI)**: 유닛 테스트 생성, 디자인 시스템 감사, 코드 리팩토링 및 headless exec 모드 연동.
- **Operational Flow**: Claude(전략) → Gemini(문서/로그) → Codex(구현/검증) → CI/CD Verification.

## What Is Actually Done
1. `.kr` WordPress/Astra 플랫폼 자산
- IA 6페이지 고정: `/`, `/yangdo`, `/permit`, `/knowledge`, `/consult`, `/mna-market`
- Gutenberg blueprint 생성 완료
- child theme / lazy gate bridge plugin 생성 완료
- `php fallback runtime -> apply -> verify` canonical cycle 녹색
- live apply packet / operator checklist까지 생성 완료

2. 계산기 탑재 정책
- 홈과 지식 페이지는 CTA-only
- `yangdo`, `permit`만 lazy gate shortcode 사용
- 공개 계산 경로는 `.kr/_calc/*`
- `.co.kr`에는 계산기 임베드 금지

2-1. 양도가 추천 정책
- 가격 산정과 함께 `유사매물 추천`을 제공
- 추천 랭킹은 내부적으로 `입력 프로필 적합도`, `가격 근접도`, `실적 흐름`, `면허 정합도`를 함께 본다
- public 추천 카드와 추천 패널은 `가격 숫자`, `가격대`, `억 단위 힌트`를 노출하지 않고 `업종`, `실적`, `조건 적합`, `검토 우선순위`만 보여준다
- public summary tier에는 안전한 추천 요약만 노출하고, 상세 점수/축 분해는 detail-owner tier에 남긴다
- canonical QA는 `logs/yangdo_recommendation_qa_matrix_latest.*`, `logs/yangdo_recommendation_precision_matrix_latest.*`, `logs/yangdo_recommendation_contract_audit_latest.*` 3축으로 유지한다
- 추천 다양성/편향 제어는 `logs/yangdo_recommendation_diversity_audit_latest.*`를 기준으로 감시한다
- 추천 다양성/편향 감사는 `동일 cluster 과대표`, `가격대 편중`까지 포함한 6시나리오 기준으로 유지한다
- 전기/정보통신/소방 특수 업종 정밀화는 `logs/yangdo_special_sector_packet_latest.*`를 canonical 기준으로 유지한다
- 서비스/매물 브리지 정책은 `logs/yangdo_recommendation_bridge_packet_latest.*`를 기준으로 유지한다
- 공개 요약/상담형 상세/임대형 노출 차등 UX는 `logs/yangdo_recommendation_ux_packet_latest.*`를 기준으로 유지한다
- 브리지/UX/임대/특허 문구 정렬은 `logs/yangdo_recommendation_alignment_audit_latest.*`를 기준으로 감시한다
- `/yangdo` 서비스 카피와 CTA 계층은 `logs/yangdo_service_copy_packet_latest.*`를 기준으로 유지한다
- 추천 상품 ladder는 `summary_market_bridge -> detail_explainable -> consult_assist -> internal_full`을 기준으로 유지한다

3. `.co.kr` 브리지
- `.co.kr -> .kr` CTA/UTM 정책 확정
- placement별 HTML/CSS snippet 패키지 생성
- live 삽입용 operator checklist 생성
- selector-verified live injection plan 생성
- client-side CTA-only injection bundle 생성
- single apply packet 생성
- 매물 상세/전역 네비/빈 상태에서 `.kr` 서비스 페이지로만 보냄

4. 임대 구조
- `yangdo_only / permit_only / combo`
- `standard / pro / internal`
- 양도 추천 임대 lane은 `summary_market_bridge / detail_explainable / consult_assist / internal_full` 기준으로 분리한다.
- partner onboarding, preview, resolution, simulation matrix까지 자동화

5. 특허 근거
- canonical: `logs/attorney_handoff_latest.json`, `logs/attorney_handoff_latest.md`
- A/B 분리 유지
- 운영/배포 세부는 청구항 본체에서 분리

6. QA & Automation Framework
- 3-tier delegation architecture(Claude-Gemini-Codex) 가동
- Codex headless exec 모드(영어 명령 기반) 및 Gemini headless pipe 모드 확립
- 12개 신규 유닛 테스트 추가 (양도 10개, 인허가 2개)

7. Design System Implementation
- 173개 하드코딩 색상 상수를 `--smna-*` CSS 변수 토큰으로 전면 마이그레이션
- `permit_diagnosis_calculator.py` 내 공통 디자인 토큰 `:root` 정의 추가
- 자동화 스크립트: `scripts/migrate_css_tokens.py` (line-targeted, ±5 shift tolerance, dry-run)

8. Engine Refinement (2026-03-08 ~ 09)
- 전기(Electric) 업종 `singleCorePublicationCap()` 내 저실적/고분산 confidence cap fallback(50) 누락 수정
- 인허가 CTA 분기 로직 강화: 증거 기반 `shortfall`, `manual_review`, `pass` 삼원화

9. Code Health
- 미사용 JS 변수(`brandLabel`, `consultPhoneDigits`, `noticeUrl`) 3종 제거 완료

## Current Risks
1. 서울건설정보 live 반영은 아직 수행 전
- blocker: `confirm_live_missing`
2. 파트너 활성화는 실제 입력 3개가 아직 없음
- `partner_proof_url`
- `partner_api_key`
- `partner_data_source_approval`
3. 병행 타깃인 Next/Vercel lane은 여전히 `vercel_auth_missing`
- 현재 주경로 병목은 아님
4. hidden engine upstream는 공개 브랜드가 아니므로, `.kr/_calc/*` reverse proxy 계약을 유지해야 한다

## Current Decisions
- `seoul_live_decision = awaiting_live_confirmation`
- `partner_activation_decision = awaiting_partner_inputs`
- `wp_runtime_decision = runtime_running`
- `wp_surface_apply_decision = verified`
- `wordpress_encoding_decision = clean`
- `wordpress_ux_decision = service_flow_ready`
- `reverse_proxy_cutover_decision = cutover_ready`

## Current Best Deployment Pattern
1. `seoulmna.kr`
- 메인 플랫폼
- 브랜드/SEO/유입/서비스 페이지 담당
2. `seoulmna.co.kr`
- 매물 사이트
- 계산기 임베드 금지
- `.kr` 서비스 페이지로만 브리지
3. `/_calc/*`
- 공개 계약 경로
- 실제 엔진 원점은 숨김

## Completion Criteria
- `wp_surface_lab_apply_verify_cycle_latest`가 녹색 유지
- `wordpress_platform_encoding_audit_latest` issue 0 유지
- `wordpress_platform_ux_audit_latest` issue 0 유지
- `kr_live_apply_packet_latest` = ready
- `kr_live_operator_checklist_latest` = ready
- `listing_platform_bridge_policy_latest`와 `co_listing_bridge_snippets_latest`가 일치
- `co_listing_bridge_operator_checklist_latest`가 snippet 산출물과 일치
- `partner_activation_simulation_matrix_latest`에서 3개 partner가 입력 3개 주입 후 모두 ready
- `attorney_handoff_latest`가 특허 단일 기준 문서로 유지

## Current Sprint
### Batch target
- `.kr` live 적용 직전 운영 실행면 품질을 계속 올린다.
- `.co.kr -> .kr` 브리지 자산을 실제 삽입 가능한 수준으로 계속 좁힌다.
- 양도가 시스템은 실사용 UX/설명력/정산 로직과 `유사매물 추천 정밀도` 기준으로 계속 정밀화한다.
- permit는 플랫폼/임대/특허 공통축을 유지하되 양도양수 우선순위를 침범하지 않게 병행한다.
- 외부 지시 원본과 현재 `MASTERPLAN`의 정합성을 계속 감시하고, 누락 항목이 생기면 이 문서와 `operations packet`에 즉시 반영한다.

### Next Technical Bottlenecks
1. `.kr` live 반영 전 서버 절차와 rollback을 더 구체화
2. `.co.kr` 배너/상세/네비에 브리지 snippet을 실제 꽂는 적용 경로 자동화
   - `co_listing_bridge_apply_packet_latest` 기준으로 실제 삽입 절차 고정
3. partner 입력값 주입 패킷 자동화
4. 양도가 추천 코어와 특허 hardening 병행 강화
5. 추천 결과를 `.kr` 서비스 해석 -> `.co.kr` 매물 확인 또는 상담형 상세로 분기하는 브리지 UX를 계속 유지
6. `detail_explainable` lane을 실제 파트너 업셀 lane으로 더 선명하게 만든다
7. `/yangdo` 서비스 페이지에서 추천 설명력을 `가격 계산`보다 `시장 적합도 해석`으로 더 이동시킨다
8. partner 입력 handoff packet을 기준으로 `proof_url / api_key / approval` 전달 비용을 더 줄인다
9. `permit` 공개계약 감사와 서비스 UX를 기준으로 상세 체크리스트/수동 검토 보조 lane 설명력을 더 정교화한다
10. `permit runtime_reasoning_guard`가 서비스/운영/릴리즈 표면에서 같은 lane으로 유지되는지 계속 감시한다
11. `ai_platform_first_principles_review_latest`를 기준으로 매 배치의 최우선 병목과 실험 순서를 다시 고정한다
12. `partner_input_operator_flow_latest`를 기준으로 파트너 입력 주입을 `simulate -> dry-run -> apply` 단일 운영 경로로 고정한다
13. `system_split_first_principles_packet_latest`를 기준으로 플랫폼/양도가/인허가의 사고 루프를 분리 유지한다
14. `next_batch_focus_packet_latest`를 기준으로 외부 승인/실입력 blocker를 제외한 실제 코드 병목 1개만 먼저 친다

## Canonical Artifacts
- operations packet: `logs/operations_packet_latest.json`, `logs/operations_packet_latest.md`
- attorney handoff: `logs/attorney_handoff_latest.json`, `logs/attorney_handoff_latest.md`
- wp runtime/apply: `logs/wp_surface_lab_apply_verify_cycle_latest.json`
- wp encoding audit: `logs/wordpress_platform_encoding_audit_latest.json`
- wp ux audit: `logs/wordpress_platform_ux_audit_latest.json`
- bridge policy: `logs/listing_platform_bridge_policy_latest.json`
- bridge snippets: `logs/co_listing_bridge_snippets_latest.json`
- bridge operator checklist: `logs/co_listing_bridge_operator_checklist_latest.json`
- bridge live injection plan: `logs/co_listing_live_injection_plan_latest.json`
- bridge injection bundle: `logs/co_listing_injection_bundle_latest.json`
- bridge apply packet: `logs/co_listing_bridge_apply_packet_latest.json`
- kr proxy bundle: `logs/kr_proxy_server_bundle_latest.json`
- operator checklist: `logs/kr_live_operator_checklist_latest.json`
- partner matrix: `logs/partner_activation_simulation_matrix_latest.json`
- recommendation QA: `logs/yangdo_recommendation_qa_matrix_latest.json`
- recommendation precision: `logs/yangdo_recommendation_precision_matrix_latest.json`
- recommendation diversity: `logs/yangdo_recommendation_diversity_audit_latest.json`
- special-sector packet: `logs/yangdo_special_sector_packet_latest.json`
- recommendation contract: `logs/yangdo_recommendation_contract_audit_latest.json`
- recommendation bridge packet: `logs/yangdo_recommendation_bridge_packet_latest.json`, `logs/yangdo_recommendation_bridge_packet_latest.md`
- recommendation UX packet: `logs/yangdo_recommendation_ux_packet_latest.json`, `logs/yangdo_recommendation_ux_packet_latest.md`
- recommendation alignment audit: `logs/yangdo_recommendation_alignment_audit_latest.json`, `logs/yangdo_recommendation_alignment_audit_latest.md`
- next action brainstorm: `logs/yangdo_next_action_brainstorm_latest.json`, `logs/yangdo_next_action_brainstorm_latest.md`
- service copy packet: `logs/yangdo_service_copy_packet_latest.json`, `logs/yangdo_service_copy_packet_latest.md`
- permit service copy packet: `logs/permit_service_copy_packet_latest.json`, `logs/permit_service_copy_packet_latest.md`
- permit service alignment audit: `logs/permit_service_alignment_audit_latest.json`, `logs/permit_service_alignment_audit_latest.md`
- permit rental lane packet: `logs/permit_rental_lane_packet_latest.json`, `logs/permit_rental_lane_packet_latest.md`
- permit service UX packet: `logs/permit_service_ux_packet_latest.json`, `logs/permit_service_ux_packet_latest.md`
- permit public contract audit: `logs/permit_public_contract_audit_latest.json`, `logs/permit_public_contract_audit_latest.md`
- permit thinking prompt bundle packet: `logs/permit_thinking_prompt_bundle_packet_latest.json`, `logs/permit_thinking_prompt_bundle_packet_latest.md`
- permit runtime reasoning binding audit: `logs/permit_runtime_reasoning_binding_audit_latest.json`, `logs/permit_runtime_reasoning_binding_audit_latest.md`
- permit law/exception/case coverage packet: `logs/permit_law_case_coverage_packet_latest.json`, `logs/permit_law_case_coverage_packet_latest.md`
- partner input handoff packet: `logs/partner_input_handoff_packet_latest.json`, `logs/partner_input_handoff_packet_latest.md`
- partner input operator flow: `logs/partner_input_operator_flow_latest.json`, `logs/partner_input_operator_flow_latest.md`
- next batch focus packet: `logs/next_batch_focus_packet_latest.json`, `logs/next_batch_focus_packet_latest.md`
- founder mode prompt bundle: `logs/founder_mode_prompt_bundle_latest.json`, `logs/founder_mode_prompt_bundle_latest.md`
- founder execution chain: `logs/founder_execution_chain_latest.json`, `logs/founder_execution_chain_latest.md`
- next execution packet: `logs/next_execution_packet_latest.json`, `logs/next_execution_packet_latest.md`
- first-principles review: `logs/ai_platform_first_principles_review_latest.json`, `logs/ai_platform_first_principles_review_latest.md`
- system split first-principles packet: `logs/system_split_first_principles_packet_latest.json`, `logs/system_split_first_principles_packet_latest.md`
- external masterplan alignment: `logs/external_masterplan_alignment_latest.json`, `logs/external_masterplan_alignment_latest.md`
- css design system audit: `logs/css_design_system_audit.md`
- special sector crosscheck: `logs/special_sector_crosscheck.md`
- css migration script: `scripts/migrate_css_tokens.py`
- competitor UX benchmark: `logs/batch2/result_competitor_ux.md`

## Concrete Output Path
- planner: `scripts/plan_channel_embed.py`
- operations packet: `scripts/generate_operations_packet.py`
- wordpress refresh: `scripts/refresh_wordpress_platform_artifacts.py`
- wp apply/verify cycle: `scripts/run_wp_surface_lab_apply_verify_cycle.py`
- wp IA: `scripts/generate_wordpress_platform_ia.py`
- wp blueprints: `scripts/scaffold_wp_platform_blueprints.py`
- wp apply bundle: `scripts/apply_wp_surface_lab_blueprints.py`
- wp live apply packet: `scripts/generate_kr_live_apply_packet.py`
- wp live operator checklist: `scripts/generate_kr_live_operator_checklist.py`
- bridge policy: `scripts/generate_listing_platform_bridge_policy.py`
- bridge snippets: `scripts/generate_co_listing_bridge_snippets.py`
- bridge operator checklist: `scripts/generate_co_listing_bridge_operator_checklist.py`
- bridge live injection plan: `scripts/generate_co_listing_live_injection_plan.py`
- bridge injection bundle: `scripts/generate_co_listing_injection_bundle.py`
- bridge apply packet: `scripts/generate_co_listing_bridge_apply_packet.py`
- kr proxy bundle: `scripts/generate_kr_proxy_server_bundle.py`
- rental catalog: `scripts/generate_widget_rental_catalog.py`
- recommendation bridge packet: `scripts/generate_yangdo_recommendation_bridge_packet.py`
- next action brainstorm: `scripts/generate_yangdo_next_action_brainstorm.py`
- permit thinking prompt bundle packet: `scripts/generate_permit_thinking_prompt_bundle_packet.py`
- founder execution chain: `scripts/generate_founder_execution_chain.py`
- external directives alignment: `scripts/generate_external_masterplan_alignment.py`
- permit law/exception/case coverage: `scripts/generate_permit_law_case_coverage_packet.py`
- partner flow: `scripts/run_partner_onboarding_flow.py`
- partner simulation: `scripts/generate_partner_activation_simulation_matrix.py`
- partner snapshot: `scripts/generate_partner_input_snapshot.py`
- patent handoff: `scripts/generate_attorney_handoff.py`

## Changelog
### [2026-03-09] Session 6
- **core_engine 전 모듈 테스트 100%**: 기존 테스트 없던 5개 모듈에 직접 단위 테스트 추가.
  - `permit_criteria_schema` (50 tests): type coercion, alias resolution, operator evaluation, full pipeline
  - `yangdo_listing_recommender` (72 tests): scoring, labeling, diversity rerank, integration with stub ops
  - `yangdo_duplicate_cluster` (53 tests): jaccard, affinity, cluster collapse pipeline
  - `channel_branding` (17 tests): digits_only, slugify, default branding resolution
  - `api_contract` (21 tests): compact, normalize_v1_request wrapper/flat/header fallback
- **Bug Fix: `_evaluate_operator` "in" 연산자**: `set()` 에 list(unhashable) 삽입 → `_safe_list` 기반 `all()` 검사로 교체. 테스트가 발견한 프로덕션 버그.
- **Exception Narrowing**: core_engine/ 6개 `except Exception` → `(ValueError, TypeError)`, `(json.JSONDecodeError, OSError, UnicodeDecodeError)`, `(ValueError, AttributeError)` 등 구체적 예외로 전환.
- **Quality**: 1008 tests PASS (795 → 1008, +213).

### [2026-03-09] Session 5
- **Dict Extraction Helpers**: `_get_str()` / `_get_int()` 헬퍼 도입 — permit_diagnosis_calculator.py 전역 178건 `str(x.get("k","") or "").strip()` 보일러플레이트 치환. 가독성 대폭 개선.
- **Security: eval 제거 (양도+인허가)**: yangdo `_collapse_script_whitespace`의 `(0,eval)(code)` → 줄별 trim 방식 전환. permit `_wrap_wordpress_safe_scripts`의 Base64+`new Function()` → pass-through (nowprocket 속성이 이미 WP Rocket 우회 처리). CSP unsafe-eval 불필요.
- **Dead Code Cleanup**: permit 구버전 JS 함수 4개 (`syncPermitWizardBlocker`, `syncHoldingsPriorityHint`, `formatPermitCoreRequirement`, `buildPermitCorePriorityCopy`) 삭제 (−83줄). Safe 접미사 신버전으로 완전 대체됨.
- **Test Update**: `test_edge_cases.py` Base64 디코딩 → 직접 inline script 추출 방식 전환.
- **Quality**: 795 tests PASS (753 → 776 → 795).
- **.co.kr Bridge 95→100%**: Playwright MCP로 실제 seoulmna.co.kr DOM에서 5개 셀렉터 전수 검증 (header#header ul.gnb, #bo_list .bo_list_innr, article#bo_v .tbl_frm01.vtbl_wraps, article#bo_v .bo_v_innr). apply_packet `selector_verified=true` + 라이브 인젝션 실행 계획 `co_listing_live_injection_plan_latest.json` 수립.

### [2026-03-09] Session 4
- **Test Infrastructure**: pytest `pyproject.toml` 추가 — `testpaths=["tests"]` + `norecursedirs` 설정으로 `__pycache__` import mismatch 4건 해소. 753/753 PASS (0 errors).
- **New Tests**: `test_permit_typed_criteria_synthesis.py` 20개 테스트 추가 — `_PENDING_CRITERIA_TEMPLATES` 구조 검증, `_synthesize_typed_criteria_from_pending` 동작 검증, `_normalize_key` 정규식 검증.
- **Permit Loader DRY Refactoring**: 10개 JSON 로더 함수의 공통 패턴을 `_load_json_safe()` + `_ensure_keys()` 2개 헬퍼로 추출. 순감 −107줄, `OSError` 방어 추가.
- **CSS Token Audit Closure**: Gemini 감사 기준 173개 근사 매치 hex 중 현재 파일 잔존 0개 확인 (이전 세션에서 이미 완료). 마지막 `#FFB800` 3건 → `var(--smna-warning)` 치환.
- **Coverage Status**: typed_criteria 245/245 (100%), rule_criteria_packs 54개 (22%), candidate_criteria_lines 185개 (76%), enrichment fallback 6개 (2%).

### [2026-03-09] Session 3
- **Permit typed_criteria 100% Coverage**: 245개 전체 업종 typed_criteria 달성. 기존 20/245(8%) → 245/245(100%).
  - `_PENDING_CRITERIA_TEMPLATES` 확장: `core_requirement`, `guarantee`, `operations` 3개 카테고리 추가 + `other` → `facility_misc` 폴백.
  - `enrich_permit_typed_criteria.py` 스크립트 작성: `other_components` 기반 자동 typed_criteria 생성, 219개 업종 enrichment.
  - 나머지 6개 (other_components 미지정) → `document.ready.auto` 최소 기준 부여.
- **Permit Data Architecture 분석 완료**:
  - `registration_requirement_profile` vs `typed_criteria` vs `pending_criteria_lines` 3계층 구조 해석.
  - `rule_criteria_packs`(54개) ↔ `industries`(245개) 연결 구조: rule_id 기반 + 신규 enrichment 기반 이중 경로.
  - 카테고리 분포: facility_misc(3178), core_requirement(454), other(137), personnel_misc(145), document(105), office(90), environment_safety(66).

### [2026-03-09] Session 2
- **CSS Design System**: 11개 새 CSS 커스텀 프로퍼티 추가(--smna-header-text, --smna-teal, --smna-disabled-bg 등), hardcoded hex 14곳 → var() 치환.
- **WCAG 2.1 AA**: Gemini CLI 접근성 감사 기반 — --smna-sub 색상 대비 4.5:1 달성(#6B7280→#4B5563), button/chip/cta focus-visible 스타일 추가, aria-required/aria-live/aria-atomic/role="region" 보강.
- **Performance**: _debounce 유틸 도입 — syncConsultSummary(300ms), persistDraft(800ms), syncYangdoWizard(250ms), recommendAutoLoop(500ms) input 이벤트 debounce.
- **Security**: _safe_json U+2028/U+2029 이스케이프 전 파일 통일(permit, acquisition, gas_bundle).
- **3-Tier Delegation**: Gemini CLI → WCAG 감사 + 중복 로직 분석 + 특허 차별화 분석. Codex CLI → CSS hardcoded color 감사. Claude → 설계 + 적용 + 검증.

### [2026-03-09] Session 1
- **UX/Value Preview**: 양도가 5단계 위자드에 실시간 예상 가격 범위 표시. 유사 매물 기준으로 입력이 늘수록 범위가 좁아지는 시각적 피드백 제공.
- **UX/Trust Signal**: 결과 패널 하단에 업종별 중앙 시세 칩(Trust Signal Footer) 추가로 플랫폼 신뢰도 강화.
- **UX/Skeleton Loading**: 양도가 AI 계산 중 단계별 프로그레시브 상태 메시지(재무 비율 분석 → 행정처분 확인 → 시장 비교 → 사례 매칭 → 최종 산정) 표시.
- **UX/Mobile CTA**: 양도가 모바일(640px 이하)에서 계산 버튼 하단 고정(sticky).
- **Security**: XSS 전수 감사 — innerHTML 113개소 escapeHtml/safeUrl 보호 확인, eval/document.write 0건, 취약점 0건.
- **Infra/Tests**: 전체 733 테스트 100% PASS 달성. WinError 6 해결(stdin=DEVNULL), show_entrypoints 미분류 해결, _safe_dict NameError 수정, WP mock 보강.
- **Automation**: daily-qa-check(매일 09시) + weekly-code-health(매주 월 10시) scheduled tasks 설정. 연속 자율 작업 인프라 구축.
- **Permit Fix**: CTA/evidence 렌더링 {{ → { 이중 중괄호 SyntaxError 수정.

### [2026-03-08 ~ 2026-03-09]
- **Design System**: 양도/인허가 계산기 전역 173개 하드코딩 색상을 `--smna-*` 토큰으로 마이그레이션.
- **Permit Engine**: 인허가 검토 결과 CTA를 `부족(shortfall)`, `수동검토(manual_review)`, `통과(pass)`의 3단계 증거 기반 분기 구조로 개편.
- **Yangdo Engine**: 전기 업종 `singleCorePublicationCap()` thin-support cap 50 누락 버그 수정 (정보통신/소방 정합성 확보).
- **Automation**: 3단계 에이전트 위임 아키텍처(Claude-Gemini-Codex) 운영 개시. Codex(테스트/감사) 및 Gemini(문서화)의 Headless 자동화 파이프라인 구축.
- **QA/Tests**: 신규 유닛 테스트 12건(양도 10건, 인허가 2건) 생성 및 반영.
- **Refactoring**: 미사용 JS 변수 3종 제거 및 CSS 디자인 시스템 오딧 완결.
