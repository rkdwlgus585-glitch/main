# SeoulMNA 실행 로드맵 (현실 운영안)

## 1) 목표
- 자동화는 `동시 일괄 실행`이 아닌 `분리 실행 + 시간차 실행`으로 운영한다.
- 사전 검증과 시뮬레이션을 통과한 경우에만 실제 적용한다.
- 운영 시간 제약(평일 09:00~23:00, 주말 14:00~23:00) 안에서만 작업한다.

## 2) 운영 제약(고정)
- 활성 시간:
  - 평일: `09:00~23:00`
  - 주말: `14:00~23:00`
- now→sheet 실행 슬롯: `12:00`, `18:00` (하루 2회)
- 통합 시작업(`SeoulMNA_All_Startup`)은 비활성 유지
- 권장 시작 지연:
  - Ops Watchdog: `0초`
  - WordPress Scheduler Watchdog: `+60초`
  - Blog Startup Once: `+180초` (선택)
  - Tistory Daily Once: `+360초` (선택)

## 3) 실행 전 필수 절차
1. 계획 출력(변경 없음):
```powershell
py -3 scripts/execute_roadmap_simulation.py --strict
```
2. 결과 확인:
   - `logs/roadmap_simulation_latest.json`
   - `logs/roadmap_simulation_latest.md`
3. `overall_ok=true`가 아니면 적용 금지

## 4) 시뮬레이션 합격 기준
- Preflight
  - `all.py`, `mnakr.py`, `tistory_ops/run.py`, `service_account.json`, `.env` 존재
  - `SITE_URL`, `MNA_BOARD_SLUG`, `ADMIN_ID`, `ADMIN_PW`, `GEMINI_API_KEY` 유효
  - WordPress 인증 방식 1개 이상 유효 (`WP_JWT_TOKEN` 또는 `WP_USER+APP_PASSWORD` 등)
- 분리 검증
  - `scripts/show_entrypoints.py --strict` 통과
  - `tistory_ops/run.py verify-split` 통과
- 블로그 검증
  - `mnakr.py --schedule-check` 정상
  - `mnakr.py --wp-check` 통과
- 매물 파이프라인 검증
  - 관리자메모 계획 시뮬레이션(`--fix-admin-memo-plan-only`) 정상
  - 대조 dry-run(`--reconcile-dry-run`) 실행 가능

## 5) 적용 절차 (2단계 안전 적용)
1. 적용 계획 먼저 출력:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/apply_execution_profile.ps1
```
2. 계획이 맞으면 실제 적용:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/apply_execution_profile.ps1 -Apply
```
3. 블로그/티스토리 시작업도 자동 활성화가 필요할 때만:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/apply_execution_profile.ps1 -Apply -EnableBlogStartupOnce -EnableTistoryDailyOnce
```

## 6) 운영 Runbook
- 상시(로그온 후 백그라운드)
  - `SeoulMNA_Ops_Watchdog`: 시트/홈페이지/관리자메모/품질 점검
  - `SeoulMNA_MnakrScheduler_Watchdog`: 워드프레스 스케줄러 유지
- 선택(자동 발행이 필요한 날만 활성)
  - `SeoulMNA_Blog_StartupOnce`
  - `SeoulMNA_Tistory_DailyOnce`

## 7) 장애 대응
1. 게시/동기화 실패 시:
   - `logs/startup_now_to_sheet.log`
   - `logs/ops_watchdog.log`
   - `logs/startup_blog_once.log`
   - `logs/startup_tistory_daily.log`
2. 워드프레스 인증 점검:
```powershell
py -3 mnakr.py --wp-check
```
3. 엔트리포인트 계약 점검:
```powershell
py -3 scripts/show_entrypoints.py --strict
```
4. 롤백 원칙:
   - 적용 스크립트 재실행으로 태스크 상태를 즉시 복원
   - `SeoulMNA_All_Startup`은 필요 시에만 임시 활성

## 8) 현재 검증 스냅샷 (기준 시각: 2026-02-28)
- `py -3 scripts/execute_roadmap_simulation.py --strict` 결과: `overall_ok=true`
- 작업 스케줄러 상태:
  - `SeoulMNA_Ops_Watchdog`: Enabled
  - `SeoulMNA_MnakrScheduler_Watchdog`: Enabled
  - `SeoulMNA_Blog_StartupOnce`: Disabled
  - `SeoulMNA_Tistory_DailyOnce`: Disabled
  - `SeoulMNA_All_Startup`: Disabled

이 상태가 현재 요구사항(분리 실행, 과부하/429 리스크 억제)과 가장 일치한다.

## 9) 게시판 활용 현실 계획 (서울건설정보 + 외부 채널 분리)
1. 서울건설정보 `mna` 게시판(고객 기준 메인)
- 목적: 매물 원본 데이터의 단일 출처(Single Source of Truth)
- 노출 원칙:
  - 공개 양도가는 `협의` 유지
  - 청구 양도가/입금가 정보는 관리자메모(`wr_20`)에만 기록
  - 관리자메모는 “청구 양도가 입력 후” 일괄 반영
- 운영 주기:
  - now→sheet: 12:00, 18:00
  - 관리자메모 증분 교정: 활성 시간 내 주기 실행
  - 관리자메모 전체 교정: 1일 1회

2. 서울건설정보 공지/안내 게시판(운영 공지)
- 목적: 월별 정리, 제도변경, 점검 공지
- 운영:
  - 월별 아카이브 자동 생성은 유지
  - 고객 공지는 사람 검수 후 게시

3. 서울건설정보 양도가 산정 페이지(고객/내부 2뷰)
- 고객 뷰:
  - 매물번호 기준 링크 일치
  - 가격은 `오차 범위 숫자`만 표시 (`입금가`, `양도가` 용어 금지)
- 내부 뷰:
  - 서울건설정보 매물번호 + now UID 동시 표기
  - 근거 데이터/유사도/참조 매물 표시

4. 외부 채널(워드프레스, 티스토리)
- 목적: 유입 확보와 검색 확장
- 원칙:
  - 서울건설정보 원본과 분리 실행
  - 티스토리 자동화는 `tistory_ops`로만 운용
  - 발행 실패가 서울건설정보 파이프라인을 막지 않도록 격리

## 10) 부팅 시 “앱 선택” 팝업 4개 원인/해결/재발 방지
1. 원인
- 사용자 Startup 폴더(`%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup`)에
  - `MNAKR_AutoScheduler.cmd.bak_20260225_1`
  - `MNAKR_AutoScheduler.cmd.disabled_20260227_093548`
  - `SeoulMNA_BlogScheduler_OnStartup.vbs.disabled_20260227_093548`
  - `SeoulMNA_NowToSheet_OnStartup.vbs.disabled_20260227_093548`
  파일이 남아 있음.
- 이 파일들은 확장자가 `.bak_*`, `.disabled_*`로 바뀐 레거시 시작파일이라, 로그온 시 Windows가 실행 대상을 몰라 “앱 선택” 창을 띄움.

2. 해결
- `scripts/apply_execution_profile.ps1`에 레거시 Startup 파일 자동 아카이브 기능 추가.
- `-Apply` 실행 시 위 파일을 `logs/startup_artifacts_archive/<timestamp>/`로 이동.

3. 재발 방지
- `scripts/execute_roadmap_simulation.py --strict`에
  - `startup:legacy_artifacts_absent` 검증을 필수 항목으로 추가.
- 즉, 다음부터는 Startup 잔여 파일이 있으면 시뮬레이션 단계에서 즉시 실패하여 적용 전 차단됨.
