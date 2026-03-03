@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"

echo.
echo ============================================
echo   B-plan Masterpiece Deploy (GAS + co.kr)
echo ============================================
echo 1. Build+Deploy+Verify (recommended)
echo 2. Build+Deploy+Verify + write GAS URLs to .env
echo.
set "MODE=1"
set /p MODE=Select mode (1/2): 

set "GAS_EXEC="
set /p GAS_EXEC=Enter GAS exec URL (blank=use existing env/fallback): 

if "%MODE%"=="2" goto MODE2

echo.
%PY% scripts\deploy_b_plan_masterpiece.py --gas-exec-url "%GAS_EXEC%" --report logs\b_plan_masterpiece_latest.json
echo.
echo Done. Report: logs\b_plan_masterpiece_latest.json
pause
exit /b %errorlevel%

:MODE2
echo.
%PY% scripts\deploy_b_plan_masterpiece.py --gas-exec-url "%GAS_EXEC%" --persist-env --report logs\b_plan_masterpiece_latest.json
echo.
echo Done. Report: logs\b_plan_masterpiece_latest.json
pause
exit /b %errorlevel%
