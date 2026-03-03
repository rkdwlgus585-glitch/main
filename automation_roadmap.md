# Automation Roadmap (행정사사무소하랑 / 서울건설정보)

> 운영용 최신 실행안 기준 문서: execution_roadmap_realistic.md
>  
> 사전 검증/시뮬레이션: py -3 scripts/execute_roadmap_simulation.py --strict
>  
> 실행 프로필 계획/적용: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/apply_execution_profile.ps1 [-Apply]
## North Star
- 검색 상위 노출 + 상담 전환율 동시 개선
- 반복 업무 자동화로 대표 집중 업무(상담/클로징/의사결정)에 시간 재배분
- 운영 장애(절전/오프라인/인증만료)에도 끊기지 않는 파이프라인 구축

## Current Status (2026-02-22)
1. (DONE) `all.py` 수집 -> 구글시트 저장
2. (DONE) `all.py`에 seoulmna.co.kr `mna` 게시판 업로드 파이프라인 추가
3. (DONE) 업로드 중복 방지 상태파일(`all_upload_state.json`) 적용
4. (DONE) UTF-8/종료 처리 안정화(`_safe_quit` 재귀 버그 제거)

## Priority Backlog (Impact x Feasibility)

### P0. 수익 직결 (즉시)
1. 상담 인입 자동 캡처 허브
- Source: 카카오톡 오픈채팅/전화 기록/문의폼/이메일
- Output: 단일 CRM 시트(리드ID, 유입채널, 관심업무, 긴급도, 다음액션)
- KPI: 누락 리드 0건, 응답 SLA 10분 이내

2. 상담 요약 자동화
- Input: 통화/채팅 원문
- Action: 요약 + 리스크 + 필요서류 + 다음 메시지 초안 자동 생성
- Output: 고객별 타임라인 카드
- KPI: 상담 후 정리시간 70% 절감

3. 견적서 자동 생성기 (신규등록/양도양수 분기)
- Input: 상담 체크리스트
- Action: 업무범위/난이도/기한 기반 템플릿 산출
- Output: PDF 견적서 + 카카오/메일 발송문
- KPI: 견적 발송까지 평균 5분 이내

4. 매물 추천 자동 송부
- Input: 고객 조건(예산/업종/지역/희망시점)
- Action: 시트/사이트 매물 매칭 -> 상위 3~5개 추천문 자동 생성
- Output: 카카오/메일 전송 패키지
- KPI: 상담->매물제안 리드타임 1시간 -> 10분

### P1. SEO + 광고 수익화 루프
1. 쿼리 리라이트 루프
- Input: Search Console + 네이버 서치어드바이저
- Action: 노출高/CTR低 쿼리 자동 탐지 -> 제목/요약 개선 큐 등록
- KPI: 30일 CTR +20% 이상

2. 포스팅 카니발라이제이션 차단
- Action: 기존 글 임베딩/유사도 점검 후 신규 발행 제한
- KPI: 중복 주제 발행률 0%

3. 상업의도 기반 CTA 최적화
- Variant: 손실회피형/신뢰형/속도형
- KPI: 클릭률 + 상담 전환율 동시 개선

4. 광고-콘텐츠 연동
- Action: 광고 고성과 키워드 자동 반영 콘텐츠 캘린더
- KPI: CPC 하락 + 유기/유료 전환율 상승

### P2. 운영 안정성 / 보안
1. 절전/오프라인 대응
- Action: 작업 큐 영속화 + 재시작시 미처리 작업 이어서 수행
- KPI: 중단 후 복구율 100%

2. 인증 만료 감시
- 대상: 사이트 로그인, 구글 서비스 계정, 웹훅
- Action: 사전 경고 + 자동 헬스체크
- KPI: 인증 오류로 인한 실패 0건

3. 보안 기본선
- 비밀키 분리(.env, 접근권한 최소화)
- 로그 마스킹(전화번호/민감정보)
- 발행/삭제 작업 감사로그

## Suggested Workflow Architecture
1. Intake Layer
- `lead_intake.py`: 상담 원문 수집 + 리드ID 발급

2. Decision Layer
- `lead_router.py`: 신규등록/양도양수/기업진단/기타 분류

3. Execution Layer
- `quote_engine.py`: 견적/서류목록 생성
- `listing_matcher.py`: 매물 추천
- `all.py`: 외부 매물 수집 + 시트 + 사이트 업로드

4. Growth Layer
- `seo_optimizer.py`: 쿼리 리라이트 큐
- `content_scheduler.py`: 성과 기반 발행 시간 최적화

5. Control Layer
- `ops_monitor.py`: 실패 재시도, 락, 알림, 헬스체크

## 14-Day Execution Plan
1. D1-D3: 상담 인입 허브 + 상담요약 자동화
2. D4-D6: 견적서 자동 생성 + 발송 템플릿 통합
3. D7-D9: 매물 자동 매칭/송부 파이프라인
4. D10-D12: 검색쿼리 리라이트 루프
5. D13-D14: 보안/운영 헬스체크 대시보드

## Immediate Next Actions
1. generate template: `python lead_intake.py --sample-csv`
2. validate ingest: `python lead_intake.py --csv lead_intake_sample.csv --dry-run`
3. run real ingest, then run matching: `python match.py`
4. next implementation (P0-2): `lead_brief.py` for consult summary automation
## Lead Intake Quick Start
- generate sample: `python lead_intake.py --sample-csv`
- single input: `python lead_intake.py --title "consult title" --content "consult body" --channel kakao --customer "name" --contact 01012345678`
- batch csv: `python lead_intake.py --csv lead_intake_sample.csv`
- dry run: `python lead_intake.py --csv lead_intake_sample.csv --dry-run`

## Ops Update
- daily consult-matching scheduler added: `consult_match_scheduler.py`
- start loop: `python consult_match_scheduler.py --scheduler`
- run once: `python consult_match_scheduler.py --once`
- status check: `python consult_match_scheduler.py --status`
- helper bat: `????????.bat`

## Revenue Execution Plan (2026-02-25)
### Offer stack (immediate launch)
1. Paid diagnostic PDF (gabji + analysis report)
- Lite: 99,000 KRW (single review)
- Standard: 299,000 KRW (risk + action plan + call)
- Premium: 590,000 KRW (negotiation-ready package)
2. Premium listing boost
- Weekend boost, top pin, verified badge
3. Success fee lane
- Keep the core high-ticket close as primary revenue source

### Funnel KPI (weekly)
1. Lead -> consult rate: >= 35%
2. Consult -> paid diagnostic rate: >= 20%
3. Diagnostic -> contract rate: >= 25%
4. Contract -> close rate: >= 40%

### Operating cadence (fit to power-on windows)
1. Weekday 09:00-23:00
- New listing sync + consult follow-up + 1-page admin memo fixes each hour
2. Weekend 14:00-23:00
- 1.5x batch volume for backfill, quality rewrite, premium pin refresh

### Stability gates (non-negotiable)
1. Sheet row jump watchdog must stay enabled
2. Admin memo format validator must block legacy format
3. Sum mismatch on gabji report must block by default (`--allow-sum-mismatch` only for manual override)
4. Domain separation guard must stay strict (`seoulmna.kr` vs `seoulmna.co.kr`)

### gb2_v3 integration readiness (deep check)
1. Added backend audit script:
- `python paid_ops/run.py gb2-audit --out logs/gb2_v3_integration_audit_latest.json`
2. Latest result:
- `gb2_v3`: not importable (module missing)
- `gabji`: fully ready
3. Decision:
- current production backend stays `gabji`
- `gb2_v3` can be enabled with `--gabji-backend gb2_v3` once module is installed and contract-compatible
4. Contract for backend swap:
- required symbols: `ListingSheetLookup`, `GabjiGenerator`
- required methods: `ListingSheetLookup.load_listing`, `GabjiGenerator.analyze_image`

### New commands for operations
1. Backend audit:
- `python paid_ops/run.py gb2-audit`
2. Report generation:
- `python paid_ops/run.py gabji-report --registration 7737 --output output/7737_report.pdf`
3. Backend override test:
- `python paid_ops/run.py gabji-report --registration 7737 --gabji-backend gb2_v3 --print-backend-audit`
4. Legacy/paid separation verification:
- `python paid_ops/run.py verify-split --out logs/paid_legacy_split_verify_latest.json`

## Tistory Automation Plan (seoulmna.tistory.com)
### Isolation rule
1. All Tistory code lives only under `tistory_ops/`
2. Legacy launchers (`*.bat`, `launchers/*.bat`, `scripts/*.cmd`) must not call `tistory_ops/`
3. Verify before release:
- `py -3 tistory_ops/run.py verify-split --out logs/tistory_split_verify_latest.json`

### Channel operating model
1. Weekday
- 09:00-23:00: one new post slot every 2 hours, focus on high-intent listings
2. Weekend
- 14:00-23:00: one new post slot every 1 hour, expand long-tail inventory coverage

### Post automation commands
1. Category discovery
- `py -3 tistory_ops/run.py categories-api` (legacy diagnostic)
2. Dry-run HTML preview
- `py -3 tistory_ops/run.py publish-listing --registration 7540 --dry-run --out-html output/tistory_7540_preview.html --print-payload`
3. Actual publish
- `py -3 tistory_ops/run.py publish-listing --registration 7540 --interactive-login --open-browser`
4. Debugger attach publish
- `py -3 tistory_ops/run.py publish-listing --registration 7540 --debugger 127.0.0.1:9222 --open-browser`

### 운영 지표
1. 품질
- 게시물 템플릿 섹션 완성도(회사개요/매출실적/재무지표/주요체크사항) 100%
2. 운영
- 드라이런 성공률, 실제 발행 성공률, 카테고리 매핑 성공률 추적
3. 유입
- 포스트 노출 대비 클릭(CTR), 클릭 대비 문의율만 모니터링



