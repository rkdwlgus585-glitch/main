@echo off
chcp 65001 >nul 2>&1
title G2B Auto v3.0

python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  [!] Python 필요: https://www.python.org/downloads/
        echo      설치시 "Add Python to PATH" 체크!
        pause
        exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

%PYTHON% -c "import openpyxl" >nul 2>&1
if %errorlevel% neq 0 (
    echo  openpyxl 설치중...
    %PYTHON% -m pip install openpyxl -q
)

cd /d "%~dp0"
%PYTHON% collect.py

if %errorlevel% neq 0 (
    echo.
    echo  오류 발생
)
pause
