@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/actual batch
:: [GROUP] LISTING_PIPELINE
setlocal
call "%~dp0launchers\launch_consult_match_scheduler.bat" %*
exit /b %errorlevel%
