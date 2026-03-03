# AI 양도가 산정 계산기 백서 실행 현황 (2026-03-01)

## 결론: `seoulmna.kr`로 분리 이전이 필수는 아님
- 그누보드5(`seoulmna.co.kr`) 내부에서도 서버측 API(`api_calc.php`)로 **원본 데이터 비노출 구조** 구현 가능.
- 따라서 현재 단계에서는 `co.kr` 단독 운영으로도 백서의 핵심 목표(보안/전환/리드수집) 달성 가능.
- `kr`는 선택적 확장(브랜드 분리, 트래픽 분산, 광고용 랜딩) 용도로 유지하는 것이 현실적.

## 이번 턴 반영 완료
- 전역 우측 세로 배너 재구성
  - 로고 제거
  - `서울건설정보` 텍스트 브랜딩 적용
  - 서브 문구에서 `카카오톡 오픈채팅 상담` 문구 제거, 전화만 유지
- 계산기 페이지 헤더 로고 제거
  - 상단 브랜드를 텍스트만 노출하도록 변경
- 계산기 제목 색상 고정
  - `h2`에 `color: #f8fbff !important` 적용 (검정색 출력 이슈 방지)
- `co.kr` 재배포 완료
  - 고객용: `https://seoulmna.co.kr/yangdo_ai/7`
  - 취득비용: `https://seoulmna.co.kr/yangdo_ai_ops/8`
- `co.kr` 전역 배너 스니펫 재적용 완료
  - 적용 리포트: `logs/co_global_banner_apply_latest.json` (`ok=true`)

## 백서 핵심 항목 실행 파일 생성 완료
- 그누보드5 블랙박스 패키지 자동 생성기 추가
  - 스크립트: [generate_gnuboard_blackbox_package.py](/C:/Users/rkdwl/Desktop/auto/scripts/generate_gnuboard_blackbox_package.py)
- 서버 배포용 산출물 생성
  - API: [api_calc.php](/C:/Users/rkdwl/Desktop/auto/output/deploy/gnuboard_blackbox/api_calc.php)
  - 데이터셋: [yangdo_dataset.php](/C:/Users/rkdwl/Desktop/auto/output/deploy/gnuboard_blackbox/yangdo_dataset.php)
  - 배포가이드: [README.md](/C:/Users/rkdwl/Desktop/auto/output/deploy/gnuboard_blackbox/README.md)
- 최신 학습데이터 반영 건수
  - `dataset_rows = 1146`

## 백서 소스 반영 근거 파일
- 문서 스냅샷: [whitepaper_sources_snapshot.json](/C:/Users/rkdwl/Desktop/auto/docs/whitepaper_sources_snapshot.json)
- 추출본(원문 참조): [whitepaper_docx_extract.json](/C:/Users/rkdwl/Desktop/auto/docs/whitepaper_docx_extract.json)

## 남은 1개 운영 작업 (서버 파일 업로드)
- 이유: 현재 자동화 권한은 게시글/HTML 수정 중심이며, 웹루트 PHP 파일 생성 권한(FTP/SFTP/호스팅 파일매니저 API)은 별도.
- 작업:
  - `output/deploy/gnuboard_blackbox/api_calc.php`
  - `output/deploy/gnuboard_blackbox/yangdo_dataset.php`
  - 두 파일을 `seoulmna.co.kr` 서버 경로에 업로드
- 업로드 후:
  - `.env`의 `YANGDO_ESTIMATE_ENDPOINT=https://seoulmna.co.kr/api_calc.php`
  - 계산기 재배포 실행 시 브라우저 dataset 비노출 모드 전환 가능.

