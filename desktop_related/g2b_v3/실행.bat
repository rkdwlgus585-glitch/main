@echo off
chcp 65001 >nul 2>&1
title G2B Auto v3.0
echo.
echo  [i] 레거시 실행파일입니다. run.bat(v3)로 위임합니다.
echo.
cd /d "%~dp0"
call run.bat
exit /b %errorlevel%
