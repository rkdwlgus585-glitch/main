@echo off
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  우클릭 - 관리자 권한으로 실행 필요
    pause & exit /b 1
)
set S=%~dp0collect.py
for /f "tokens=*" %%i in ('where python 2^>nul') do set P=%%i
if "%P%"=="" for /f "tokens=*" %%i in ('where py 2^>nul') do set P=%%i
if "%P%"=="" (
    echo  [!] python/py 실행 파일을 찾을 수 없습니다.
    pause & exit /b 1
)
schtasks /delete /tn "G2B_Auto" /f >nul 2>&1
schtasks /create /tn "G2B_Auto" /tr "\"%P%\" \"%S%\" --non-interactive" /sc weekly /d MON /st 09:00 /f
if %errorlevel% equ 0 (echo  [OK] 매주 월요일 09:00 등록) else (echo  [!] 실패)
pause
