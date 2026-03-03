@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/calculator autodrive(stop mode)
:: [GROUP] CALCULATOR_AUTODRIVE
setlocal
call "%~dp0launchers\launch_calculator_autodrive.bat" stop
exit /b %errorlevel%
