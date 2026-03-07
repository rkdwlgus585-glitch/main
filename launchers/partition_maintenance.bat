@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\partition_maintenance.py --sync --restore-missing --relocate-site-temp --status
endlocal
