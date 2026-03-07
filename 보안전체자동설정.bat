@echo off
setlocal
cd /d "%~dp0"
call launchers\launch_security_do_all.bat %*
endlocal
