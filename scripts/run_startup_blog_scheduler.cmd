@echo off
REM [ROLE] OPS_RUNNER - startup task: seoulmna.kr blog publish once/day
setlocal
cd /d "%~dp0.."

if not exist logs mkdir logs
set "LOG_FILE=logs\startup_blog_scheduler.log"

echo. >>"%LOG_FILE%"
echo [%date% %time%] START blog startup-once >>"%LOG_FILE%"
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%cd%\scripts\run_startup_blog_once.ps1" -RepoRoot "%cd%" >>"%LOG_FILE%" 2>&1
set "RC=%errorlevel%"
echo [%date% %time%] END blog startup-once rc=%RC% >>"%LOG_FILE%"

exit /b %RC%
