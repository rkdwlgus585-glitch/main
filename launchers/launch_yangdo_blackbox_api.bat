@echo off
setlocal
cd /d %~dp0\..
py -3 yangdo_blackbox_api.py --host 0.0.0.0 --port 8790
endlocal
