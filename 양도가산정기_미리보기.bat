@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"

echo.
echo [1/2] Build customer HTML...
%PY% all.py --build-yangdo-page --yangdo-page-mode customer --yangdo-page-output output/yangdo_price_calculator_customer.html
if errorlevel 1 (
  echo.
  echo [FAIL] HTML build failed.
  pause
  exit /b 1
)

echo.
echo [2/2] Launch local preview server...
start "YANGDO_PREVIEW_SERVER" cmd /k "cd /d ""%~dp0"" && %PY% -m http.server 8877 --directory output"
timeout /t 2 >nul
start "" "http://127.0.0.1:8877/yangdo_price_calculator_customer.html"

echo.
echo [DONE] Browser opened.
echo - URL: http://127.0.0.1:8877/yangdo_price_calculator_customer.html
echo - To stop server: press Ctrl+C in the YANGDO_PREVIEW_SERVER window
pause
exit /b 0
