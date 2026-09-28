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

# Chuyển đến thư mục dist (sau khi build)
if [ -d "dist" ]; then
    cd "$(dirname "$0")/dist"
else
    # Nếu chưa build, chuyển đến public
    cd "$(dirname "$0")/public"
fi

# Cấp quyền thực thi
chmod +x start.sh 2>/dev/null

# Chạy start.sh
if [ -f "start.sh" ]; then
    ./start.sh
else
    echo "[ERROR] Không tìm thấy start.sh"
    echo "Vui lòng chạy: npm run build"
    exit 1
fi
