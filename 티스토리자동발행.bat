@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/tistory publish launcher
:: [GROUP] BLOG_CONTENT
setlocal
call "%~dp0launchers\launch_tistory_publish.bat" %*
exit /b %errorlevel%
