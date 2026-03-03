@echo off
REM [ROLE] ROOT_SHIM - confirmed-only site publish entrypoint
REM [GROUP] LISTING_PIPELINE
setlocal
cd /d "%~dp0"
call "%~dp0launchers\launch_confirmed_publish.bat" %*
set "RC=%errorlevel%"
pause
exit /b %RC%
