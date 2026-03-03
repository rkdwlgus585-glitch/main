@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/actual batch
:: [GROUP] DOCUMENT_AUTOMATION
setlocal
call "%~dp0launchers\launch_gabji.bat" %*
exit /b %errorlevel%
