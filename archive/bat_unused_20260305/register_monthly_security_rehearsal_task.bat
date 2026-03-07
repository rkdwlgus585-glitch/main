@echo off
setlocal
cd /d "%~dp0"
call launchers\register_monthly_security_rehearsal_task.bat
endlocal
