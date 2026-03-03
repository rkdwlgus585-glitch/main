@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"

echo.
echo [AI ACQUISITION CALCULATOR PUBLISH]
echo - Default board slug: yangdo_ai_ops
echo.

set "WRID="
set /p WRID=Enter target WR_ID (required): 
for /f "tokens=* delims= " %%A in ("%WRID%") do set "WRID=%%A"
if not defined WRID (
  echo [STOP] WR_ID is required.
  pause
  exit /b 1
)
echo %WRID%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo [STOP] WR_ID must be numeric.
  pause
  exit /b 1
)

set "BOARD=yangdo_ai_ops"
set /p BOARD_IN=Enter board slug (default yangdo_ai_ops): 
if not "%BOARD_IN%"=="" set "BOARD=%BOARD_IN%"

set "SUBJECT="
set /p SUBJECT=Enter subject (blank=default): 

echo.
echo [RUN] acquisition page publish...
if "%SUBJECT%"=="" (
  %PY% scripts\deploy_yangdo_site_release.py --publish --skip-customer-publish --acquisition-board "%BOARD%" --acquisition-wr-id %WRID%
) else (
  %PY% scripts\deploy_yangdo_site_release.py --publish --skip-customer-publish --acquisition-board "%BOARD%" --acquisition-wr-id %WRID% --acquisition-subject "%SUBJECT%"
)

if errorlevel 1 (
  echo.
  echo [FAIL] Publish returned error.
  pause
  exit /b 1
)

echo.
echo [DONE] Acquisition page published/updated.
pause
exit /b 0
