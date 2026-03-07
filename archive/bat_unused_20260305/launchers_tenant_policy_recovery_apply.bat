@echo off
setlocal
if "%~1"=="" (
  echo Usage: tenant_policy_recovery_apply.bat ^<tenant_id^>
  exit /b 1
)
cd /d "%~dp0.."
py -3 scripts\tenant_policy_recovery.py --tenant-id %1 --apply
endlocal
