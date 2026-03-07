@echo off
setlocal
if "%~1"=="" (
  echo Usage: tenant_policy_recovery_apply.bat ^<tenant_id^>
  exit /b 1
)
cd /d "%~dp0"
call launchers\tenant_policy_recovery_apply.bat %1
endlocal
