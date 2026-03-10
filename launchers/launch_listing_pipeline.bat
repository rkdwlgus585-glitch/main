@echo off
REM [ROLE] REAL_LAUNCHER - canonical listing pipeline launcher (collector + reconcile)
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
if /i "%MODE%"=="reconcile" goto reconcile_full
if /i "%MODE%"=="reconcile-sheet" goto reconcile_sheet
if /i "%MODE%"=="reconcile-menu" goto reconcile_menu
if /i "%MODE%"=="collect" goto run_default_args
if /i "%MODE%"=="default" goto run_default_args
if /i "%MODE%"=="help" goto help

python ..\ALL\all.py %RAW_ARGS%
goto done

:menu
echo.
echo [LISTING MENU]
echo 1. Default collector (all.py)
echo 2. Reconcile (sheet + seoul)
echo 3. Reconcile (sheet only, no seoul login)
set /p MODE_CHOICE=Select mode [1/2/3]:
set "MODE_CHOICE=%MODE_CHOICE: =%"
set "MODE_CHOICE=%MODE_CHOICE:~0,1%"
if "%MODE_CHOICE%"=="1" goto run_default
if "%MODE_CHOICE%"=="2" goto reconcile_full_menu
if "%MODE_CHOICE%"=="3" goto reconcile_sheet_menu
echo Invalid selection.
goto done

:run_default
python ..\ALL\all.py
goto done

:reconcile_full_menu
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0
goto done

:reconcile_sheet_menu
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0 --reconcile-sheet-only
goto done

:reconcile_menu
echo.
echo [RECONCILE MENU]
echo 1. Apply reconcile (sheet + seoul)
echo 2. Apply reconcile (sheet only, no seoul login)
echo 3. Dry-run reconcile (sheet + seoul)
echo 4. Dry-run reconcile (sheet only)
echo 5. Exit
set /p MODE_CHOICE=Select [1/2/3/4/5]:
set "MODE_CHOICE=%MODE_CHOICE: =%"
set "MODE_CHOICE=%MODE_CHOICE:~0,1%"
if "%MODE_CHOICE%"=="1" goto full_apply
if "%MODE_CHOICE%"=="2" goto sheet_apply
if "%MODE_CHOICE%"=="3" goto full_dry
if "%MODE_CHOICE%"=="4" goto sheet_dry
if "%MODE_CHOICE%"=="5" goto done
echo Invalid selection.
goto done

:full_apply
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0
goto done

:sheet_apply
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0 --reconcile-sheet-only
goto done

:full_dry
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0 --reconcile-dry-run
goto done

:sheet_dry
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0 --reconcile-sheet-only --reconcile-dry-run
goto done

:reconcile_full
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0 %EXTRA_ARGS%
goto done

:reconcile_sheet
python ..\ALL\all.py --reconcile-published --reconcile-seoul-pages 0 --reconcile-sheet-only %EXTRA_ARGS%
goto done

:run_default_args
python ..\ALL\all.py %EXTRA_ARGS%
goto done

:help
echo.
echo [LISTING PIPELINE HELP]
echo launchers\launch_listing_pipeline.bat [mode] [options]
echo.
echo modes:
echo   menu            interactive menu
echo   reconcile       reconcile apply (sheet + seoul)
echo   reconcile-sheet reconcile apply (sheet only)
echo   reconcile-menu  interactive reconcile menu
echo   collect/default same as default collector
echo.
echo examples:
echo   launchers\launch_listing_pipeline.bat
echo   launchers\launch_listing_pipeline.bat reconcile --reconcile-dry-run
echo   launchers\launch_listing_pipeline.bat reconcile-sheet --reconcile-status-only
goto done

:done
exit /b %errorlevel%
