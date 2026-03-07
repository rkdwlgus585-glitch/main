@echo off
setlocal
cd /d "%~dp0"
call launchers\tenant_onboarding_check.bat
endlocal
