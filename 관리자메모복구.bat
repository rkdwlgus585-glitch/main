@echo off
REM [ROLE] ROOT_SHIM - admin memo restore entrypoint
REM [GROUP] LISTING_PIPELINE
setlocal
cd /d "%~dp0"
call "%~dp0launchers\launch_admin_memo_restore.bat" %*
set "RC=%errorlevel%"
pause
exit /b %RC%
