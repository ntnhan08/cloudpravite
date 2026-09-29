# ☁️ Cloud Private - Unified Protocol

Hệ thống lưu trữ cá nhân với **HTTP + TCP kết hợp trên CÙNG 1 PORT**.

## 🚀 Tính năng

- ✅ **Unified Port**: HTTP + TCP trên cùng port 8080
- ✅ Upload mọi loại file (không giới hạn)
- ✅ Tạo thư mục, quản lý file
- ✅ TCP upload siêu nhanh (không overhead HTTP)
- ✅ Checksum SHA-256 đảm bảo không mất file
- ✅ Chunked upload (chia nhỏ file)
- ✅ Drag & Drop
- ✅ Không cần tạo tài khoản
- ✅ Auto-detect protocol
- ✅ **One-click start** - Nhấn là chạy!

## ⚡ Quick Start (1 Click)

### Windows
```
Double-click: START.bat
```

### Linux / macOS
```bash
chmod +x START.sh
./START.sh
```

**Script sẽ tự động:**
1. ✅ Kiểm tra Python đã cài chưa
2. ✅ Tạo thư mục lưu trữ
3. ✅ Khởi động server
4. ✅ Mở trình duyệt

## 📋 Yêu cầu

- **Python 3.7+** (chỉ cần Python, không cần cài gì thêm!)
- Trình duyệt web hiện đại

## 🔧 Manual Start

Nếu không dùng one-click script:

```bash
cd public
python server.py
```

Sau đó mở `index.html` trong trình duyệt hoặc truy cập http://localhost:8080

## 📡 TCP Client (Fast Upload)

```bash
cd public

# Upload file qua TCP (siêu nhanh)
python tcp_client.py upload myfile.zip /documents/

# Liệt kê file
python tcp_client.py list /documents/

# Ping server
python tcp_client.py ping
```

## 🔌 Unified Protocol

Server chạy trên **1 port duy nhất** (mặc định 8080), tự động detect:

```
Client kết nối → Server peek 8 bytes đầu
  ├─ Bắt đầu bằng HTTP method (GET, POST...) → HTTP handler
  └─ Bắt đầu bằng length-prefixed JSON → TCP handler
```

**Ưu điểm:**
- Chỉ cần mở 1 port firewall
- Frontend và TCP client dùng cùng URL
- Không conflict port

## 📡 API Endpoints (HTTP)

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/status` | GET | Trạng thái server |
| `/api/list?path=/` | GET | Liệt kê file |
| `/api/upload` | POST | Upload file (multipart) |
| `/api/download?path=/` | GET | Tải file |
| `/api/mkdir` | POST | Tạo thư mục |
| `/api/delete` | POST | Xóa file/thư mục |

## 🔒 Đảm bảo không mất file

1. **Checksum SHA-256**: Tính hash trước khi upload
2. **Atomic write**: Ghi vào temp file → rename
3. **Backup**: File cũ backup trước khi ghi đè
4. **Verify**: Server verify checksum sau khi nhận

## 📁 Cấu trúc

```
├── START.bat             ← One-click start (Windows)
├── START.sh              ← One-click start (Linux/Mac)
├── index.html            ← Frontend HTML/CSS/JS thuần
├── build.js              ← Build script (optional)
├── package.json          ← Chỉ có script build
├── public/
│   ├── start.bat         ← Start script chi tiết (Windows)
│   ├── start.sh          ← Start script chi tiết (Linux/Mac)
│   ├── install.bat       ← Install script (Windows)
│   ├── install.sh        ← Install script (Linux/Mac)
│   ├── server.py         ← Backend Python (unified HTTP+TCP)
│   ├── tcp_client.py     ← TCP client CLI
│   ├── requirements.txt  ← Dependencies (không cần cài)
│   └── README.md         ← Tài liệu này
└── cloud_storage/        ← Thư mục lưu trữ (tự động tạo)
```

## ⚙️ Cấu hình

Trong `server.py`:

```python
PORT = 8080        # Unified port (HTTP + TCP)
STORAGE_DIR = "./cloud_storage"
CHUNK_SIZE = 1MB
MAX_FILE_SIZE = 10GB
```

## 🎯 Tại sao không dùng framework?

- **Nhẹ**: Không cần install hàng trăm MB dependencies
- **Nhanh**: Không cần build time
- **Đơn giản**: Chỉ cần Python + trình duyệt
- **Dễ deploy**: Copy files là chạy được
- **One-click**: Double-click là chạy
- **Không lock-in**: Không phụ thuộc vào bất kỳ framework nào

## 🐛 Troubleshooting

### Lỗi "Python chưa được cài đặt"
- Windows: Tải từ https://www.python.org/downloads/
- macOS: `brew install python3`
- Linux: `sudo apt install python3`

### Lỗi "Port 8080 đã được sử dụng"
- Đổi port trong `server.py`: `PORT = 9090`
- Hoặc tắt ứng dụng đang dùng port 8080

### Lỗi "Không kết nối được server"
- Kiểm tra server đang chạy
- Kiểm tra firewall không chặn port 8080
- Thử truy cập http://localhost:8080/api/status

## 📝 License

MIT
