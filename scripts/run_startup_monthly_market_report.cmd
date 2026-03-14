@echo off
REM [ROLE] OPS_RUNNER - startup task: monthly market report refresh
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if not exist logs mkdir logs
set "LOG_FILE=logs\startup_monthly_market_report.log"
set "LOCK_DIR=logs\monthly_market_report.lock"

if not defined MONTHLY_MARKET_REPORT_SCHEDULE_STATE set "MONTHLY_MARKET_REPORT_SCHEDULE_STATE=logs\monthly_market_report_schedule_state.json"
if not defined MONTHLY_MARKET_REPORT_SOURCE_JSON set "MONTHLY_MARKET_REPORT_SOURCE_JSON=logs\monthly_notice_keyword_report_latest.json"
if not defined MONTHLY_MARKET_REPORT_OUTPUT_DIR set "MONTHLY_MARKET_REPORT_OUTPUT_DIR=output\monthly_market_report"
if not defined MONTHLY_MARKET_REPORT_STATE_FILE set "MONTHLY_MARKET_REPORT_STATE_FILE=logs\monthly_market_report_publish_state.json"
if not defined MONTHLY_MARKET_REPORT_REVIEW_JSON set "MONTHLY_MARKET_REPORT_REVIEW_JSON=logs\monthly_market_report_review_latest.json"
if not defined MONTHLY_MARKET_REPORT_REVIEW_MD set "MONTHLY_MARKET_REPORT_REVIEW_MD=logs\monthly_market_report_review_latest.md"

echo. >>"%LOG_FILE%"
2>nul mkdir "%LOCK_DIR%"
if errorlevel 1 (
    echo [%date% %time%] SKIP monthly-market-report lock-exists >>"%LOG_FILE%"
    exit /b 0
)

echo [%date% %time%] START monthly-market-report refresh >>"%LOG_FILE%"
set "PY_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 (
    set "PY_CMD=python"
    where python >nul 2>&1
    if errorlevel 1 (
        echo [%date% %time%] ERROR monthly-market-report python-runtime-missing >>"%LOG_FILE%"
        set "RC=9009"
        goto done
    )
)

%PY_CMD% scripts\plan_monthly_market_report_schedule.py --run-state-file %MONTHLY_MARKET_REPORT_SCHEDULE_STATE% --mark-run >>"%LOG_FILE%" 2>&1
set "RC=!errorlevel!"
if "!RC!"=="10" (
    echo [%date% %time%] SKIP monthly-market-report schedule-not-due >>"%LOG_FILE%"
    set "RC=0"
    goto done
)
if not "!RC!"=="0" (
    echo [%date% %time%] ERROR monthly-market-report schedule-check rc=!RC! >>"%LOG_FILE%"
    goto done
)

echo [%date% %time%] START monthly-market-report publish-pipeline >>"%LOG_FILE%"
%PY_CMD% scripts\run_monthly_market_report_publish_pipeline.py --report-json %MONTHLY_MARKET_REPORT_SOURCE_JSON% --output-dir %MONTHLY_MARKET_REPORT_OUTPUT_DIR% --state-file %MONTHLY_MARKET_REPORT_STATE_FILE% --review-report-json %MONTHLY_MARKET_REPORT_REVIEW_JSON% --review-report-md %MONTHLY_MARKET_REPORT_REVIEW_MD% >>"%LOG_FILE%" 2>&1
set "RC=!errorlevel!"
echo [%date% %time%] END monthly-market-report publish-pipeline rc=!RC! >>"%LOG_FILE%"

:done
echo [%date% %time%] END monthly-market-report refresh rc=!RC! >>"%LOG_FILE%"

rmdir "%LOCK_DIR%" >nul 2>&1
exit /b !RC!