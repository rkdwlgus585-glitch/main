@echo off
:: [ROLE] REAL_LAUNCHER - calculator autodrive entrypoint (start/status/stop)
:: [GROUP] CALCULATOR_AUTODRIVE
setlocal
cd /d "%~dp0.."

set "MODE=%~1"
if /i "%MODE%"=="start" goto start
if /i "%MODE%"=="status" goto status
if /i "%MODE%"=="stop" goto stop

echo.
echo [CALCULATOR AUTODRIVE]
echo 1. Start autodrive loop (hidden, KR-only lock on)
echo 2. Show autodrive status
echo 3. Stop autodrive
set /p MODE_CHOICE=Select mode [1/2/3]:
if "%MODE_CHOICE%"=="1" goto start
if "%MODE_CHOICE%"=="2" goto status
if "%MODE_CHOICE%"=="3" goto stop

echo Invalid selection.
pause
exit /b 1

:start
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_calculator_autodrive_until_9am.ps1"
goto done

:status
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\show_calculator_autodrive_status.ps1"
goto done

:stop
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\stop_calculator_autodrive.ps1"
goto done

:done
set "RC=%errorlevel%"
pause
exit /b %RC%
