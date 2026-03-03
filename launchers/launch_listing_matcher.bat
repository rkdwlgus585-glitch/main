@echo off
:: [ROLE] REAL_LAUNCHER - listing matcher with passthrough args
setlocal
cd /d "%~dp0.."
python listing_matcher.py %*
