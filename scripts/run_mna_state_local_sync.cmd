@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist logs mkdir logs

set "PY_CMD=py -3"
where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [mna_state_local_sync] python runtime missing
        exit /b 9009
    )
    set "PY_CMD=python"
)

%PY_CMD% scripts\mna_state_local_sync.py --mode merge --headless --data-file logs/local_auto_state.json %*
set "RC=%errorlevel%"
exit /b %RC%
