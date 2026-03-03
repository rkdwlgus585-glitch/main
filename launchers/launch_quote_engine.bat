@echo off
:: [ROLE] REAL_LAUNCHER - runs quote_engine with passthrough args
setlocal
cd /d "%~dp0.."
python quote_engine.py %*
