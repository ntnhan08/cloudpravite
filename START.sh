#!/bin/bash

# Cloud Private - One Click Start (Linux/Mac)
# Tự động: Kiểm tra → Cài đặt → Chạy → Mở trình duyệt

clear

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ☁️  CLOUD PRIVATE - ONE CLICK START                    ║"
echo "║                                                         ║"
echo "║  Tự động: Kiểm tra → Cài đặt → Chạy → Mở trình duyệt   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Chuyển đến thư mục script
cd "$(dirname "$0")/public"

# Cấp quyền thực thi
chmod +x start.sh 2>/dev/null

# Chạy start.sh
./start.sh
