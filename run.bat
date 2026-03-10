@echo off
chcp 65001 >nul 2>nul
cd /d "%~dp0"

echo ================================================================
echo SeoulMNA Automation Runner
echo ================================================================
echo.
echo   1. all            (매물 수집/반영 파이프라인)
echo   2. maemul         (매물 링크 HTML 생성)
echo   3. match          (상담-매물 매칭)
echo   4. premium        (프리미엄 글 자동화)
echo   5. blog-cli       (블로그 자동발행 1회 실행)
echo   6. notice-monthly (월별 공지 초안 생성)
echo   7. notice-archive (월별 공지 누적 갱신)
echo   8. help
echo   9. exit
echo.
set /p choice="Select (1-9): "

if "%choice%"=="1" python ..\ALL\run.py all
if "%choice%"=="2" python ..\ALL\run.py maemul
if "%choice%"=="3" python ..\ALL\run.py match
if "%choice%"=="4" python ..\ALL\run.py premium
if "%choice%"=="5" python ..\ALL\run.py blog-cli
if "%choice%"=="6" python ..\ALL\run.py notice-monthly
if "%choice%"=="7" python ..\ALL\run.py notice-archive --min-uid 7684
if "%choice%"=="8" python ..\ALL\run.py help
if "%choice%"=="9" exit /b 0

echo.
pause
