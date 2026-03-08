# Zero-Touch Revenue Strategy (기획 -> 수입)

작성일: 2026-02-25
기준 데이터: `result/latest_summary.json`, `result/sales_kpi_latest.json`, `result/sales_simulation_latest.json`

## 1. 결론 요약
- 현재 상태는 **자동화 준비는 완료**, **영업 실행은 미착수** 상태다.
- 따라서 "내가 손대지 않아도"를 달성하려면, 시스템 자동화 + 실행 인력 위임을 결합한 운영모델이 필요하다.
- 현실적 목표:
  - 1차(4주): 월 700만~1,200만 KRW 런레이트
  - 2차(8~12주): 월 1,200만~2,000만 KRW 런레이트

## 2. 현실 전제(필수)
"무터치"는 아래 4개 권한 위임이 없으면 성립하지 않는다.
1. 영업 실행 권한: 대리인이 고객 연락/미팅 예약/제안 발송 가능
2. 가격/할인 권한: 패키지별 허용 할인율(예: 10%) 사전 승인
3. 계약/정산 권한: 전자계약, 세금계산서, 입금 확인 담당자 지정
4. 운영 책임자 지정: KPI 미달 시 즉시 교정 실행하는 1인 책임자

## 3. 현재 수치 기반 진단
- 수집 품질: FULL, 총 920건, 재량 627건
- 영업 퍼널: 50건 모두 `new`, contacted/meeting/proposal/closed 모두 0
- 파이프라인 시뮬레이션(8주 P50):
  - conservative: 15.6M
  - base: 22.8M
  - aggressive: 30.0M
- 해석:
  - 데이터와 리드 품질은 "영업 가능한 수준"
  - 실행조직(담당자 배정/접촉/제안)이 없어 매출 실현이 정지된 상태

## 4. 무터치 운영 구조 (RACI)
### 4.1 역할
- Owner(당신): 월간 목표 승인만 수행
- Revenue Operator(필수 1명): 일일 운영 총괄, KPI 책임
- SDR/BD(1~2명): 아웃바운드 연락/미팅 확보
- Proposal Manager(1명): 제안서/견적 발송, SLA 준수
- Delivery Lead(1명): 납품 품질/일정 관리
- Finance Admin(파트타임): 청구/입금/미수 관리

### 4.2 책임 분리
- 시스템은 `autopilot.py` + `business_ops.py`가 자동 수행
- 사람은 `sales_activity_latest.csv` 상태 전환과 고객 커뮤니케이션만 수행
- Owner는 주 1회 보고서 승인/방향 수정만 수행

## 5. 수익 모델 (자동 실행 친화)
### 5.1 상품
- Quick Win: 1.2M
- Standard: 1.8M
- Premium: 2.5M
- Retainer Lite: 390K / month
- Retainer Pro: 990K / month

### 5.2 목표 믹스(8주차까지)
- Quick Win 45%
- Standard 40%
- Premium 15%
- 예상 평균 객단가(가중): 약 1.62M

### 5.3 매출 목표 역산
- 월 20M 목표 시 필요 클로즈 수:
  - 평균 1.62M 기준 약 13건/월
- 현재 주 2건 목표는 월 약 8.7건(약 10M 수준)으로 부족
- 따라서 20M 달성 조건:
  - 주간 클로즈 목표를 3.5건 이상으로 상향
  - 또는 Retainer 15~20계정 추가 확보

## 6. 실행 시퀀스 (무터치 오퍼레이션)
### Phase 0 (D+2)
1. `clients.csv` 30개 이상 채우기(운영자 작업)
2. `sales_activity_latest.csv` 50건 owner 강제 배정
3. 상태 전환 SLA 고정
   - new -> contacted: 48시간
   - contacted -> meeting: 7일
   - meeting -> proposal: 24시간
   - proposal follow-up: D+2, D+5

### Phase 1 (주 1~2)
1. 주 50건 초도 연락
2. 주 10건 미팅 확보
3. 주 4건 제안서 발송
4. 주 2건 클로즈 달성

### Phase 2 (주 3~6)
1. 제안서 템플릿 2종 A/B 테스트
2. 업종별 콜 스크립트 분리(토목/전기/기타)
3. 미팅 녹취/노트 기반 반려사유 분류
4. 승률 낮은 구간(미팅->제안, 제안->클로즈) 집중 교정

### Phase 3 (주 7~12)
1. 고가 패키지(Premium/Standard) 비중 확대
2. Retainer 전환 캠페인 자동화
3. 월 반복매출(MRR) 비중 30% 이상 확보
4. 월 20M 목표 재판정(달성/보류)

## 7. 자동화 운영 규칙 (핵심)
1. 스케줄
- 매일 08:30: `py autopilot.py --skip-test-api --skip-collect --skip-regression --continue-on-error`
- 매주 월 09:00: `py autopilot.py --continue-on-error`

2. 보고 산출물(자동)
- `result/next_actions_latest.md`
- `result/sales_daily_plan_latest.md`
- `result/sales_weekly_report_latest.md`
- `result/sales_simulation_latest.md`

3. 자동 경보 트리거
- contacted_rate < 0.4 -> 아웃바운드 증량 지시
- close_rate < 0.2 (proposal 3건 이상) -> 후속 일정 강제
- closed = 0 (2주 연속) -> 상위 20개 집중 스프린트 발동

## 8. 리스크와 차단선
- 리스크 1: 고객사 DB 부재
  - 차단선: `clients.csv` 30개 미만이면 광고/확장 금지
- 리스크 2: 담당자 미배정
  - 차단선: owner 공란 10% 초과 시 신규 리드 투입 중지
- 리스크 3: 저단가 편중
  - 차단선: Quick Win 비중 60% 초과 시 Standard 업셀 캠페인 의무
- 리스크 4: 미수금 증가
  - 차단선: 미수 30일 초과 3건 이상 시 신규 제안 제한

## 9. 무터치 운영의 현실적 정의
- "내가 손대지 않음"은 "완전 무인"이 아니라 "위임된 조직이 자동 보고 체계로 실행"을 뜻한다.
- Owner는 아래만 하면 된다.
  1. 월 1회 목표 승인
  2. 월 1회 인력/예산 승인
  3. 주간 보고서 확인(10분)

## 10. 즉시 실행 체크리스트
1. 운영자 1명 지정(오늘)
2. `clients.csv` 30개 입력(48시간)
3. `sales_activity_latest.csv` owner 50건 배정(오늘)
4. 주간 KPI 목표 고정
   - contacted >= 50
   - meeting >= 10
   - proposal >= 4
   - closed >= 2
5. 2주 후 재판정
   - 위 4개 KPI 달성 시 확장
   - 미달 시 스크립트/오퍼/타깃 재설계
