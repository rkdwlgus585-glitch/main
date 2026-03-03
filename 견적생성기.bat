@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/actual batch
:: [GROUP] DOCUMENT_AUTOMATION
setlocal
call "%~dp0launchers\launch_quote_engine.bat" %*
exit /b %errorlevel%
