@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/actual batch
:: [GROUP] BLOG_CONTENT
setlocal
call "%~dp0launchers\launch_premium_auto.bat" %*
exit /b %errorlevel%
