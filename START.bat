@echo off
chcp 65001 >nul
title Cloud Private - One Click Start

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║  ☁️  CLOUD PRIVATE - ONE CLICK START                    ║
echo ║                                                         ║
echo ║  Tự động: Kiểm tra → Cài đặt → Chạy → Mở trình duyệt   ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Chuyển đến thư mục public
cd /d "%~dp0public"

REM Chạy start.bat
call start.bat
