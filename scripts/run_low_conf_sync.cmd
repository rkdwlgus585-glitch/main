@echo off
:: [ROLE] OPS_RUNNER - scheduled low-confidence sheet sync maintenance job
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

set "PY_CMD="
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python launcher not found. >> logs\price_low_conf_scheduler.log
    exit /b 1
)

%PY_CMD% ..\ALL\all.py --sync-low-confidence-sheet --low-limit 500 --low-recent-numbers 2000 --low-skip-reviewed >> logs\price_low_conf_scheduler.log 2>&1
exit /b %errorlevel%
