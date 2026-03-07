@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\monthly_security_rehearsal.py
endlocal
