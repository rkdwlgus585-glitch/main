@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_monthly_security_rehearsal_task.ps1 -RepoRoot "%cd%"
endlocal
