@echo off
setlocal
cd /d "%~dp0.."
py -3 scripts\prepare_patent_handoff_bundle.py
endlocal
