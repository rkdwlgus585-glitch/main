@echo off
chcp 65001 >nul 2>&1
title G2B_Auto Task Status

echo.
echo [i] 작업 스케줄러 상태 확인: G2B_Auto
echo.

schtasks /query /tn "G2B_Auto" /v /fo list
if %errorlevel% neq 0 (
    echo.
    echo [!] G2B_Auto 작업을 찾을 수 없습니다.
    echo     먼저 schedule.bat를 관리자 권한으로 실행하세요.
)

echo.
pause
