@echo off
REM [ROLE] ROOT_SHIM - monthly notice archive entrypoint
REM [GROUP] NOTICE_ARCHIVE
setlocal
cd /d "%~dp0"
call "%~dp0launchers\launch_monthly_notice_archive.bat" %*
set "RC=%errorlevel%"
pause
exit /b %RC%

