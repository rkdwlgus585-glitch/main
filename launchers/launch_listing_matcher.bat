@echo off
:: [ROLE] REAL_LAUNCHER - listing matcher with passthrough args
setlocal
cd /d "%~dp0.."
python ..\ALL\listing_matcher.py %*
