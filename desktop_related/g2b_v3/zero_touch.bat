@echo off
chcp 65001 >nul 2>&1
title Zero Touch Revenue

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
%PYTHON% zero_touch_revenue.py --monthly-goal 200000 --continue-on-error

if %errorlevel% neq 0 (
    echo.
    echo  [!] Zero-touch run finished with errors. Check result/zero_touch_ops_latest.md
)
pause
