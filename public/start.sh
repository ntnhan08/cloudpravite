#!/bin/bash

# Cloud Private - Auto Start Script
# Tự động kiểm tra, cài đặt và chạy server

clear

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ☁️  CLOUD PRIVATE - AUTO START                         ║"
echo "║  HTTP + TCP Unified Protocol                            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Kiểm tra Python
echo "[1/4] Đang kiểm tra Python..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "✅ Python3 đã sẵn sàng"
    $PYTHON_CMD --version
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo "✅ Python đã sẵn sàng"
    $PYTHON_CMD --version
else
    echo "❌ Python chưa được cài đặt!"
    echo ""
    echo "Vui lòng cài Python:"
    echo "  - Ubuntu/Debian: sudo apt install python3"
    echo "  - macOS: brew install python3"
    echo "  - Windows: https://www.python.org/downloads/"
    echo ""
    read -p "Nhấn Enter để thoát..."
    exit 1
fi
echo ""

# Tạo thư mục storage
echo "[2/4] Đang tạo thư mục lưu trữ..."
if [ ! -d "cloud_storage" ]; then
    mkdir -p cloud_storage
    echo "✅ Đã tạo thư mục cloud_storage"
else
    echo "✅ Thư mục cloud_storage đã tồn tại"
fi
echo ""

# Kiểm tra server.py
echo "[3/4] Đang kiểm tra server.py..."
if [ ! -f "server.py" ]; then
    echo "❌ Không tìm thấy server.py!"
    echo ""
    read -p "Nhấn Enter để thoát..."
    exit 1
fi
echo "✅ server.py đã sẵn sàng"
echo ""

# Mở trình duyệt
echo "[4/4] Đang mở trình duyệt..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:8080 2>/dev/null &
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8080 2>/dev/null &
    elif command -v gnome-open &> /dev/null; then
        gnome-open http://localhost:8080 2>/dev/null &
    fi
fi
echo "✅ Đã mở trình duyệt"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "  🚀 Đang khởi động server..."
echo "  📁 Storage: $(pwd)/cloud_storage"
echo "  🌐 URL: http://localhost:8080"
echo "  🔌 Port: 8080 (HTTP + TCP unified)"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Nhấn Ctrl+C để dừng server"
echo ""

# Chạy server
$PYTHON_CMD server.py

echo ""
echo "Server đã dừng."
