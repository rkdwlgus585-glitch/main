@echo off
REM [ROLE] REAL_LAUNCHER - confirmed-only site apply from verified audit targets
REM [GROUP] LISTING_PIPELINE
setlocal
cd /d "%~dp0.."

set "MODE=%~1"
set "RAW_ARGS=%*"
set "EXTRA_ARGS=%RAW_ARGS%"
if not "%MODE%"=="" (
    set "EXTRA_ARGS=%RAW_ARGS:* =%"
    if /i "%RAW_ARGS%"=="%MODE%" set "EXTRA_ARGS="
)

if /i "%MODE%"=="menu" goto menu
if /i "%MODE%"=="plan" goto plan
if /i "%MODE%"=="dry" goto dry
if /i "%MODE%"=="apply" goto apply
if /i "%MODE%"=="apply-all" goto apply_all
if /i "%MODE%"=="help" goto help
if "%MODE%"=="" goto menu

python scripts\republish_from_audit.py %RAW_ARGS%
goto done

:menu
echo.
echo [CONFIRMED PUBLISH MENU]
echo 1. Plan-only (traffic preflight)
echo 2. Dry-run (latest confirmed targets)
echo 3. Apply low-traffic batch (limit 20, delay 1.5s)
echo 4. Apply full confirmed targets (delay 1.0s)
echo 5. Exit
set /p MODE_CHOICE=Select [1/2/3/4/5]:
set "MODE_CHOICE=%MODE_CHOICE: =%"
set "MODE_CHOICE=%MODE_CHOICE:~0,1%"
if "%MODE_CHOICE%"=="1" goto plan
if "%MODE_CHOICE%"=="2" goto dry
if "%MODE_CHOICE%"=="3" goto apply
if "%MODE_CHOICE%"=="4" goto apply_all
goto done

:plan
python scripts\republish_from_audit.py --key-mode year --plan-only %EXTRA_ARGS%
goto done

:dry
python scripts\republish_from_audit.py --key-mode year --dry-run --delay-sec 0.1 %EXTRA_ARGS%
goto done

:apply
python scripts\republish_from_audit.py --key-mode year --delay-sec 1.5 --limit 20 %EXTRA_ARGS%
goto done

:apply_all
python scripts\republish_from_audit.py --key-mode year --delay-sec 1.0 %EXTRA_ARGS%
goto done

:help
echo.
echo [CONFIRMED PUBLISH HELP]
echo launchers\launch_confirmed_publish.bat [mode] [options]
echo.
echo modes:
echo   menu      interactive menu (default)
echo   plan      traffic preflight plan only (no requests)
echo   dry       dry-run on latest confirmed target file
echo   apply     low-traffic apply (limit 20, delay 1.5s)
echo   apply-all full apply (delay 1.0s)
echo.
echo examples:
echo   launchers\launch_confirmed_publish.bat plan
echo   launchers\launch_confirmed_publish.bat dry
echo   launchers\launch_confirmed_publish.bat apply --targets logs\reconcile_audit\affected_row_shift_20260224.json
echo   launchers\launch_confirmed_publish.bat apply-all --key-mode mp
goto done

:done
exit /b %errorlevel%
