# Workspace Partitions

이 폴더는 이번 세션 작업물을 목적별로 분리한 구획입니다.

## partitions
- `calculator_session/`: 양도가/인허가 계산기 관련 산출물
- `site_session/`: `seoulmna.co.kr` / `seoulmna.kr` 홈페이지 반영/미리보기 산출물

## 운영 원칙
1. 런타임 코어 파일(`all.py`, `yangdo_*`, `acquisition_calculator.py`, `permit_diagnosis_calculator.py`, 기존 운영 스크립트)은 경로 의존성 때문에 루트 경로를 유지합니다.
2. 세션 산출물(문서, 임시 스크립트, 임시 HTML/CSS/JS, 테스트 산출물)은 이 파티션으로 이동합니다.
3. 이후 신규 작업도 먼저 목적 파티션에 저장한 뒤, 운영 반영이 필요한 것만 루트 운영 경로로 승격합니다.

## 유지보수 명령
- 전체 동기화/복원/임시파일 이동/상태 확인:
  - `py -3 scripts/partition_maintenance.py --sync --restore-missing --relocate-site-temp --status`
- 런처:
  - `launchers/partition_maintenance.bat`
  - `작업물구획정리.bat`
