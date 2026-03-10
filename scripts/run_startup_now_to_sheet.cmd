@echo off
REM [ROLE] OPS_RUNNER - canonical nowmna -> Google Sheet -> seoul catchup runner
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if not exist logs mkdir logs
set "LOG_FILE=logs\startup_now_to_sheet.log"
set "LOCK_DIR=logs\now_to_sheet.lock"

if not defined NOW_TO_SHEET_MAX_RETRIES set "NOW_TO_SHEET_MAX_RETRIES=6"
if not defined NOW_TO_SHEET_RETRY_BASE_SEC set "NOW_TO_SHEET_RETRY_BASE_SEC=120"
if not defined NOW_TO_SHEET_RETRY_MAX_SEC set "NOW_TO_SHEET_RETRY_MAX_SEC=1800"
if not defined NOW_TO_SHEET_LOCK_STALE_MIN set "NOW_TO_SHEET_LOCK_STALE_MIN=120"
if not defined NOW_TO_SHEET_SKIP_UPLOAD set "NOW_TO_SHEET_SKIP_UPLOAD=0"
if not defined NOW_TO_SHEET_EXTRA_ARGS set "NOW_TO_SHEET_EXTRA_ARGS="
if not defined SCHEDULE_TARGET_HOURS set "SCHEDULE_TARGET_HOURS=12,18"
if not defined SCHEDULE_TARGET_HOUR set "SCHEDULE_TARGET_HOUR=18"

echo. >>"%LOG_FILE%"
set "LOCK_AGE_MIN=0"
if exist "%LOCK_DIR%" (
    for /f %%I in ('powershell -NoProfile -Command "$p=''%LOCK_DIR%''; if(-not (Test-Path -LiteralPath $p)){''0''} else {[int](((Get-Date)-(Get-Item -LiteralPath $p).LastWriteTime).TotalMinutes)}"') do set "LOCK_AGE_MIN=%%I"
    if not defined LOCK_AGE_MIN set "LOCK_AGE_MIN=0"
    set /a __lock_age=!LOCK_AGE_MIN!
    if !__lock_age! GEQ %NOW_TO_SHEET_LOCK_STALE_MIN% (
        for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "STALE_TS=%%I"
        if not defined STALE_TS set "STALE_TS=unknown"
        ren "%LOCK_DIR%" "now_to_sheet.lock.stale_!STALE_TS!" >nul 2>&1
        if exist "%LOCK_DIR%" (
            echo [%date% %time%] SKIP now-to-sheet sync lock-exists stale-rename-failed age=!LOCK_AGE_MIN!m >>"%LOG_FILE%"
            exit /b 0
        )
        echo [%date% %time%] INFO now-to-sheet stale-lock isolated age=!LOCK_AGE_MIN!m tag=!STALE_TS! >>"%LOG_FILE%"
    ) else (
        echo [%date% %time%] SKIP now-to-sheet sync lock-exists age=!LOCK_AGE_MIN!m >>"%LOG_FILE%"
        exit /b 0
    )
)

2>nul mkdir "%LOCK_DIR%"
if errorlevel 1 (
    echo [%date% %time%] SKIP now-to-sheet sync lock-create-failed >>"%LOG_FILE%"
    exit /b 0
)

set "PY_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [%date% %time%] ERROR now-to-sheet python-runtime-missing >>"%LOG_FILE%"
        set "RC=9009"
        goto done
    )
    set "PY_CMD=python"
)

set "ATTEMPT=0"
set "RC=1"
set "WAIT_SEC=%NOW_TO_SHEET_RETRY_BASE_SEC%"
REM Canonical policy:
REM - nowmna -> Google Sheet sync is always performed
REM - seoul upload is attempted only for rows with claim price (enforced in ..\ALL\all.py)
set "SYNC_ARGS=--scheduled-catchup --catchup-full-reconcile"
if /i "%NOW_TO_SHEET_SKIP_UPLOAD%"=="1" set "SYNC_ARGS=!SYNC_ARGS! --catchup-no-upload"
if not "%NOW_TO_SHEET_EXTRA_ARGS%"=="" (
    set "SYNC_ARGS=!SYNC_ARGS! %NOW_TO_SHEET_EXTRA_ARGS%"
)

:retry_loop
set /a ATTEMPT+=1
echo [%date% %time%] START now-to-sheet sync attempt=!ATTEMPT! args=!SYNC_ARGS! >>"%LOG_FILE%"
%PY_CMD% ..\ALL\all.py !SYNC_ARGS! >>"%LOG_FILE%" 2>&1
set "RC=!errorlevel!"
if "!RC!"=="0" goto done
if !ATTEMPT! GEQ %NOW_TO_SHEET_MAX_RETRIES% goto done

echo [%date% %time%] RETRY now-to-sheet sync rc=!RC! wait=!WAIT_SEC!s >>"%LOG_FILE%"
powershell -NoProfile -Command "Start-Sleep -Seconds !WAIT_SEC!" >nul 2>&1
set /a WAIT_SEC*=2
if !WAIT_SEC! GTR %NOW_TO_SHEET_RETRY_MAX_SEC% set "WAIT_SEC=%NOW_TO_SHEET_RETRY_MAX_SEC%"
goto retry_loop

:done
echo [%date% %time%] END now-to-sheet sync rc=!RC! attempts=!ATTEMPT! >>"%LOG_FILE%"
rmdir "%LOCK_DIR%" >nul 2>&1
if exist "%LOCK_DIR%" (
    for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "RELEASE_TS=%%I"
    if not defined RELEASE_TS set "RELEASE_TS=unknown"
    ren "%LOCK_DIR%" "now_to_sheet.lock.stale_release_!RELEASE_TS!" >nul 2>&1
    if exist "%LOCK_DIR%" (
        echo [%date% %time%] WARN now-to-sheet lock release failed >>"%LOG_FILE%"
    ) else (
        echo [%date% %time%] WARN now-to-sheet lock renamed due release failure >>"%LOG_FILE%"
    )
)
exit /b !RC!

