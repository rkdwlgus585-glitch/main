@echo off
:: [ROLE] OPS_RUNNER - daily quality gate and trend report maintenance job
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

if not exist logs mkdir logs

set "PY_CMD="
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python launcher not found. >> logs\quality_daily_scheduler.log
    exit /b 1
)

%PY_CMD% scripts\quality_gate_runner.py --quiet >> logs\quality_daily_scheduler.log 2>&1
set "QA_RC=%errorlevel%"

%PY_CMD% scripts\quality_trend_report.py --window-days 7 --quiet >> logs\quality_daily_scheduler.log 2>&1
set "TREND_RC=%errorlevel%"

if not "%QA_RC%"=="0" exit /b %QA_RC%
if not "%TREND_RC%"=="0" exit /b %TREND_RC%
exit /b 0
