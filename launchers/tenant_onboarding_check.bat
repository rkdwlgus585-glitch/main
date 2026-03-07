@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\validate_tenant_onboarding.py --strict
endlocal
