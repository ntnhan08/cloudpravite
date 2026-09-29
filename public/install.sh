#!/bin/bash

# Cloud Private - Install Dependencies Script

clear

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ☁️  CLOUD PRIVATE - INSTALL DEPENDENCIES               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Kiểm tra Python
echo "[1/3] Đang kiểm tra Python..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
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
$PYTHON_CMD --version
echo "✅ Python OK"
echo ""

# Kiểm tra pip
echo "[2/3] Đang kiểm tra pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "⚠️  pip chưa có, đang cài đặt..."
    $PYTHON_CMD -m ensurepip --upgrade
fi
echo "✅ pip OK"
echo ""

# Cài đặt dependencies
echo "[3/3] Đang cài đặt dependencies..."
echo ""
echo "ℹ️  Server sử dụng Python standard library - KHÔNG CẦN cài thêm gì!"
echo ""
echo "Nếu muốn cài optional packages:"
echo "  pip install -r requirements.txt"
echo ""
echo "✅ Sẵn sàng chạy server!"
echo ""
echo "Chạy: ./start.sh"
echo ""
