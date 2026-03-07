# 양도양수/인허가 보안 기반 운영안 (2026-03-05)

## 1) 목표
- 탈취(키/계정/PII), 해킹(무단 접근/데이터 위변조), DDoS(가용성 저하) 리스크를 동시에 낮춘다.
- 서울건설정보 내부 운영과 타사 제휴형(멀티테넌트) 확장을 같은 보안 프레임으로 통일한다.

## 2) 코드 반영 완료 항목

### A. 공통 보안 모듈 신설
- 파일: `security_http.py`
- 적용 기능:
  - API 보안 헤더 기본 세트
  - API Key/Bearer 인증 비교 (`hmac.compare_digest`)
  - 신뢰 가능한 클라이언트 IP 파싱
  - Sliding-window 레이트리미터
  - Origin allowlist 파서

### B. 양도가 블랙박스 API 하드닝
- 파일: `yangdo_blackbox_api.py`
- 반영:
  - `/estimate` 인증키 게이트(옵션)
  - `/reload` 관리자 키 게이트(없으면 일반 API키 fallback)
  - 요청 본문 크기 제한
  - `application/json` 강제
  - CORS allowlist
  - 보안 헤더 + 내부 예외 메시지 마스킹
  - 레이트리밋 + `Retry-After`

### C. 상담/사용로그 API 하드닝
- 파일: `yangdo_consult_api.py`
- 반영:
  - `/consult`, `/usage` 인증키 게이트
  - 요청 본문 크기 제한
  - `application/json` 강제
  - CORS allowlist 모드(빈 값이면 CORS 미허용)
  - 보안 헤더 + 내부 예외 메시지 마스킹
  - 레이트리밋 + `Retry-After`

## 3) 운영 설정값 (권장)

### 양도가 블랙박스 API
- `YANGDO_BLACKBOX_API_KEY`: 필수 (프론트 호출용)
- `YANGDO_BLACKBOX_ADMIN_API_KEY`: 필수 (`/reload` 전용)
- `YANGDO_BLACKBOX_ALLOW_ORIGINS`: 서울건설정보/파트너 도메인만
- `YANGDO_BLACKBOX_RATE_LIMIT_PER_MIN`: 90 (시작값)
- `YANGDO_BLACKBOX_MAX_BODY_BYTES`: 65536
- `YANGDO_BLACKBOX_TRUST_X_FORWARDED_FOR`: 프록시 뒤면 `true`

### 상담 API
- `YANGDO_CONSULT_API_KEY`: 필수
- `YANGDO_CONSULT_ALLOW_ORIGINS`: 허용 도메인만
- `YANGDO_CONSULT_RATE_LIMIT_PER_MIN`: 120 (시작값)
- `YANGDO_CONSULT_MAX_BODY_BYTES`: 131072
- `YANGDO_CONSULT_TRUST_X_FORWARDED_FOR`: 프록시 뒤면 `true`

## 4) 근본 대응(인프라 계층, 필수)
애플리케이션 코드만으로는 대규모 DDoS를 완전 차단할 수 없다. 아래를 반드시 함께 적용한다.

1. Reverse Proxy/WAF
- Cloudflare(또는 동급) 앞단 배치
- Bot fight + Managed WAF 규칙 on
- `/reload`, `/usage`는 stricter rate limit

2. Origin 보호
- API origin IP 직접공개 금지
- 방화벽에서 프록시 egress IP만 허용

3. 비밀정보 관리
- `.env` 장기보관 금지
- Secret Manager 또는 OS credential store 사용
- 키 30일 주기 회전, key overlap 7일

4. 관제/탐지
- 401/429/5xx 비율 알람
- 요청량 급증 알람
- 관리자 엔드포인트 호출 감사로그 별도 분리

## 5) 멀티테넌트(타사 제공) 보안정책
- 테넌트별 API 키 분리(유출 시 blast radius 제한)
- 테넌트별 Origin allowlist 분리
- Standard/Pro 기능게이트는 키 권한으로 분리
- 관리자 키는 고객사 운영키와 물리적으로 분리

## 6) 즉시 실행 체크리스트
1. 운영 키 발급: `public`, `admin` 2종
2. 양 API 실행 스크립트에 키/리밋 인자 반영
3. 프록시/WAF에서 경로별 레이트 정책 적용
4. 24시간 트래픽 관찰 후 limit 미세조정
5. 7일 내 key rotation runbook 확정
6. 정책 알림 스크립트 실행: `py -3 scripts/tenant_policy_notify.py`
7. 차단 복구는 runbook 순서대로 단건 적용: `py -3 scripts/tenant_policy_recovery.py --tenant-id <tenant_id> --apply`
8. 월간 리허설 실행: `py -3 scripts/monthly_security_rehearsal.py`
9. 월간 리허설 작업 등록: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_monthly_security_rehearsal_task.ps1`

## 7) 현실적 한계와 보완
- 완전한 “해킹 0%”는 불가능하다.
- 목표는 `침입 난이도 상승 + 피해범위 축소 + 탐지시간 단축 + 복구시간 단축`이다.
- 본 변경은 앱 계층 최소 필수조건을 충족했고, 인프라 계층(WAF/Origin 차폐)까지 합쳐야 근본 대응이 완성된다.
