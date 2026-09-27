@echo off
chcp 65001 >nul
title Cloud Private Server

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║  ☁️  CLOUD PRIVATE - AUTO START                         ║
echo ║  HTTP + TCP Unified Protocol                            ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Kiểm tra Python
echo [1/4] Đang kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python chưa được cài đặt!
    echo.
    echo Vui lòng cài Python từ: https://www.python.org/downloads/
    echo.
    echo Nhấn phím bất kỳ để thoát...
    pause >nul
    exit /b 1
)

python --version
echo ✅ Python đã sẵn sàng
echo.

REM Tạo thư mục storage
echo [2/4] Đang tạo thư mục lưu trữ...
if not exist "cloud_storage" (
    mkdir "cloud_storage"
    echo ✅ Đã tạo thư mục cloud_storage
) else (
    echo ✅ Thư mục cloud_storage đã tồn tại
)
echo.

REM Kiểm tra server.py
echo [3/4] Đang kiểm tra server.py...
if not exist "server.py" (
    echo ❌ Không tìm thấy server.py!
    echo.
    echo Nhấn phím bất kỳ để thoát...
    pause >nul
    exit /b 1
)
echo ✅ server.py đã sẵn sàng
echo.

REM Mở trình duyệt
echo [4/4] Đang mở trình duyệt...
start http://localhost:8080
echo ✅ Đã mở trình duyệt
echo.

echo ═══════════════════════════════════════════════════════════
echo   🚀 Đang khởi động server...
echo   📁 Storage: %cd%\cloud_storage
echo   🌐 URL: http://localhost:8080
echo   🔌 Port: 8080 (HTTP + TCP unified)
echo ═══════════════════════════════════════════════════════════
echo.
echo   Nhấn Ctrl+C để dừng server
echo.

REM Chạy server
python server.py

echo.
echo Server đã dừng.
pause
