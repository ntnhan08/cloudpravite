@echo off
title Cloud Private Server

echo.
echo ================================================================
echo   CLOUD PRIVATE - AUTO START
echo   HTTP + TCP Unified Protocol
echo ================================================================
echo.

REM Kiem tra Python
echo [1/4] Dang kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat!
    echo.
    echo Vui long cai Python tu: https://www.python.org/downloads/
    echo.
    echo Nhan phim bat ky de thoat...
    pause >nul
    exit /b 1
)

python --version
echo [OK] Python da san sang
echo.

REM Tao thu muc storage
echo [2/4] Dang tao thu muc luu tru...
if not exist "cloud_storage" (
    mkdir "cloud_storage"
    echo [OK] Da tao thu muc cloud_storage
) else (
    echo [OK] Thu muc cloud_storage da ton tai
)
echo.

REM Kiem tra server.py
echo [3/4] Dang kiem tra server.py...
if not exist "server.py" (
    echo [ERROR] Khong tim thay server.py!
    echo.
    echo Nhan phim bat ky de thoat...
    pause >nul
    exit /b 1
)
echo [OK] server.py da san sang
echo.

REM Mo trinh duyet
echo [4/4] Dang mo trinh duyet...
start http://localhost:8080
echo [OK] Da mo trinh duyet
echo.

echo ================================================================
echo   [START] Dang khoi dong server...
echo   [STORAGE] %cd%\cloud_storage
echo   [URL] http://localhost:8080
echo   [PORT] 8080 (HTTP + TCP unified)
echo ================================================================
echo.
echo   Nhan Ctrl+C de dung server
echo.

REM Chay server
python server.py

echo.
echo Server da dung.
pause
