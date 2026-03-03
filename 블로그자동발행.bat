@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/blog launcher(startup-once hidden mode)
:: [GROUP] BLOG_CONTENT
setlocal
call "%~dp0launchers\launch_blog.bat" startup-once
exit /b %errorlevel%
