@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/calculator autodrive(start mode)
:: [GROUP] CALCULATOR_AUTODRIVE
setlocal
call "%~dp0launchers\launch_calculator_autodrive.bat" start
exit /b %errorlevel%
