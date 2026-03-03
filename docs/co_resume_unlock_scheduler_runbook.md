# CO 재개 플랜 (최종 승인 시에만 실행)

주의: 이 문서는 실행 계획입니다. 지금은 KR-only 유지 상태이므로 실행하지 않습니다.

## 0) 사전 확인
- `logs/kr_only_mode.lock` 파일이 존재하면 CO 반영이 모두 차단됩니다.
- 트래픽/캡 복구 여부를 먼저 확인합니다.

```powershell
py -3 scripts/wait_and_apply_hidden_main_banner.py --max-wait-minutes 30 --report logs/co_recovery_check_latest.json
```

## 1) 잠금 해제 (최종 승인 후)
```powershell
if (Test-Path logs/kr_only_mode.lock) { Remove-Item logs/kr_only_mode.lock -Force }
```

## 2) 계산기 배포 + CO 브리지 재연결
```powershell
py -3 scripts/deploy_yangdo_kr_banner_bridge.py --max-train-rows 260 --report logs/yangdo_co_resume_publish_latest.json
```

## 3) CO 내용관리 페이지 동기화
```powershell
py -3 scripts/deploy_co_content_pages.py --report logs/deploy_co_content_pages_resume_latest.json
```

## 4) 런타임 검증 (CO 포함)
```powershell
py -3 scripts/verify_calculator_runtime.py --allow-no-browser --report logs/verify_calculator_runtime_co_resume_latest.json
```

## 5) 스케줄러/워치독 복구
```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_mnakr_scheduler_watchdog_task.ps1
powershell -ExecutionPolicy Bypass -File scripts/register_ops_watchdog_startup_task.ps1
```

## 6) 롤백 (문제 시 즉시)
```powershell
New-Item -ItemType File -Path logs/kr_only_mode.lock -Force | Out-Null
py -3 scripts/deploy_yangdo_kr_banner_bridge.py --skip-co-publish --max-train-rows 260 --report logs/yangdo_kr_bridge_rollback_latest.json
```
