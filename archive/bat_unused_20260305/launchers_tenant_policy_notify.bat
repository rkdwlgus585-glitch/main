@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\tenant_policy_notify.py
endlocal
