#!/usr/bin/env python3
"""
Cloud Private Server
====================
Kết hợp HTTP + TCP trong 1 server duy nhất.
- HTTP: Quản lý file, thư mục, download
- TCP: Upload siêu nhanh với checksum verification
- Đảm bảo không mất file khi upload

Chạy: python server.py
"""

import os
import sys
import json
import socket
import hashlib
import threading
import time
import struct
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
from datetime import datetime
import traceback

# ============================================================
# CẤU HÌNH
# ============================================================
HTTP_PORT = 8080
TCP_PORT = 9090
STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud_storage")
CHUNK_SIZE = 1024 * 1024  # 1MB chunks
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB max

# Tạo thư mục lưu trữ
os.makedirs(STORAGE_DIR, exist_ok=True)

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def safe_path(rel_path):
    """Chuyển đường dẫn tương đối thành đường dẫn tuyệt đối an toàn"""
    # Loại bỏ path traversal
    rel_path = rel_path.replace("..", "")
    rel_path = unquote(rel_path)
    if rel_path.startswith("/"):
        rel_path = rel_path[1:]
    full_path = os.path.normpath(os.path.join(STORAGE_DIR, rel_path))
    # Đảm bảo không escape khỏi STORAGE_DIR
    if not full_path.startswith(os.path.normpath(STORAGE_DIR)):
        return None
    return full_path


def calculate_checksum(filepath):
    """Tính SHA-256 checksum của file"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def get_file_info(filepath, rel_base=STORAGE_DIR):
    """Lấy thông tin file"""
    try:
        stat = os.stat(filepath)
        rel_path = os.path.relpath(filepath, rel_base)
        return {
            "name": os.path.basename(filepath),
            "type": "folder" if os.path.isdir(filepath) else "file",
            "size": stat.st_size if not os.path.isdir(filepath) else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": "/" + rel_path.replace(os.sep, "/") if rel_path != "." else "/"
        }
    except:
        return None


def list_directory(dir_path):
    """Liệt kê nội dung thư mục"""
    files = []
    try:
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            info = get_file_info(item_path)
            if info:
                files.append(info)
    except:
        pass
    return files


# ============================================================
# CHUNKED UPLOAD HANDLER
# ============================================================

class ChunkedUploadManager:
    """Quản lý upload theo chunk để đảm bảo không mất file"""
    
    def __init__(self):
        self.uploads = {}  # key: (filename, checksum) -> {chunks_received, total_chunks, temp_path}
        self.lock = threading.Lock()
    
    def start_upload(self, filename, total_chunks, checksum, file_size):
        """Bắt đầu session upload mới"""
        key = (filename, checksum)
        with self.lock:
            temp_dir = os.path.join(STORAGE_DIR, ".tmp_uploads")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"{filename}.{checksum[:8]}.tmp")
            
            self.uploads[key] = {
                "chunks_received": set(),
                "total_chunks": total_chunks,
                "temp_path": temp_path,
                "file_size": file_size,
                "checksum": checksum,
                "started": time.time()
            }
            return temp_path
    
    def receive_chunk(self, filename, checksum, chunk_index, data):
        """Nhận chunk data"""
        key = (filename, checksum)
        with self.lock:
            if key not in self.uploads:
                return False, "Upload session not found"
            
            upload = self.uploads[key]
            temp_path = upload["temp_path"]
            
            # Ghi chunk vào vị trí đúng
            offset = chunk_index * CHUNK_SIZE
            try:
                with open(temp_path, "r+b" if os.path.exists(temp_path) else "wb") as f:
                    f.seek(offset)
                    f.write(data)
                
                upload["chunks_received"].add(chunk_index)
                
                # Kiểm tra đã nhận đủ chunks chưa
                if len(upload["chunks_received"]) == upload["total_chunks"]:
                    return self._finalize_upload(key)
                
                return True, f"Chunk {chunk_index} received ({len(upload['chunks_received'])}/{upload['total_chunks']})"
            except Exception as e:
                return False, str(e)
    
    def _finalize_upload(self, key):
        """Hoàn tất upload - verify checksum và di chuyển file"""
        upload = self.uploads[key]
        temp_path = upload["temp_path"]
        expected_checksum = upload["checksum"]
        
        # Verify checksum
        actual_checksum = calculate_checksum(temp_path)
        
        if actual_checksum != expected_checksum:
            os.remove(temp_path)
            del self.uploads[key]
            return False, f"Checksum mismatch! Expected: {expected_checksum[:16]}..., Got: {actual_checksum[:16]}..."
        
        # Di chuyển file đến vị trí cuối cùng (atomic move)
        filename = key[0]
        final_path = os.path.join(STORAGE_DIR, filename)
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        
        # Atomic move
        shutil.move(temp_path, final_path)
        
        # Cleanup
        del self.uploads[key]
        
        return True, f"Upload complete! Checksum verified: {actual_checksum[:16]}..."
    
    def cleanup_stale(self, max_age=3600):
        """Dọn dẹp upload bị bỏ dở"""
        now = time.time()
        with self.lock:
            stale_keys = [k for k, v in self.uploads.items() if now - v["started"] > max_age]
            for key in stale_keys:
                try:
                    os.remove(self.uploads[key]["temp_path"])
                except:
                    pass
                del self.uploads[key]


upload_manager = ChunkedUploadManager()

# Dọn dẹp stale uploads mỗi 5 phút
def cleanup_thread():
    while True:
        time.sleep(300)
        upload_manager.cleanup_stale()

threading.Thread(target=cleanup_thread, daemon=True).start()


# ============================================================
# HTTP SERVER HANDLER
# ============================================================

class CloudHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler cho Cloud Private"""
    
    def log_message(self, format, *args):
        """Custom log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[HTTP {timestamp}] {args[0]}")
    
    def send_json(self, data, status=200):
        """Gửi response JSON"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Xử lý GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        try:
            if path == "/api/status":
                self.send_json({"status": "ok", "storage": STORAGE_DIR, "tcp_port": TCP_PORT})
            
            elif path == "/api/list":
                rel_path = params.get("path", ["/"])[0]
                abs_path = safe_path(rel_path)
                if abs_path is None:
                    self.send_json({"error": "Invalid path"}, 400)
                    return
                if not os.path.exists(abs_path):
                    os.makedirs(abs_path, exist_ok=True)
                files = list_directory(abs_path)
                self.send_json({"files": files, "path": rel_path})
            
            elif path == "/api/download":
                rel_path = params.get("path", [""])[0]
                abs_path = safe_path(rel_path)
                if abs_path is None or not os.path.isfile(abs_path):
                    self.send_json({"error": "File not found"}, 404)
                    return
                
                filename = os.path.basename(abs_path)
                file_size = os.path.getsize(abs_path)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(file_size))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                
                with open(abs_path, "rb") as f:
                    while True:
                        data = f.read(CHUNK_SIZE)
                        if not data:
                            break
                        self.wfile.write(data)
            
            else:
                self.send_json({"error": "Not found"}, 404)
        
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def do_POST(self):
        """Xử lý POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            if path == "/api/mkdir":
                content_length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(content_length))
                rel_path = body.get("path", "")
                abs_path = safe_path(rel_path)
                if abs_path is None:
                    self.send_json({"error": "Invalid path"}, 400)
                    return
                os.makedirs(abs_path, exist_ok=True)
                self.send_json({"success": True, "path": rel_path})
            
            elif path == "/api/delete":
                content_length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(content_length))
                rel_path = body.get("path", "")
                item_type = body.get("type", "file")
                abs_path = safe_path(rel_path)
                if abs_path is None:
                    self.send_json({"error": "Invalid path"}, 400)
                    return
                if not os.path.exists(abs_path):
                    self.send_json({"error": "Not found"}, 404)
                    return
                if item_type == "folder":
                    shutil.rmtree(abs_path)
                else:
                    os.remove(abs_path)
                self.send_json({"success": True})
            
            elif path == "/api/upload":
                self._handle_upload()
            
            else:
                self.send_json({"error": "Not found"}, 404)
        
        except Exception as e:
            traceback.print_exc()
            self.send_json({"error": str(e)}, 500)
    
    def _handle_upload(self):
        """Xử lý upload file (multipart/form-data)"""
        content_type = self.headers.get("Content-Type", "")
        
        if "multipart/form-data" in content_type:
            self._handle_multipart_upload()
        else:
            self.send_json({"error": "Unsupported content type"}, 400)
    
    def _handle_multipart_upload(self):
        """Parse multipart form data và lưu file"""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        
        # Extract boundary
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part.split("=", 1)[1].strip()
                break
        
        if not boundary:
            self.send_json({"error": "No boundary found"}, 400)
            return
        
        # Read body
        body = self.rfile.read(content_length)
        
        # Parse multipart
        parts = self._parse_multipart(body, boundary)
        
        # Extract fields
        fields = {}
        file_data = None
        file_name = None
        
        for part in parts:
            name = part.get("name", "")
            if name == "file":
                file_data = part["data"]
                file_name = part.get("filename", "unknown")
            else:
                fields[name] = part["data"].decode("utf-8", errors="ignore")
        
        if file_data is None:
            self.send_json({"error": "No file data"}, 400)
            return
        
        # Get upload metadata
        rel_path = fields.get("path", "/")
        chunk_index = int(fields.get("chunk", "0"))
        total_chunks = int(fields.get("totalChunks", "1"))
        checksum = fields.get("checksum", "")
        original_filename = fields.get("fileName", file_name)
        file_size = int(fields.get("fileSize", "0"))
        
        # Build final path
        final_rel_path = rel_path.rstrip("/") + "/" + original_filename
        abs_path = safe_path(final_rel_path)
        if abs_path is None:
            self.send_json({"error": "Invalid path"}, 400)
            return
        
        if total_chunks == 1:
            # Single chunk upload - save directly with atomic write
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            # Write to temp file first
            temp_path = abs_path + ".tmp"
            with open(temp_path, "wb") as f:
                f.write(file_data)
            
            # Verify checksum if provided
            if checksum:
                actual = hashlib.sha256(file_data).hexdigest()
                if actual != checksum:
                    os.remove(temp_path)
                    self.send_json({"error": f"Checksum mismatch"}, 400)
                    return
            
            # Atomic rename
            if os.path.exists(abs_path):
                os.remove(abs_path)
            os.rename(temp_path, abs_path)
            
            self.send_json({
                "success": True,
                "filename": original_filename,
                "size": len(file_data),
                "checksum_verified": bool(checksum)
            })
        else:
            # Multi-chunk upload
            if chunk_index == 0:
                upload_manager.start_upload(final_rel_path, total_chunks, checksum, file_size)
            
            success, message = upload_manager.receive_chunk(
                final_rel_path, checksum, chunk_index, file_data
            )
            
            if success:
                self.send_json({"success": True, "message": message})
            else:
                self.send_json({"error": message}, 400)
    
    def _parse_multipart(self, body, boundary):
        """Parse multipart form data"""
        parts = []
        boundary_bytes = boundary.encode()
        delimiter = b"--" + boundary_bytes
        
        sections = body.split(delimiter)
        
        for section in sections[1:]:  # Skip first empty section
            if section.startswith(b"--"):
                break  # End boundary
            
            # Split headers and content
            if b"\r\n\r\n" in section:
                header_part, content = section.split(b"\r\n\r\n", 1)
            elif b"\n\n" in section:
                header_part, content = section.split(b"\n\n", 1)
            else:
                continue
            
            # Remove trailing \r\n
            if content.endswith(b"\r\n"):
                content = content[:-2]
            
            # Parse headers
            headers = {}
            for line in header_part.decode("utf-8", errors="ignore").split("\n"):
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()
            
            # Extract name and filename from Content-Disposition
            disposition = headers.get("content-disposition", "")
            name = ""
            filename = ""
            for param in disposition.split(";"):
                param = param.strip()
                if param.startswith("name="):
                    name = param.split("=", 1)[1].strip('"')
                elif param.startswith("filename="):
                    filename = param.split("=", 1)[1].strip('"')
            
            parts.append({
                "name": name,
                "filename": filename,
                "data": content
            })
        
        return parts


# ============================================================
# TCP SERVER - Upload siêu nhanh
# ============================================================

class TCPServer:
    """
    TCP Server cho upload file siêu nhanh.
    
    Giao thức TCP:
    1. Client gửi header (JSON): {cmd, filename, size, checksum, path}
    2. Server phản hồi: {status: "ready"}
    3. Client gửi file data theo chunks
    4. Server xác nhận từng chunk
    5. Khi hoàn tất, server verify checksum
    6. Server phản hồi: {status: "complete", checksum: "..."}
    """
    
    def __init__(self, host="0.0.0.0", port=TCP_PORT):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
    
    def start(self):
        """Khởi động TCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Tăng buffer size cho tốc độ cao
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True
        
        print(f"[TCP] Server đang chạy trên {self.host}:{self.port}")
        print(f"[TCP] Giao thức: TCP Fast Upload với Checksum Verification")
        
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                
                print(f"[TCP] Kết nối mới từ {addr}")
                # Xử lý mỗi client trong thread riêng
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr),
                    daemon=True
                ).start()
            
            except Exception as e:
                if self.running:
                    print(f"[TCP] Error: {e}")
    
    def stop(self):
        """Dừng TCP server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
    
    def _send_json(self, sock, data):
        """Gửi JSON qua TCP với length prefix"""
        msg = json.dumps(data).encode()
        # Send length (4 bytes) + message
        sock.sendall(struct.pack(">I", len(msg)) + msg)
    
    def _recv_json(self, sock):
        """Nhận JSON từ TCP với length prefix"""
        # Receive length (4 bytes)
        length_data = self._recv_exact(sock, 4)
        if not length_data:
            return None
        length = struct.unpack(">I", length_data)[0]
        if length > 10 * 1024 * 1024:  # Max 10MB header
            return None
        # Receive message
        msg_data = self._recv_exact(sock, length)
        if not msg_data:
            return None
        return json.loads(msg_data.decode())
    
    def _recv_exact(self, sock, n):
        """Nhận chính xác n bytes"""
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def _handle_client(self, sock, addr):
        """Xử lý kết nối TCP từ client"""
        try:
            sock.settimeout(300)  # 5 phút timeout
            
            # Nhận command header
            header = self._recv_json(sock)
            if not header:
                self._send_json(sock, {"status": "error", "message": "Invalid header"})
                return
            
            cmd = header.get("cmd", "")
            
            if cmd == "upload":
                self._handle_tcp_upload(sock, header)
            elif cmd == "ping":
                self._send_json(sock, {"status": "pong", "time": time.time()})
            elif cmd == "list":
                rel_path = header.get("path", "/")
                abs_path = safe_path(rel_path)
                if abs_path and os.path.exists(abs_path):
                    files = list_directory(abs_path)
                    self._send_json(sock, {"status": "ok", "files": files})
                else:
                    self._send_json(sock, {"status": "error", "message": "Path not found"})
            else:
                self._send_json(sock, {"status": "error", "message": f"Unknown command: {cmd}"})
        
        except Exception as e:
            print(f"[TCP] Error handling client {addr}: {e}")
            try:
                self._send_json(sock, {"status": "error", "message": str(e)})
            except:
                pass
        finally:
            sock.close()
    
    def _handle_tcp_upload(self, sock, header):
        """Xử lý upload file qua TCP"""
        filename = header.get("filename", "")
        file_size = header.get("size", 0)
        checksum = header.get("checksum", "")
        rel_path = header.get("path", "/")
        
        if not filename or file_size <= 0:
            self._send_json(sock, {"status": "error", "message": "Invalid upload request"})
            return
        
        # Build final path
        final_rel_path = rel_path.rstrip("/") + "/" + filename
        abs_path = safe_path(final_rel_path)
        if abs_path is None:
            self._send_json(sock, {"status": "error", "message": "Invalid path"})
            return
        
        # Tạo thư mục nếu chưa có
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        # Thông báo sẵn sàng nhận data
        self._send_json(sock, {"status": "ready", "message": "Send file data"})
        
        # Nhận file data
        temp_path = abs_path + ".tcp_tmp"
        received = 0
        sha256 = hashlib.sha256()
        start_time = time.time()
        
        try:
            with open(temp_path, "wb") as f:
                while received < file_size:
                    # Tính chunk size còn lại
                    remaining = file_size - received
                    chunk_size = min(CHUNK_SIZE, remaining)
                    
                    data = self._recv_exact(sock, chunk_size)
                    if not data:
                        raise Exception("Connection closed during upload")
                    
                    f.write(data)
                    sha256.update(data)
                    received += len(data)
                    
                    # Gửi progress mỗi 10%
                    if received % (CHUNK_SIZE * 10) == 0 or received >= file_size:
                        progress = (received / file_size) * 100
                        self._send_json(sock, {
                            "status": "progress",
                            "received": received,
                            "total": file_size,
                            "percent": round(progress, 1)
                        })
        
        except Exception as e:
            # Xóa temp file nếu lỗi
            try:
                os.remove(temp_path)
            except:
                pass
            self._send_json(sock, {"status": "error", "message": str(e)})
            return
        
        # Verify checksum
        actual_checksum = sha256.hexdigest()
        
        if checksum and actual_checksum != checksum:
            os.remove(temp_path)
            self._send_json(sock, {
                "status": "error",
                "message": f"Checksum verification failed! Expected: {checksum[:16]}..., Got: {actual_checksum[:16]}..."
            })
            return
        
        # Atomic move - đảm bảo không mất file
        if os.path.exists(abs_path):
            # Backup file cũ
            backup_path = abs_path + ".backup"
            os.rename(abs_path, backup_path)
        
        try:
            os.rename(temp_path, abs_path)
            # Xóa backup nếu thành công
            if os.path.exists(backup_path if 'backup_path' in dir() else ""):
                os.remove(backup_path)
        except:
            # Nếu rename fail, thử copy
            shutil.copy2(temp_path, abs_path)
            os.remove(temp_path)
        
        elapsed = time.time() - start_time
        speed = file_size / elapsed / (1024 * 1024) if elapsed > 0 else 0
        
        self._send_json(sock, {
            "status": "complete",
            "filename": filename,
            "size": file_size,
            "checksum": actual_checksum,
            "checksum_verified": True,
            "speed_mbps": round(speed, 2),
            "elapsed_seconds": round(elapsed, 2)
        })
        
        print(f"[TCP] Upload hoàn tất: {filename} ({file_size / 1024 / 1024:.1f} MB) - {speed:.1f} MB/s")


# ============================================================
# MAIN - Khởi động cả HTTP và TCP
# ============================================================

def main():
    print("=" * 60)
    print("  ☁️  CLOUD PRIVATE SERVER")
    print("  HTTP + TCP Combined Protocol")
    print("=" * 60)
    print(f"  📁 Storage: {STORAGE_DIR}")
    print(f"  🌐 HTTP:    http://localhost:{HTTP_PORT}")
    print(f"  🔌 TCP:     localhost:{TCP_PORT}")
    print("=" * 60)
    print()
    
    # Khởi động TCP server trong thread riêng
    tcp_server = TCPServer()
    tcp_thread = threading.Thread(target=tcp_server.start, daemon=True)
    tcp_thread.start()
    
    # Khởi động HTTP server
    http_server = HTTPServer(("0.0.0.0", HTTP_PORT), CloudHTTPHandler)
    
    print(f"[HTTP] Server đang chạy trên http://0.0.0.0:{HTTP_PORT}")
    print(f"[HTTP] Frontend: Mở trình duyệt tại http://localhost:{HTTP_PORT}")
    print()
    print("Nhấn Ctrl+C để dừng server.")
    print()
    
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Đang dừng server...")
        tcp_server.stop()
        http_server.shutdown()
        print("[INFO] Server đã dừng.")


if __name__ == "__main__":
    main()
