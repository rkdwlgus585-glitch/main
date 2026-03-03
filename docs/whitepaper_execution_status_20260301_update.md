# AI 양도가 산정 계산기 실행 현황 업데이트 (2026-03-01)

## 1) 결론: `seoulmna.kr`로 강제 이전은 필수가 아닙니다
- `seoulmna.co.kr`(그누보드5)에서 서버측 계산 API(`api_calc.php`)를 붙이면 데이터 비노출 구조를 구현할 수 있습니다.
- 즉, 현재 단계에서 `co.kr` 단독 운영으로도 백서 목표(원본 데이터 은닉, 상담 전환, 운영 자동화) 달성이 가능합니다.
- `kr`은 선택 사항입니다. 브랜딩/광고 랜딩/서비스 분리 목적이 있을 때만 추가 운영하면 됩니다.

## 2) 이번 반영 완료 항목
- 전역 배너(홈페이지) 최신 반영 완료
  - 로고 제거
  - 브랜드 텍스트를 `서울건설정보`로 통일
  - 서브 문구를 `대표 행정사 상담 / 010-9926-8661`로 통일
  - 팝업 새창 시도 + 차단 시 우측 고정 배너 폴백
- 계산기 페이지 반영 완료
  - 페이지 로고 제거
  - 제목 `AI 양도가 산정 계산기` 색상 강제(검정으로 밀리는 문제 방지)
  - 상담 안내 문구를 `대표 행정사 상담 / 010-9926-8661`로 정리
- 배포/검증
  - 고객용: `https://seoulmna.co.kr/yangdo_ai/7`
  - 취득비용: `https://seoulmna.co.kr/yangdo_ai_ops/8`
  - 검증 스크립트: `logs/verify_yangdo_full_upgrade_latest.json` (`overall_ok=true`)

## 3) 백서 실행 산출물(데이터 은닉화 패키지)
- 생성 완료:
  - `output/deploy/gnuboard_blackbox/api_calc.php`
  - `output/deploy/gnuboard_blackbox/yangdo_dataset.php`
  - `output/deploy/gnuboard_blackbox/README.md`
- 포함 로직:
  - 3년/5년 실적 비교 후 가중치 반영
  - 유사도 기반 이웃 매물 추정
  - 오차 범위/신뢰도/리스크 노트 반환

## 4) 첨부 문서 실행 추적 파일
- DOCX 실행 다이제스트: `docs/whitepaper_docx_execution_digest.json`
- PDF 실행 다이제스트: `docs/whitepaper_pdf_execution_digest.json`
- 기존 추출본: `docs/whitepaper_docx_extract.json`

## 5) 남은 운영 1단계 (권한 이슈)
- 현재 자동화는 게시글/HTML 반영은 가능하지만, 웹서버 루트에 PHP 파일 업로드 권한(FTP/SFTP 또는 서버 파일관리 API)은 별도입니다.
- 아래 파일 업로드만 완료되면 브라우저 dataset 비노출 모드로 전환됩니다.
  - `api_calc.php`
  - `yangdo_dataset.php`
- 업로드 후 `.env`에 아래를 설정:
  - `YANGDO_ESTIMATE_ENDPOINT=https://seoulmna.co.kr/api_calc.php`

