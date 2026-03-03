# 양도가 자동 산정 웹사이트 탑재 실행계획 (총괄 디렉터 버전)

## 1. 목표 고정
- 최종 목표는 **프로그램 실행**이 아니라 **seoulmna.co.kr 웹사이트 탑재/운영 완료**입니다.
- 고객용 화면은 가격 용어를 숨기고 숫자 범위만 보여줍니다.
- 운영자용 화면은 매물번호/now UID 등 내부 진단 정보를 포함합니다.
- 기존 `mna` 매물 게시판과 분리해 유지보수 리스크를 낮춥니다.

## 2. 핵심 원칙
- 고객 노출 문구에서 `입금가`, `양도가` 문자열은 금지합니다.
- 고객 링크는 항상 `https://seoulmna.co.kr/mna/{매물번호}` 형식으로 연결합니다.
- 운영자용은 별도 보드(`yangdo_ai_ops`)에서만 접근하도록 권한 분리합니다.
- 게시판 구조와 자동화 스케줄은 기존 매물 운영 플로우에 영향이 없도록 분리합니다.

## 3. 게시 구조(현실 실행안)
- 고객 보드: `yangdo_ai`
- 운영자 보드: `yangdo_ai_ops`
- 게시 방식: 각 보드 1개 고정 글(`wr_id`)을 계속 수정하는 방식
- 기대 효과:
  - URL 고정으로 마케팅/광고/상담 링크 관리 단순화
  - 게시글 누적 폭증 방지
  - 수정 이력/운영 통제 용이

## 4. 완료된 구현 항목
- `all.py`에 양도가 페이지 빌드/게시 기능 분리 구현 완료
  - `--build-yangdo-page`
  - `--publish-yangdo-page`
  - `--yangdo-page-mode customer|owner`
  - `--yangdo-page-board-slug`
  - `--yangdo-page-wr-id`
- 산정 로직 분리 완료: `yangdo_calculator.py`
- 웹사이트 릴리즈 오케스트레이터 추가 완료:
  - `scripts/deploy_yangdo_site_release.py`
  - 테스트(산정 dry-run + HTML 생성 + 정책검사) 자동화
  - 결과 리포트 JSON 생성
- 현장 실행용 배치 파일 추가 완료:
  - `양도가산정기_미리보기.bat`
  - `양도가산정기_고객게시.bat`
  - `양도가산정기_운영자게시.bat`
  - `양도가산정기_웹사이트탑재_전체실행.bat`
- 최신 테스트 결과:
  - `logs/yangdo_site_release_latest.json` 기준 `ok=true`

## 5. 실행 절차(기획 → 실행 → 완료)

### 5-1) 사전 체크
- `.env`에 사이트/관리자 계정 변수 존재 확인
- 게시 대상 `bo_table`, `wr_id` 확정
- 기존 `mna` 보드와 분리 상태 확인

### 5-2) 사전 시뮬레이션(무중단)
```powershell
py -3 scripts/deploy_yangdo_site_release.py --report logs/yangdo_site_release_latest.json
```
- 수행 내용:
  - 산정 dry-run
  - 고객/운영자 HTML 생성
  - 고객 페이지 정책 검사(금지 단어, 버튼 존재)
- 통과 조건:
  - `overall_ok=True`
  - `forbidden_terms=[]`

### 5-3) 실배포
```powershell
py -3 scripts/deploy_yangdo_site_release.py `
  --publish `
  --customer-board yangdo_ai `
  --customer-wr-id <고객WRID> `
  --owner-board yangdo_ai_ops `
  --owner-wr-id <운영자WRID> `
  --report logs/yangdo_site_release_latest.json
```
- 배포 후 리포트의 `publish_urls` 확인
- 고객 URL/운영자 URL 수동 검수

### 5-4) 완료 기준
- 고객 보드: 정상 노출 + 링크 정상 + 금지 단어 미노출
- 운영자 보드: 내부 식별자 노출 정상
- 기존 매물 자동화(`mna`)와 충돌 없음

## 6. 브레인스토밍(실행 가능한 개선안)

### A. 신뢰 강화 UX
- 결과 상단에 “최근 N건 학습 기반” 배지
- 범위 옆에 신뢰도(높음/중간/검토필요) 표시
- “왜 이 범위인지” 3줄 요약 자동 생성

### B. 상담 전환 개선
- 고객 페이지 CTA:
  - “상담 요청”
  - “같은 업종 최근 거래 범위 보기”
- 클릭 이벤트 로그를 저장해 전환 퍼널 추적

### C. 운영 효율
- 저신뢰 결과만 운영자 큐로 자동 분리
- 운영자 수정값을 재학습용 정답 데이터로 적재
- 주 1회 가중치 리밸런싱(공제/자본금/기술자/사무실/이익잉여금 우선)

## 7. 운영 리스크와 대응
- 리스크: 잘못된 링크 매핑
  - 대응: 게시 전 URL 정규식 검증 + 배포 차단
- 리스크: 고객 문구 정책 위반
  - 대응: `입금가/양도가` 문자열 검사 실패 시 배포 차단
- 리스크: 보드 권한 혼선
  - 대응: 고객/운영자 보드 권한 분리와 noindex 적용

## 8. 다음 실행 체크리스트
- 고객 보드 `wr_id` 확정
- 운영자 보드 `wr_id` 확정
- 실배포 1회 실행
- 배포 URL 2개(고객/운영자) 검수 후 운영 전환

## 9. 현재 실제 검증 결과 (2026-02-28)
- 테스트 모드 릴리즈: 통과 (`overall_ok=true`)
- 실게시 모드 릴리즈: 차단됨
  - 차단 사유: `publish_customer_url_missing`, `step_failed:publish_customer`
  - 원인: 서버 응답상 `yangdo_ai` 게시판 미존재 또는 글쓰기 권한 없음
- 조치 순서:
  1. 그누보드에 `yangdo_ai`, `yangdo_ai_ops` 생성
  2. 고객/운영자 권한 분리 설정
  3. 실게시 재실행 후 URL 생성 확인
