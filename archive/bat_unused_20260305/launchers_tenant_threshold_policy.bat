@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\enforce_tenant_threshold_policy.py --strict --apply-registry
endlocal
