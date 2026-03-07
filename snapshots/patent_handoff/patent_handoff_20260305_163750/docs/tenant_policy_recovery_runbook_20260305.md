# Tenant Policy Recovery Runbook (2026-03-05)

## 목표
- 정책 엔진이 `auto_disable` 또는 `auto_block_keys_on_disable`를 적용한 뒤,
  운영자가 안전하게 tenant를 복구할 수 있는 표준 절차를 제공한다.

## 기본 원칙
- 즉시 복구 금지: 원인 확인 없이 `enabled=true`로 되돌리지 않는다.
- 증거 보존: 복구 전 `tenant_policy_actions_latest.json`, `security_*_events.jsonl` 스냅샷 유지.
- 점진 복구: `preview` -> `single tenant apply` -> 트래픽 모니터링 순서 유지.

## 1) 사전 점검
1. 최신 정책 액션 확인  
`py -3 scripts/enforce_tenant_threshold_policy.py --strict --apply-registry`
2. 알림 발송 확인  
`py -3 scripts/tenant_policy_notify.py`
3. 보안 이벤트 확인  
`py -3 scripts/security_event_watchdog.py --lookback-min 60`

## 2) 복구 후보 조회 (Dry-run)
- 전체 disabled/blocked tenant 프리뷰  
`py -3 scripts/tenant_policy_recovery.py --all-disabled --with-blocked-keys`
- 결과 파일  
`logs/tenant_policy_recovery_latest.json`

## 3) 단건 복구 적용
- 단일 tenant 복구  
`py -3 scripts/tenant_policy_recovery.py --tenant-id <tenant_id> --apply`

동작:
- `enabled=true`
- `blocked_api_tokens=[]`
- `blocked_reason`, `blocked_at` 제거

## 4) 복구 후 검증
1. 온보딩 검증  
`py -3 scripts/validate_tenant_onboarding.py --strict`
2. API 경로 점검  
`py -3 scripts/tenant_usage_billing_report.py --strict`
3. 정책 재평가  
`py -3 scripts/enforce_tenant_threshold_policy.py --strict --apply-registry`
4. 알림 발송  
`py -3 scripts/tenant_policy_notify.py`

## 5) 롤백 기준
- 복구 후 30분 내 `auth_failed`, `auth_blocked_key`, `rate_limited` 급증 시:
1. 해당 tenant 즉시 재차단 (`enabled=false`, key block 재적용)
2. 원인 분석 완료 전 재복구 금지

## 6) 운영 자동화 연결
- `scripts/security_do_all.py`는 아래 순서로 정책 경로를 실행:
1. `tenant_usage_billing_report.py --strict`
2. `enforce_tenant_threshold_policy.py --strict --apply-registry`
3. `tenant_policy_notify.py`
