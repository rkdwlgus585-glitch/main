@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\tenant_usage_billing_report.py --strict
endlocal
