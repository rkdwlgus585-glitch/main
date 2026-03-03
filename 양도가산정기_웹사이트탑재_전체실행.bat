@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"

echo.
echo ============================================
echo   YANGDO WEBSITE RELEASE
echo ============================================
echo 1. Test-only (no publish)
echo 2. Publish (customer/acquisition WR_ID optional: blank=auto)
echo.
set "MODE=1"
set /p MODE=Select mode (1/2): 

if "%MODE%"=="2" goto PUBLISH_MODE

echo.
echo [TEST MODE] Running simulation only...
%PY% scripts\deploy_yangdo_site_release.py --report logs/yangdo_site_release_latest.json
echo.
echo Done. Report: logs\yangdo_site_release_latest.json
pause
exit /b %errorlevel%

:PUBLISH_MODE
echo.
set "C_WRID="
set /p C_WRID=Enter customer WR_ID (blank=auto): 
for /f "tokens=* delims= " %%A in ("%C_WRID%") do set "C_WRID=%%A"
if not defined C_WRID set "C_WRID=0"
echo %C_WRID%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo [STOP] customer WR_ID must be numeric.
  pause
  exit /b 1
)

set "C_BOARD=yangdo_ai"
set /p C_BOARD_IN=Enter customer board slug (default yangdo_ai): 
if not "%C_BOARD_IN%"=="" set "C_BOARD=%C_BOARD_IN%"

set "A_WRID=0"
set /p A_WRID_IN=Enter acquisition WR_ID (blank to skip): 
if not "%A_WRID_IN%"=="" set "A_WRID=%A_WRID_IN%"
for /f "tokens=* delims= " %%A in ("%A_WRID%") do set "A_WRID=%%A"
if not defined A_WRID set "A_WRID=0"
echo %A_WRID%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo [STOP] acquisition WR_ID must be numeric when provided.
  pause
  exit /b 1
)

set "A_BOARD=yangdo_ai_ops"
set /p A_BOARD_IN=Enter acquisition board slug (default yangdo_ai_ops): 
if not "%A_BOARD_IN%"=="" set "A_BOARD=%A_BOARD_IN%"

echo.
echo [PUBLISH MODE] Deploying...
%PY% scripts\deploy_yangdo_site_release.py --publish --customer-board "%C_BOARD%" --customer-wr-id %C_WRID% --acquisition-board "%A_BOARD%" --acquisition-wr-id %A_WRID% --report logs/yangdo_site_release_latest.json
echo.
echo Done. Report: logs\yangdo_site_release_latest.json
pause
exit /b %errorlevel%
