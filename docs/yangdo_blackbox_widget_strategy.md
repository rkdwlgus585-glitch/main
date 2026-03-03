# AI 양도가 산정 계산기 블랙박스/위젯 운영안

## 목표
- 클라이언트(브라우저)에 원본 학습 데이터(구글시트 기반 매물 DB)를 노출하지 않고 결과값만 반환한다.
- 계산기를 외부 고객사 사이트에도 쉽게 삽입할 수 있도록 위젯 방식으로 제공한다.
- 대외 메시지는 `매일 업데이트되는 실거래가 기반 AI 양도가 산정`으로 통일한다.

## 현재 구현
- 서버형 블랙박스 API 추가: `yangdo_blackbox_api.py`
- 실행 배치: `launchers/launch_yangdo_blackbox_api.bat`
- 기본 엔드포인트:
  - `GET /health`
  - `GET /meta`
  - `POST /estimate`
  - `POST /reload`

## API 입력(요약)
- `license_text`
- `specialty`
- `y23`, `y24`, `y25`
- `balance_eok`, `capital_eok`, `surplus_eok`
- `license_year`, `debt_ratio`, `liq_ratio`
- `company_type`, `credit_level`, `admin_history`
- `ok_capital`, `ok_engineer`, `ok_office`

## API 출력(요약)
- `estimate_center_eok`, `estimate_low_eok`, `estimate_high_eok`
- `confidence_percent`, `confidence_score`
- `neighbor_count`, `hot_match_count`
- `risk_notes[]`
- `neighbors[]` (매물번호/범위/유사도/링크)

## 페이지 반영 방식
- `YANGDO_ESTIMATE_ENDPOINT`가 설정되면 계산기 페이지는 서버 API를 우선 호출한다.
- API 실패 시, 로컬 데이터가 있을 때만 로컬 계산으로 폴백한다.
- 운영 권장: 운영환경에서는 로컬 데이터 임베딩을 끄고 API만 사용.

## 위젯화 권장안
1. 기본형(링크형): 사이트에 버튼만 삽입해 계산기 전용 페이지로 유도.
2. 임베드형(iframe):
   - 고객사 페이지에 `<iframe src="https://seoulmna.kr/yangdo-ai-customer/">` 삽입
   - 내부 로직/데이터는 서버에서만 처리.
3. JS 위젯형(2차):
   - 외부 사이트에 `<script src=".../widget.js">` 1줄 삽입
   - 버튼/모달/상담 CTA를 동일 UX로 배포.

## 마케팅 문구(권장)
- `매일 업데이트되는 실거래가 기반 AI 양도가 산정`
- `입력 즉시 예상 범위 + 상담 연결`
- `유사 매물 근거 기반 산정`

## 운영 체크리스트
- API 서버 상시 실행(윈도우 작업 스케줄러/서비스)
- `/health` 200 모니터링
- 실패 로그(429/502/timeout) 일별 집계
- 주 1회 `/reload` 또는 자동 리프레시 정책 적용
