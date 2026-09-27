@echo off
chcp 65001 >nul
title Cloud Private - Install Dependencies

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║  ☁️  CLOUD PRIVATE - INSTALL DEPENDENCIES               ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

echo [1/3] Đang kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python chưa được cài đặt!
    echo.
    echo Vui lòng cài Python từ: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
python --version
echo ✅ Python OK
echo.

echo [2/3] Đang kiểm tra pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  pip chưa có, đang cài đặt...
    python -m ensurepip --upgrade
)
echo ✅ pip OK
echo.

echo [3/3] Đang cài đặt dependencies...
echo.
echo ℹ️  Server sử dụng Python standard library - KHÔNG CẦN cài thêm gì!
echo.
echo Nếu muốn cài optional packages:
echo   pip install -r requirements.txt
echo.
echo ✅ Sẵn sàng chạy server!
echo.
echo Chạy: start.bat
echo.
pause
