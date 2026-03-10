@echo off
:: [ROLE] REAL_LAUNCHER - tistory listing publish via browser automation
:: [GROUP] BLOG_CONTENT
setlocal
cd /d "%~dp0.."

set "REG=%~1"
if /i "%REG%"=="help" goto usage
if /i "%REG%"=="startup-once" goto startup_once

set "PY_CMD="
where py >nul 2>&1
if %errorlevel%==0 set "PY_CMD=py -3"
if not defined PY_CMD (
    where python >nul 2>&1
    if %errorlevel%==0 set "PY_CMD=python"
)
if not defined PY_CMD (
    echo [ERROR] Python launcher not found.
    pause
    exit /b 1
)

if not defined REG goto daily_mode
if /i "%REG%"=="daily" goto daily_mode

echo [INFO] publish start: registration=%REG%
%PY_CMD% ..\ALL\tistory_ops\run.py publish-listing --registration %REG% --open-browser --auto-login --interactive-login --login-wait-sec 300 --draft-policy discard --audit-tag launcher
goto after_run

:daily_mode
echo [INFO] daily-once publish start (sheet sequence, start 7540)
%PY_CMD% ..\ALL\tistory_ops\run.py daily-once --start-registration 7540 --audit-tag launcher_daily
goto after_run

:startup_once
echo [INFO] startup-once tistory daily runner
call "%~dp0..\scripts\run_startup_tistory_daily.cmd"

:after_run
set "RC=%errorlevel%"

if not "%RC%"=="0" (
    echo.
    echo [WARN] publish failed (rc=%RC%). Check logs\tistory_publish_audit\*.json
) else (
    echo.
    echo [OK] publish finished.
)

pause
exit /b %RC%

:usage
echo.
echo Usage:
echo   launchers\launch_tistory_publish.bat [registration^|daily^|startup-once]
echo Example:
echo   launchers\launch_tistory_publish.bat 7540
echo   launchers\launch_tistory_publish.bat daily
pause
exit /b 0
