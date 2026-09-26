# ☁️ Cloud Private

Hệ thống lưu trữ cá nhân với giao thức HTTP + TCP kết hợp.

## 🚀 Tính năng

- ✅ Upload mọi loại file (không giới hạn)
- ✅ Tạo thư mục, quản lý file
- ✅ Giao thức TCP upload siêu nhanh
- ✅ Checksum SHA-256 đảm bảo không mất file
- ✅ Chunked upload (chia nhỏ file để upload)
- ✅ Drag & Drop
- ✅ Không cần tạo tài khoản
- ✅ Giao diện đẹp, responsive

## 📋 Yêu cầu

- Python 3.7+
- Trình duyệt web hiện đại

## 🔧 Cài đặt & Chạy

### 1. Chạy Server

```bash
cd public
python server.py
```

Server sẽ khởi động:
- **HTTP**: http://localhost:8080
- **TCP**: localhost:9090

### 2. Mở Frontend

Có 2 cách:

**Cách 1**: Mở file `public/index.html` trực tiếp trong trình duyệt

**Cách 2**: Truy cập http://localhost:8080 (nếu server phục vụ static files)

### 3. Upload file qua TCP (siêu nhanh)

```bash
cd public
python tcp_client.py upload path/to/file.pdf /my_folder/
```

## 📡 Giao thức

### HTTP API

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/status` | GET | Kiểm tra trạng thái server |
| `/api/list?path=/` | GET | Liệt kê file trong thư mục |
| `/api/upload` | POST | Upload file (multipart) |
| `/api/download?path=/` | GET | Tải file |
| `/api/mkdir` | POST | Tạo thư mục |
| `/api/delete` | POST | Xóa file/thư mục |

### TCP Protocol

Giao thức TCP sử dụng length-prefixed JSON:

```
Client → Server: [4 bytes length][JSON header]
Server → Client: [4 bytes length][JSON response]
```

**Commands:**
- `upload`: Upload file với checksum verification
- `list`: Liệt kê file
- `ping`: Kiểm tra kết nối

### Upload Flow (TCP)

1. Client gửi header: `{cmd: "upload", filename, size, checksum, path}`
2. Server trả lời: `{status: "ready"}`
3. Client gửi file data theo chunks (1MB)
4. Server xác nhận từng chunk
5. Server verify SHA-256 checksum
6. Server atomic move file vào vị trí cuối cùng

## 🔒 Bảo mật file

- **Checksum SHA-256**: Mỗi file được tính hash trước khi upload
- **Atomic write**: File được ghi vào temp rồi rename (không bao giờ ghi đè trực tiếp)
- **Backup**: File cũ được backup trước khi ghi đè
- **Verify**: Server verify checksum sau khi nhận xong

## 📁 Cấu trúc

```
public/
├── server.py          # Python backend (HTTP + TCP)
├── tcp_client.py      # TCP client CLI
├── index.html         # Frontend thuần HTML/CSS/JS
└── cloud_storage/     # Thư mục lưu trữ file (tự động tạo)
```

## ⚙️ Cấu hình

Trong `server.py`:

```python
HTTP_PORT = 8080    # Cổng HTTP
TCP_PORT = 9090     # Cổng TCP
STORAGE_DIR = "./cloud_storage"  # Thư mục lưu trữ
CHUNK_SIZE = 1MB    # Kích thước chunk
MAX_FILE_SIZE = 10GB  # Giới hạn file
```

## 🛠️ TCP Client Commands

```bash
# Upload file
python tcp_client.py upload myfile.zip /documents/

# Liệt kê file
python tcp_client.py list /documents/

# Ping server
python tcp_client.py ping
```
