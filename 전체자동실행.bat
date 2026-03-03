@echo off
:: [ROLE] ROOT_SHIM - forwards to unified startup launcher (all jobs together)
setlocal
call "%~dp0launchers\launch_startup_all.bat" %*
exit /b %errorlevel%
