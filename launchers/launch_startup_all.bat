@echo off
:: [ROLE] REAL_LAUNCHER - unified startup runner (WP + Tistory + sheet/site watchdog)
:: [GROUP] BLOG_CONTENT
setlocal
cd /d "%~dp0.."
set "SMOKE_PY=scripts/show_entrypoints.py"

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\run_startup_all.ps1" -RepoRoot "%cd%"
set "RC=%errorlevel%"
exit /b %RC%
