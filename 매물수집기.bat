@echo off
REM [ROLE] ROOT_SHIM - listing pipeline user entrypoint
REM [GROUP] LISTING_PIPELINE
setlocal
cd /d "%~dp0"
call "%~dp0launchers\launch_listing_pipeline.bat" %*
set "RC=%errorlevel%"
pause
exit /b %RC%
