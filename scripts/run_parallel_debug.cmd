@echo off
:: [ROLE] OPS_RUNNER - parallel debug sweep maintenance job
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

set "PY_CMD="
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python launcher not found.
    exit /b 1
)

%PY_CMD% scripts\parallel_debug_all.py
exit /b %errorlevel%
