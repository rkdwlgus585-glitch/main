@echo off
REM [ROLE] REAL_LAUNCHER - wr_20 admin memo restore from sheet basis
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
if /i "%MODE%"=="help" goto usage_info
if /i "%MODE%"=="usage" goto usage_info
if "%MODE%"=="" goto menu

python all.py %RAW_ARGS%
goto done

:menu
echo.
echo [ADMIN MEMO RESTORE MENU]
echo 1. Plan-only (traffic preflight)
echo 2. Dry-run (include non-raw, limit 30, pages 3)
echo 3. Apply low-traffic batch (limit 20, pages 3, delay 2.0s)
echo 4. Apply auto-resume (all pages, safe-limit+state, delay 1.8s)
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
python all.py --fix-admin-memo --fix-admin-memo-plan-only --fix-admin-memo-all --fix-admin-memo-pages 0 --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 %EXTRA_ARGS%
goto done

:dry
python all.py --fix-admin-memo --fix-admin-memo-dry-run --fix-admin-memo-all --fix-admin-memo-pages 3 --fix-admin-memo-limit 30 --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 %EXTRA_ARGS%
goto done

:apply
python all.py --fix-admin-memo --fix-admin-memo-all --fix-admin-memo-pages 3 --fix-admin-memo-limit 20 --fix-admin-memo-delay-sec 2.0 --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 %EXTRA_ARGS%
goto done

:apply_all
python all.py --fix-admin-memo --fix-admin-memo-all --fix-admin-memo-pages 0 --fix-admin-memo-limit 0 --fix-admin-memo-delay-sec 1.8 --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 %EXTRA_ARGS%
goto done

:usage_info
echo.
echo [ADMIN MEMO RESTORE HELP]
echo launchers\launch_admin_memo_restore.bat [mode] [options]
echo.
echo modes:
echo   menu      interactive menu (default)
echo   plan      traffic preflight plan only (no requests)
echo   dry       dry-run restore
echo   apply     low-traffic batch apply
echo   apply-all auto-resume apply (all pages, safe-limit + state)
echo.
echo examples:
echo   launchers\launch_admin_memo_restore.bat plan
echo   launchers\launch_admin_memo_restore.bat dry
echo   launchers\launch_admin_memo_restore.bat apply --fix-admin-memo-limit 10
echo   launchers\launch_admin_memo_restore.bat apply-all --fix-admin-memo-reset-state
goto done

:done
exit /b %errorlevel%


