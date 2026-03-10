@echo off
:: [ROLE] REAL_LAUNCHER - consult matcher scheduler loop
setlocal
cd /d "%~dp0.."
python ..\ALL\consult_match_scheduler.py --scheduler
pause
