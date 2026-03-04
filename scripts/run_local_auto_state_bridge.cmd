@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\local_auto_state_bridge.py --host 127.0.0.1 --port 18777 --data-file logs/local_auto_state.json
endlocal

