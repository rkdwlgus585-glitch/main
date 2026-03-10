@echo off
:: [ROLE] REAL_LAUNCHER - premium content generator
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0.."
python ..\ALL\premium_auto.py
pause
