@echo off
:: [ROLE] REAL_LAUNCHER - runs gabji automation directly
setlocal
cd /d "%~dp0.."
set "PY_CMD="
where py >nul 2>&1
if %errorlevel%==0 set "PY_CMD=py -3"
if not defined PY_CMD (
    where python >nul 2>&1
    if %errorlevel%==0 set "PY_CMD=python"
)
if not defined PY_CMD (
    echo [ERROR] Python launcher not found.
    exit /b 1
)
%PY_CMD% gabji.py %*
exit /b %errorlevel%
