#!/usr/bin/env python3
"""
Cloud Private Server - UNIFIED PROTOCOL
========================================
KẾT HỢP HTTP + TCP trên CÙNG 1 PORT DUY NHẤT.

Server tự động detect protocol từ bytes đầu tiên:
- HTTP request (GET, POST, PUT, DELETE...) → xử lý HTTP
- TCP custom (length-prefixed JSON) → xử lý TCP siêu nhanh

Chạy: python server.py
Port: 8080 (cả HTTP và TCP)
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
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
import traceback

# ============================================================
# CẤU HÌNH
# ============================================================
PORT = 8080  # SINGLE PORT cho cả HTTP và TCP
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
    rel_path = rel_path.replace("..", "")
    rel_path = unquote(rel_path)
    if rel_path.startswith("/"):
        rel_path = rel_path[1:]
    full_path = os.path.normpath(os.path.join(STORAGE_DIR, rel_path))
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
# CHUNKED UPLOAD MANAGER
# ============================================================

class ChunkedUploadManager:
    """Quản lý upload theo chunk để đảm bảo không mất file"""
    
    def __init__(self):
        self.uploads = {}
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
            
            offset = chunk_index * CHUNK_SIZE
            try:
                with open(temp_path, "r+b" if os.path.exists(temp_path) else "wb") as f:
                    f.seek(offset)
                    f.write(data)
                
                upload["chunks_received"].add(chunk_index)
                
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
        
        actual_checksum = calculate_checksum(temp_path)
        
        if actual_checksum != expected_checksum:
            os.remove(temp_path)
            del self.uploads[key]
            return False, f"Checksum mismatch!"
        
        filename = key[0]
        final_path = os.path.join(STORAGE_DIR, filename)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        
        shutil.move(temp_path, final_path)
        del self.uploads[key]
        
        return True, f"Upload complete! Checksum verified."
    
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

def cleanup_thread():
    while True:
        time.sleep(300)
        upload_manager.cleanup_stale()

threading.Thread(target=cleanup_thread, daemon=True).start()


# ============================================================
# UNIFIED SERVER - KẾT HỢP HTTP + TCP
# ============================================================

class UnifiedServer:
    """
    Server duy nhất lắng nghe trên 1 port, tự động detect protocol.
    
    Cách hoạt động:
    1. Peek 8 bytes đầu tiên của connection
    2. Nếu bắt đầu bằng HTTP method (GET, POST, PUT, DELETE, HEAD, OPTIONS) → HTTP handler
    3. Ngược lại → TCP custom protocol handler
    """
    
    HTTP_METHODS = [b"GET ", b"POST ", b"PUT ", b"DELETE ", b"HEAD ", b"OPTIONS "]
    
    def __init__(self, host="0.0.0.0", port=PORT):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
    
    def start(self):
        """Khởi động unified server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)
        self.running = True
        
        print(f"[SERVER] Unified server đang chạy trên port {self.port}")
        print(f"[SERVER] Tự động detect: HTTP + TCP trên cùng 1 port")
        print(f"[SERVER] Storage: {STORAGE_DIR}")
        
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                
                # Xử lý mỗi connection trong thread riêng
                threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, addr),
                    daemon=True
                ).start()
            
            except Exception as e:
                if self.running:
                    print(f"[SERVER] Error: {e}")
    
    def stop(self):
        """Dừng server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
    
    def _handle_connection(self, sock, addr):
        """Detect protocol và delegate đến handler phù hợp"""
        try:
            # Peek 8 bytes đầu để detect protocol
            sock.settimeout(5.0)
            peek_data = sock.recv(8, socket.MSG_PEEK)
            
            if not peek_data:
                sock.close()
                return
            
            # Detect HTTP
            is_http = any(peek_data.startswith(method) for method in self.HTTP_METHODS)
            
            if is_http:
                self._handle_http(sock, addr)
            else:
                self._handle_tcp(sock, addr)
        
        except Exception as e:
            try:
                sock.close()
            except:
                pass
    
    # ============================================================
    # HTTP HANDLER
    # ============================================================
    
    def _handle_http(self, sock, addr):
        """Xử lý HTTP request"""
        try:
            sock.settimeout(60.0)
            
            # Đọc request line và headers
            request_data = b""
            while b"\r\n\r\n" not in request_data:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                request_data += chunk
                if len(request_data) > 65536:  # Max header size
                    break
            
            if b"\r\n\r\n" not in request_data:
                self._send_http_error(sock, 400, "Bad Request")
                return
            
            header_end = request_data.index(b"\r\n\r\n")
            headers_raw = request_data[:header_end].decode("utf-8", errors="ignore")
            body_start = request_data[header_end + 4:]
            
            # Parse request line
            lines = headers_raw.split("\r\n")
            request_line = lines[0]
            parts = request_line.split(" ")
            if len(parts) < 2:
                self._send_http_error(sock, 400, "Bad Request")
                return
            
            method = parts[0]
            path = parts[1]
            
            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()
            
            # Đọc body nếu có
            content_length = int(headers.get("content-length", 0))
            body = body_start
            while len(body) < content_length:
                chunk = sock.recv(min(65536, content_length - len(body)))
                if not chunk:
                    break
                body += chunk
            
            # Route request
            self._route_http(sock, method, path, headers, body)
        
        except Exception as e:
            traceback.print_exc()
            try:
                self._send_http_error(sock, 500, str(e))
            except:
                pass
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _route_http(self, sock, method, path, headers, body):
        """Route HTTP request đến handler phù hợp"""
        parsed = urlparse(path)
        route = parsed.path
        params = parse_qs(parsed.query)
        
        try:
            if route == "/api/status":
                self._send_http_json(sock, 200, {
                    "status": "ok",
                    "protocol": "unified",
                    "storage": STORAGE_DIR,
                    "port": self.port
                })
            
            elif route == "/api/list" and method == "GET":
                rel_path = params.get("path", ["/"])[0]
                abs_path = safe_path(rel_path)
                if abs_path is None:
                    self._send_http_json(sock, 400, {"error": "Invalid path"})
                    return
                if not os.path.exists(abs_path):
                    os.makedirs(abs_path, exist_ok=True)
                files = list_directory(abs_path)
                self._send_http_json(sock, 200, {"files": files, "path": rel_path})
            
            elif route == "/api/download" and method == "GET":
                rel_path = params.get("path", [""])[0]
                abs_path = safe_path(rel_path)
                if abs_path is None or not os.path.isfile(abs_path):
                    self._send_http_json(sock, 404, {"error": "File not found"})
                    return
                
                filename = os.path.basename(abs_path)
                file_size = os.path.getsize(abs_path)
                
                response_headers = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: application/octet-stream\r\n"
                    f"Content-Disposition: attachment; filename=\"{filename}\"\r\n"
                    f"Content-Length: {file_size}\r\n"
                    f"Access-Control-Allow-Origin: *\r\n"
                    f"\r\n"
                )
                sock.sendall(response_headers.encode())
                
                with open(abs_path, "rb") as f:
                    while True:
                        data = f.read(CHUNK_SIZE)
                        if not data:
                            break
                        sock.sendall(data)
            
            elif route == "/api/upload" and method == "POST":
                self._handle_http_upload(sock, headers, body)
            
            elif route == "/api/mkdir" and method == "POST":
                data = json.loads(body)
                rel_path = data.get("path", "")
                abs_path = safe_path(rel_path)
                if abs_path is None:
                    self._send_http_json(sock, 400, {"error": "Invalid path"})
                    return
                os.makedirs(abs_path, exist_ok=True)
                self._send_http_json(sock, 200, {"success": True, "path": rel_path})
            
            elif route == "/api/delete" and method == "POST":
                data = json.loads(body)
                rel_path = data.get("path", "")
                item_type = data.get("type", "file")
                abs_path = safe_path(rel_path)
                if abs_path is None:
                    self._send_http_json(sock, 400, {"error": "Invalid path"})
                    return
                if not os.path.exists(abs_path):
                    self._send_http_json(sock, 404, {"error": "Not found"})
                    return
                if item_type == "folder":
                    shutil.rmtree(abs_path)
                else:
                    os.remove(abs_path)
                self._send_http_json(sock, 200, {"success": True})
            
            else:
                self._send_http_json(sock, 404, {"error": "Not found"})
        
        except Exception as e:
            traceback.print_exc()
            self._send_http_json(sock, 500, {"error": str(e)})
    
    def _handle_http_upload(self, sock, headers, body):
        """Xử lý HTTP multipart upload"""
        content_type = headers.get("content-type", "")
        
        if "multipart/form-data" not in content_type:
            self._send_http_json(sock, 400, {"error": "Unsupported content type"})
            return
        
        # Extract boundary
        boundary = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part.split("=", 1)[1].strip()
                break
        
        if not boundary:
            self._send_http_json(sock, 400, {"error": "No boundary found"})
            return
        
        # Parse multipart
        parts = self._parse_multipart(body, boundary)
        
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
            self._send_http_json(sock, 400, {"error": "No file data"})
            return
        
        rel_path = fields.get("path", "/")
        chunk_index = int(fields.get("chunk", "0"))
        total_chunks = int(fields.get("totalChunks", "1"))
        checksum = fields.get("checksum", "")
        original_filename = fields.get("fileName", file_name)
        file_size = int(fields.get("fileSize", "0"))
        
        final_rel_path = rel_path.rstrip("/") + "/" + original_filename
        abs_path = safe_path(final_rel_path)
        if abs_path is None:
            self._send_http_json(sock, 400, {"error": "Invalid path"})
            return
        
        if total_chunks == 1:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            temp_path = abs_path + ".tmp"
            with open(temp_path, "wb") as f:
                f.write(file_data)
            
            if checksum:
                actual = hashlib.sha256(file_data).hexdigest()
                if actual != checksum:
                    os.remove(temp_path)
                    self._send_http_json(sock, 400, {"error": "Checksum mismatch"})
                    return
            
            if os.path.exists(abs_path):
                os.remove(abs_path)
            os.rename(temp_path, abs_path)
            
            self._send_http_json(sock, 200, {
                "success": True,
                "filename": original_filename,
                "size": len(file_data),
                "checksum_verified": bool(checksum)
            })
        else:
            if chunk_index == 0:
                upload_manager.start_upload(final_rel_path, total_chunks, checksum, file_size)
            
            success, message = upload_manager.receive_chunk(
                final_rel_path, checksum, chunk_index, file_data
            )
            
            if success:
                self._send_http_json(sock, 200, {"success": True, "message": message})
            else:
                self._send_http_json(sock, 400, {"error": message})
    
    def _parse_multipart(self, body, boundary):
        """Parse multipart form data"""
        parts = []
        boundary_bytes = boundary.encode()
        delimiter = b"--" + boundary_bytes
        
        sections = body.split(delimiter)
        
        for section in sections[1:]:
            if section.startswith(b"--"):
                break
            
            if b"\r\n\r\n" in section:
                header_part, content = section.split(b"\r\n\r\n", 1)
            elif b"\n\n" in section:
                header_part, content = section.split(b"\n\n", 1)
            else:
                continue
            
            if content.endswith(b"\r\n"):
                content = content[:-2]
            
            headers = {}
            for line in header_part.decode("utf-8", errors="ignore").split("\n"):
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()
            
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
    
    def _send_http_json(self, sock, status, data):
        """Gửi HTTP JSON response"""
        body = json.dumps(data).encode()
        status_text = {200: "OK", 400: "Bad Request", 404: "Not Found", 500: "Internal Server Error"}.get(status, "OK")
        
        response = (
            f"HTTP/1.1 {status} {status_text}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            f"Access-Control-Allow-Headers: Content-Type\r\n"
            f"\r\n"
        ).encode() + body
        
        sock.sendall(response)
    
    def _send_http_error(self, sock, status, message):
        """Gửi HTTP error response"""
        self._send_http_json(sock, status, {"error": message})
    
    # ============================================================
    # TCP CUSTOM PROTOCOL HANDLER
    # ============================================================
    
    def _handle_tcp(self, sock, addr):
        """Xử lý TCP custom protocol"""
        try:
            sock.settimeout(300)
            
            # Nhận header (length-prefixed JSON)
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
        
        final_rel_path = rel_path.rstrip("/") + "/" + filename
        abs_path = safe_path(final_rel_path)
        if abs_path is None:
            self._send_json(sock, {"status": "error", "message": "Invalid path"})
            return
        
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        self._send_json(sock, {"status": "ready", "message": "Send file data"})
        
        temp_path = abs_path + ".tcp_tmp"
        received = 0
        sha256 = hashlib.sha256()
        start_time = time.time()
        
        try:
            with open(temp_path, "wb") as f:
                while received < file_size:
                    remaining = file_size - received
                    chunk_size = min(CHUNK_SIZE, remaining)
                    
                    data = self._recv_exact(sock, chunk_size)
                    if not data:
                        raise Exception("Connection closed during upload")
                    
                    f.write(data)
                    sha256.update(data)
                    received += len(data)
                    
                    if received % (CHUNK_SIZE * 10) == 0 or received >= file_size:
                        progress = (received / file_size) * 100
                        self._send_json(sock, {
                            "status": "progress",
                            "received": received,
                            "total": file_size,
                            "percent": round(progress, 1)
                        })
        
        except Exception as e:
            try:
                os.remove(temp_path)
            except:
                pass
            self._send_json(sock, {"status": "error", "message": str(e)})
            return
        
        actual_checksum = sha256.hexdigest()
        
        if checksum and actual_checksum != checksum:
            os.remove(temp_path)
            self._send_json(sock, {
                "status": "error",
                "message": "Checksum verification failed!"
            })
            return
        
        if os.path.exists(abs_path):
            backup_path = abs_path + ".backup"
            os.rename(abs_path, backup_path)
        
        try:
            os.rename(temp_path, abs_path)
            if 'backup_path' in locals() and os.path.exists(backup_path):
                os.remove(backup_path)
        except:
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
        
        print(f"[TCP] Upload: {filename} ({file_size / 1024 / 1024:.1f} MB) - {speed:.1f} MB/s")
    
    def _send_json(self, sock, data):
        """Gửi JSON qua TCP với length prefix"""
        msg = json.dumps(data).encode()
        sock.sendall(struct.pack(">I", len(msg)) + msg)
    
    def _recv_json(self, sock):
        """Nhận JSON từ TCP"""
        length_data = self._recv_exact(sock, 4)
        if not length_data:
            return None
        length = struct.unpack(">I", length_data)[0]
        if length > 10 * 1024 * 1024:
            return None
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


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  ☁️  CLOUD PRIVATE SERVER - UNIFIED PROTOCOL")
    print("  HTTP + TCP Combined on SINGLE PORT")
    print("=" * 60)
    print(f"  📁 Storage: {STORAGE_DIR}")
    print(f"  🔌 Port:    {PORT} (HTTP + TCP)")
    print("=" * 60)
    print()
    print("Server tự động detect protocol:")
    print("  • HTTP request → xử lý như web API")
    print("  • TCP custom → xử lý như fast upload")
    print()
    print("Frontend: Mở index.html trong trình duyệt")
    print("TCP CLI: python tcp_client.py upload <file> [path]")
    print()
    print("Nhấn Ctrl+C để dừng server.")
    print()
    
    server = UnifiedServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INFO] Đang dừng server...")
        server.stop()
        print("[INFO] Server đã dừng.")


if __name__ == "__main__":
    main()
