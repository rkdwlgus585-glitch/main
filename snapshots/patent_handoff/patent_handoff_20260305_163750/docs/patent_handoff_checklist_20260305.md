# 변리사 핸드오프 체크리스트 (2026-03-05)

## 공통 제출물
1. 발명 개요 1p
- 양도가/인허가 각각 문제정의, 해결구성, 기대효과.
2. 기술 흐름도
- 입력 -> 정규화/매핑 -> 판정/산정 -> 결과/로그.
3. 구현 근거 경로
- 실제 코드 파일/테스트 파일/로그 산출물 목록.
4. 사업 적용 범위
- 서울건설정보 내부 적용 + 파트너 멀티테넌트 확장 구조.

## 양도가 패키지
1. 문서:
- `docs/patent_package_yangdo_draft_20260305.md`
2. 코드 근거:
- `yangdo_blackbox_api.py`
- `yangdo_calculator.py`
- `acquisition_calculator.py`
- `yangdo_consult_api.py`
3. 테스트/로그:
- `tests/test_yangdo_calculator_input_variables.py`
- `logs/tenant_usage_billing_latest.json`

## 인허가 패키지
1. 문서:
- `docs/patent_package_permit_draft_20260305.md`
2. 코드/데이터 근거:
- `permit_diagnosis_calculator.py`
- `config/permit_registration_rules_law.json`
- `config/permit_registration_criteria_expanded.json`
3. 테스트/로그:
- `tests/test_permit_diagnosis_calculator_rules.py`
- `scripts/run_permit_diagnosis_input_fuzz.py`

## 법률/행정 게이트(외부전문가 필요)
1. 독립항/종속항 최종 확정
2. 법령 해석 문구와 면책 문구 검토
3. 데이터 출처·권리·개인정보 처리 고지 검토

## 내부 완료 조건
1. 변리사 1차 미팅 전 3개 문서 전달 완료
2. 질의응답 로그를 `docs/`에 버전별 저장
3. 출원 일정(국내 우선권 기준) 확정

## 번들 생성 자동화
- 실행: `py -3 scripts/prepare_patent_handoff_bundle.py`
- 결과:
  - `snapshots/patent_handoff/patent_handoff_<timestamp>/manifest.json`
  - `snapshots/patent_handoff/patent_handoff_<timestamp>.zip`
