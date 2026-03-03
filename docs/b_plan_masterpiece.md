# B안 마스터피스 실행 가이드 (GAS + seoulmna.co.kr)

## 목표
- FTP 없이 `seoulmna.co.kr` 내부에서 계산기 운영
- 계산 로직/데이터는 GAS(Web App)로 블랙박스화
- co.kr에는 라우팅/브랜딩/전환 UI만 남기고, 계산 엔진은 외부 실행

## 구성
1. `scripts/generate_gas_masterpiece_bundle.py`
- 고객용/취득비용 계산기 HTML + `Code.gs` + `appsscript.json` 자동 생성
- 출력: `output/gas_masterpiece/`

2. `scripts/deploy_co_content_pages.py`
- 그누보드 내용관리 `ai_calc`, `ai_acq` 자동 생성/수정
- 내용관리 페이지는 브리지 플레이스홀더로 유지

3. `scripts/prepare_co_global_banner_snippet.py`
- 전역 배너 + 계산기 브리지 스니펫 생성
- 내용관리/게시판 페이지 모두 자동 브리지 렌더링

4. `scripts/apply_co_global_banner_admin.py`
- 관리자 `config_form`의 추가 script에 자동 반영

5. `scripts/deploy_b_plan_masterpiece.py`
- 위 1~4 + 검증을 순차 실행하는 오케스트레이터

## 실행
- 초간단: `양도가산정기_B안_마스터피스_전체실행.bat`
- 직접 실행:
```powershell
py -3 scripts/deploy_b_plan_masterpiece.py --report logs/b_plan_masterpiece_latest.json
```
- 배포 품질 강제(권장): GAS `/exec` URL이 아니면 실패 처리
```powershell
py -3 scripts/deploy_b_plan_masterpiece.py --require-gas --gas-exec-url "https://script.google.com/macros/s/xxx/exec" --persist-env --report logs/b_plan_masterpiece_latest.json
```

## GAS 배포
1. `output/gas_masterpiece/`의 파일을 Apps Script 프로젝트에 반영
2. 웹앱 배포 후 exec URL 확보
3. 재실행:
```powershell
py -3 scripts/deploy_b_plan_masterpiece.py --gas-exec-url "https://script.google.com/macros/s/xxx/exec" --persist-env
```

## 검증 포인트
- `https://seoulmna.co.kr/` 페이지 소스에 `SEOULMNA GLOBAL BANNER START` 존재
- `https://seoulmna.co.kr/bbs/content.php?co_id=ai_calc` 접속 시 브리지 렌더링
- `https://seoulmna.co.kr/bbs/content.php?co_id=ai_acq` 접속 시 브리지 렌더링
- 리포트: `logs/b_plan_masterpiece_latest.json`
- 리포트 `warnings`에 `frame_urls_not_gas_exec_using_fallback_or_custom_domain`가 있으면 아직 GAS 실URL 전환 전 상태
