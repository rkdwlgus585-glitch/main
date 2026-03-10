@echo off
REM [ROLE] REAL_LAUNCHER - monthly notice archive generator
REM [GROUP] NOTICE_ARCHIVE
setlocal
cd /d "%~dp0.."

python ..\ALL\run.py notice-monthly --monthly-archive %*
exit /b %errorlevel%

