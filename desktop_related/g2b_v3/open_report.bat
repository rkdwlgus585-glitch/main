@echo off
chcp 65001 >nul 2>&1
set REPORT=%~dp0result\zero_touch_infographic_report.html

if not exist "%REPORT%" (
    echo [!] Report not found: %REPORT%
    pause
    exit /b 1
)

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "%REPORT%"
    exit /b 0
)

if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" "%REPORT%"
    exit /b 0
)

if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" "%REPORT%"
    exit /b 0
)

if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files\Microsoft\Edge\Application\msedge.exe" "%REPORT%"
    exit /b 0
)

echo [!] Could not find Chrome/Edge executable. Opening with default app...
start "" "%REPORT%"
