@echo off
chcp 65001 >nul 2>&1
title G2B Auto Scheduler
echo.
echo  [i] 레거시 등록파일입니다. schedule.bat(v3)로 위임합니다.
echo.
cd /d "%~dp0"
call schedule.bat
exit /b %errorlevel%
