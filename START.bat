@echo off
title Cloud Private - One Click Start

echo.
echo ================================================================
echo   CLOUD PRIVATE - ONE CLICK START
echo.
echo   Tu dong: Kiem tra - Cai dat - Chay - Mo trinh duyet
echo ================================================================
echo.

REM Chuyen den thu muc public
cd /d "%~dp0public"

REM Chay start.bat
call start.bat
