@echo off
REM [ROLE] OPS_RUNNER - startup task: tistory daily once publish
setlocal
cd /d "%~dp0.."

if not exist logs mkdir logs
set "LOG_FILE=logs\startup_tistory_daily_scheduler.log"

echo. >>"%LOG_FILE%"
echo [%date% %time%] START tistory startup-daily >>"%LOG_FILE%"
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%cd%\scripts\run_startup_tistory_daily.ps1" -RepoRoot "%cd%" -StartRegistration 7540 >>"%LOG_FILE%" 2>&1
set "RC=%errorlevel%"
echo [%date% %time%] END tistory startup-daily rc=%RC% >>"%LOG_FILE%"

exit /b %RC%
