@echo off
REM [ROLE] OPS_RUNNER - startup task: monthly notice archive refresh
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if not exist logs mkdir logs
set "LOG_FILE=logs\startup_notice_archive.log"
set "LOCK_DIR=logs\notice_archive.lock"

if not defined NOTICE_ARCHIVE_PAGES set "NOTICE_ARCHIVE_PAGES=12"
if not defined NOTICE_ARCHIVE_MIN_UID set "NOTICE_ARCHIVE_MIN_UID=7684"
if not defined NOTICE_ARCHIVE_MAX_WRITES set "NOTICE_ARCHIVE_MAX_WRITES=2"
if not defined NOTICE_ARCHIVE_WRITE_BUFFER set "NOTICE_ARCHIVE_WRITE_BUFFER=12"
if not defined NOTICE_ARCHIVE_WRITE_DELAY_SEC set "NOTICE_ARCHIVE_WRITE_DELAY_SEC=1.5"
if not defined NOTICE_SYNC_MIN_UPDATE_DAYS set "NOTICE_SYNC_MIN_UPDATE_DAYS=7"
if not defined NOTICE_ARCHIVE_REVIEW_JSON set "NOTICE_ARCHIVE_REVIEW_JSON=logs\notice_archive_review_latest.json"
if not defined NOTICE_ARCHIVE_REVIEW_MD set "NOTICE_ARCHIVE_REVIEW_MD=logs\notice_archive_review_latest.md"
if not defined NOTICE_ARCHIVE_SCHEDULE_STATE set "NOTICE_ARCHIVE_SCHEDULE_STATE=logs\notice_archive_schedule_state.json"

echo. >>"%LOG_FILE%"
2>nul mkdir "%LOCK_DIR%"
if errorlevel 1 (
    echo [%date% %time%] SKIP notice-archive refresh lock-exists >>"%LOG_FILE%"
    exit /b 0
)

echo [%date% %time%] START notice-archive refresh >>"%LOG_FILE%"
set "PY_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 (
    set "PY_CMD=python"
    where python >nul 2>&1
    if errorlevel 1 (
        echo [%date% %time%] ERROR notice-archive python-runtime-missing >>"%LOG_FILE%"
        set "RC=9009"
        goto done
    )
)

%PY_CMD% scripts\plan_monthly_notice_archive_schedule.py --run-state-file %NOTICE_ARCHIVE_SCHEDULE_STATE% --mark-run >>"%LOG_FILE%" 2>&1
set "RC=!errorlevel!"
if "!RC!"=="10" (
    echo [%date% %time%] SKIP notice-archive refresh schedule-not-due >>"%LOG_FILE%"
    set "RC=0"
    goto done
)
if not "!RC!"=="0" (
    echo [%date% %time%] ERROR notice-archive schedule-check rc=!RC! >>"%LOG_FILE%"
    goto done
)

echo [%date% %time%] START notice-archive publish-pipeline >>"%LOG_FILE%"
%PY_CMD% scripts\run_monthly_notice_archive_publish_pipeline.py --pages %NOTICE_ARCHIVE_PAGES% --min-uid %NOTICE_ARCHIVE_MIN_UID% --review-json %NOTICE_ARCHIVE_REVIEW_JSON% --review-md %NOTICE_ARCHIVE_REVIEW_MD% --max-writes %NOTICE_ARCHIVE_MAX_WRITES% --write-buffer %NOTICE_ARCHIVE_WRITE_BUFFER% --delay-sec %NOTICE_ARCHIVE_WRITE_DELAY_SEC% --min-update-days %NOTICE_SYNC_MIN_UPDATE_DAYS% >>"%LOG_FILE%" 2>&1
set "RC=!errorlevel!"
echo [%date% %time%] END notice-archive publish-pipeline rc=!RC! >>"%LOG_FILE%"

:done
echo [%date% %time%] END notice-archive refresh rc=!RC! >>"%LOG_FILE%"

rmdir "%LOCK_DIR%" >nul 2>&1
exit /b !RC!
