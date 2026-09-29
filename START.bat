@echo off
title Cloud Private - One Click Start

echo.
echo ================================================================
echo   CLOUD PRIVATE - ONE CLICK START
echo.
echo   Tu dong: Kiem tra - Cai dat - Chay - Mo trinh duyet
echo ================================================================
echo.

REM Chuyen den thu muc dist (sau khi build)
if exist "dist" (
    cd /d "%~dp0dist"
) else (
    REM Neu chua build, chuyen den public
    cd /d "%~dp0public"
)

REM Chay start.bat
if exist "start.bat" (
    call start.bat
) else (
    echo [ERROR] Khong tim thay start.bat
    echo Vui long chay: npm run build
    pause
)
