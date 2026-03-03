@echo off
:: [ROLE] ROOT_SHIM - forwards to launchers/blog launcher(gui mode)
:: [GROUP] BLOG_CONTENT
setlocal
call "%~dp0launchers\launch_blog.bat" gui
exit /b %errorlevel%
