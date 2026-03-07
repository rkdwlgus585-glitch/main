@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PY=py -3"
where py >nul 2>&1
if errorlevel 1 set "PY=python"

echo.
echo [SeoulMNA 보안 스택 전체 자동 설정]
echo - API 키 부트스트랩
echo - 보안 API 스택 기동
echo - 시작프로그램/감시 태스크 등록
echo - 보안 워치독 1회 실행
echo - Cloudflare baseline 적용(자격증명 있을 때)
echo.

%PY% scripts/security_do_all.py
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo [완료] 보안 스택 자동 설정 성공
) else (
  echo [주의] 일부 단계 실패. logs/security_do_all_latest.json 확인
)
pause
exit /b %RC%

