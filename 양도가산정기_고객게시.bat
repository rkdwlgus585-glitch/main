@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"

echo.
echo [YANGDO CUSTOMER PUBLISH]
echo - Default board slug: yangdo_ai
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

set "BOARD=yangdo_ai"
set /p BOARD_IN=Enter board slug (default yangdo_ai): 
if not "%BOARD_IN%"=="" set "BOARD=%BOARD_IN%"

set "SUBJECT="
set /p SUBJECT=Enter subject (blank=default): 

echo.
echo [RUN] customer mode publish...
if "%SUBJECT%"=="" (
  %PY% all.py --publish-yangdo-page --yangdo-page-mode customer --yangdo-page-board-slug "%BOARD%" --yangdo-page-wr-id %WRID%
) else (
  %PY% all.py --publish-yangdo-page --yangdo-page-mode customer --yangdo-page-board-slug "%BOARD%" --yangdo-page-wr-id %WRID% --yangdo-page-subject "%SUBJECT%"
)

if errorlevel 1 (
  echo.
  echo [FAIL] Publish returned error.
  pause
  exit /b 1
)

echo.
echo [DONE] Customer page published/updated.
pause
exit /b 0
