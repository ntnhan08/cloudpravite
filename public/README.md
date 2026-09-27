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
- ✅ **Không dùng framework** - HTML/CSS/JS thuần + Python

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
- Không cần build tool (Vite, Webpack, etc.)

## 📋 Yêu cầu

- Python 3.7+
- Trình duyệt web hiện đại
- Node.js (chỉ để chạy build script đơn giản)

## 🔧 Cài đặt & Chạy

### 1. Build (optional - chỉ copy files)

```bash
npm run build
```

Hoặc đơn giản copy files thủ công:
```bash
mkdir -p dist
cp index.html dist/
cp public/* dist/
```

### 2. Chạy Server

```bash
cd dist
python server.py
```

Server sẽ chạy:
- **Unified Port**: 8080 (cả HTTP + TCP)
- **Storage**: ./cloud_storage/

### 3. Mở Frontend

Mở `dist/index.html` trong trình duyệt. Frontend kết nối qua HTTP đến cùng port 8080.

### 4. Upload qua TCP (Fast Upload)

```bash
cd dist
python tcp_client.py upload myfile.zip /documents/
python tcp_client.py list /documents/
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
├── build.js            # Build script đơn giản (copy files)
├── package.json        # Chỉ có script build
├── public/
│   ├── server.py       # Backend Python (unified HTTP+TCP)
│   ├── tcp_client.py   # TCP client CLI
│   └── README.md       # Tài liệu này
└── dist/               # Output sau khi build
    ├── index.html
    ├── server.py
    ├── tcp_client.py
    └── README.md
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
- **Không lock-in**: Không phụ thuộc vào bất kỳ framework nào

## 📝 License

MIT
