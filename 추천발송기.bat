@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/actual batch
:: [GROUP] LISTING_PIPELINE
setlocal
call "%~dp0launchers\launch_listing_matcher.bat" %*
exit /b %errorlevel%
