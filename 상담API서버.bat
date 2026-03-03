@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"

echo.
echo [서울건설정보 상담 API 서버 시작]
echo - endpoint: /consult
echo - health  : /health
echo.

%PY% yangdo_consult_api.py --host 0.0.0.0 --port 8788

echo.
echo [종료] 상담 API 서버가 중지되었습니다.
pause
