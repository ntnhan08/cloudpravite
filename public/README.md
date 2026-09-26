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

## 🔌 Unified Protocol

Server chạy trên **1 port duy nhất** (mặc định 8080), tự động detect:

```
Client kết nối → Server peek 8 bytes đầu
  ├─ Bắt đầu bằng "GET "/"POST "/... → HTTP handler
  └─ Bắt đầu bằng length-prefixed JSON → TCP handler
```

**Ưu điểm:**
- Chỉ cần mở 1 port firewall
- Frontend và TCP client dùng cùng URL
- Không conflict port

## 📋 Yêu cầu

- Python 3.7+
- Trình duyệt web hiện đại

## 🔧 Chạy Server

```bash
python server.py
```

Server sẽ chạy:
- **Unified Port**: 8080 (cả HTTP + TCP)
- **Storage**: ./cloud_storage/

## 🌐 Frontend (HTTP)

Mở `index.html` trong trình duyệt. Frontend kết nối qua HTTP đến cùng port 8080.

## 📡 TCP Client (Fast Upload)

```bash
# Upload file qua TCP (siêu nhanh)
python tcp_client.py upload myfile.zip /documents/

# Liệt kê file
python tcp_client.py list /documents/

# Ping server
python tcp_client.py ping
```

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
├── index.html          # Frontend HTML/CSS/JS thuần
├── public/
│   ├── server.py       # Backend Python (unified HTTP+TCP)
│   ├── tcp_client.py   # TCP client CLI
│   └── README.md       # Tài liệu này
└── cloud_storage/      # Thư mục lưu trữ (tự động tạo)
```

## ⚙️ Cấu hình

Trong `server.py`:

```python
PORT = 8080        # Unified port (HTTP + TCP)
STORAGE_DIR = "./cloud_storage"
CHUNK_SIZE = 1MB
MAX_FILE_SIZE = 10GB
```
