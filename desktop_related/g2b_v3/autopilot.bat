@echo off
chcp 65001 >nul 2>&1
title G2B Autopilot

python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  [!] Python is required: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

cd /d "%~dp0"
%PYTHON% autopilot.py --continue-on-error

if %errorlevel% neq 0 (
    echo.
    echo  [!] Autopilot finished with errors. Check logs and result/next_actions_latest.md
)
pause
