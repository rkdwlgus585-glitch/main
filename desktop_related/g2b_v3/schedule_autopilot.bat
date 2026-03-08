@echo off
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Run as Administrator to register scheduler task.
    pause & exit /b 1
)

set S=%~dp0autopilot.py
for /f "tokens=*" %%i in ('where python 2^>nul') do set P=%%i
if "%P%"=="" for /f "tokens=*" %%i in ('where py 2^>nul') do set P=%%i
if "%P%"=="" (
    echo  [!] python/py executable not found.
    pause & exit /b 1
)

schtasks /delete /tn "G2B_Autopilot" /f >nul 2>&1
schtasks /create /tn "G2B_Autopilot" /tr "\"%P%\" \"%S%\" --continue-on-error" /sc weekly /d MON /st 09:30 /f
if %errorlevel% equ 0 (
    echo  [OK] Registered weekly G2B_Autopilot at MON 09:30
) else (
    echo  [!] Failed to register task
)
pause
