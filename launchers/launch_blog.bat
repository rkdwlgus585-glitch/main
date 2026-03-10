@echo off
:: [ROLE] REAL_LAUNCHER - blog entrypoint (gui/auto/scheduler/status)
:: [GROUP] BLOG_CONTENT
setlocal
cd /d "%~dp0.."

set "MODE=%~1"
if /i "%MODE%"=="gui" goto gui
if /i "%MODE%"=="auto" goto auto_once
if /i "%MODE%"=="scheduler" goto scheduler
if /i "%MODE%"=="status" goto schedule_check
if /i "%MODE%"=="startup-once" goto startup_once

echo.
echo [BLOG LAUNCHER]
echo 1. Run blog generator GUI
echo 2. Publish once (--cli)
echo 3. Run auto-publish scheduler (--scheduler)
echo 4. Show current schedule (--schedule-check)
echo 5. Startup-once hidden run (once/day)
set /p MODE_CHOICE=Select mode [1/2/3/4/5]:
if "%MODE_CHOICE%"=="1" goto gui
if "%MODE_CHOICE%"=="2" goto auto_once
if "%MODE_CHOICE%"=="3" goto scheduler
if "%MODE_CHOICE%"=="4" goto schedule_check
if "%MODE_CHOICE%"=="5" goto startup_once

echo Invalid selection.
pause
exit /b 1

:gui
python ..\ALL\mnakr.py
goto done

:auto_once
python ..\ALL\mnakr.py --cli
goto done

:schedule_check
python ..\ALL\mnakr.py --schedule-check
goto done

:startup_once
call "%~dp0..\scripts\run_startup_blog_scheduler.cmd"
goto done

:scheduler
echo.
echo [AUTO-PUBLISH SCHEDULE]
python ..\ALL\mnakr.py --schedule-check
echo.
echo [RUN CONDITIONS]
echo 1. Keep this computer powered on.
echo 2. Keep this terminal window open.
echo 3. Disable sleep/hibernate during schedule window.
echo 4. Keep internet connection active.
echo 5. Ensure WP auth is valid (WP_USER+WP_APP_PASSWORD or WP_JWT_TOKEN).
echo.
python ..\ALL\mnakr.py --scheduler
goto done

:done
set "RC=%errorlevel%"
pause
exit /b %RC%
