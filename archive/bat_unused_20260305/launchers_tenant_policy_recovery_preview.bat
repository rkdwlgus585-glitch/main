@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\tenant_policy_recovery.py --all-disabled --with-blocked-keys
endlocal
