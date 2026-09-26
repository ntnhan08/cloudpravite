#!/usr/bin/env python3
"""
TCP Client cho Cloud Private
Sử dụng để upload file qua TCP (siêu nhanh)

Cách dùng:
    python tcp_client.py upload <file_path> [remote_path]
    python tcp_client.py list [remote_path]
    python tcp_client.py ping
"""

import socket
import struct
import json
import hashlib
import os
import sys
import time

TCP_HOST = "localhost"
TCP_PORT = 9090
CHUNK_SIZE = 1024 * 1024  # 1MB


def send_json(sock, data):
    """Gửi JSON qua TCP với length prefix"""
    msg = json.dumps(data).encode()
    sock.sendall(struct.pack(">I", len(msg)) + msg)


def recv_json(sock):
    """Nhận JSON từ TCP"""
    length_data = recv_exact(sock, 4)
    if not length_data:
        return None
    length = struct.unpack(">I", length_data)[0]
    msg_data = recv_exact(sock, length)
    if not msg_data:
        return None
    return json.loads(msg_data.decode())


def recv_exact(sock, n):
    """Nhận chính xác n bytes"""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def calculate_checksum(filepath):
    """Tính SHA-256 checksum"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def upload_file(filepath, remote_path="/"):
    """Upload file qua TCP"""
    if not os.path.isfile(filepath):
        print(f"❌ File không tồn tại: {filepath}")
        return False
    
    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    
    print(f"📤 Đang upload: {filename}")
    print(f"   Kích thước: {file_size / 1024 / 1024:.2f} MB")
    print(f"   Đường dẫn: {remote_path}")
    
    # Tính checksum
    print("   Đang tính checksum...")
    checksum = calculate_checksum(filepath)
    print(f"   SHA-256: {checksum[:32]}...")
    
    # Kết nối TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    
    try:
        sock.connect((TCP_HOST, TCP_PORT))
        print(f"   ✅ Đã kết nối TCP server")
        
        # Gửi header
        send_json(sock, {
            "cmd": "upload",
            "filename": filename,
            "size": file_size,
            "checksum": checksum,
            "path": remote_path
        })
        
        # Chờ server sẵn sàng
        response = recv_json(sock)
        if not response or response.get("status") != "ready":
            print(f"   ❌ Server không sẵn sàng: {response}")
            return False
        
        print("   🚀 Đang truyền file...")
        
        # Gửi file data
        sent = 0
        start_time = time.time()
        last_progress = 0
        
        with open(filepath, "rb") as f:
            while sent < file_size:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                sock.sendall(data)
                sent += len(data)
                
                # Hiển thị progress
                progress = (sent / file_size) * 100
                if progress - last_progress >= 5:
                    elapsed = time.time() - start_time
                    speed = sent / elapsed / (1024 * 1024) if elapsed > 0 else 0
                    print(f"   ⏳ {progress:.1f}% - {speed:.1f} MB/s", end="\r")
                    last_progress = progress
                
                # Nhận progress update từ server (non-blocking)
                sock.setblocking(False)
                try:
                    server_msg = recv_json(sock)
                    if server_msg and server_msg.get("status") == "error":
                        print(f"\n   ❌ Lỗi: {server_msg.get('message')}")
                        return False
                except:
                    pass
                sock.setblocking(True)
        
        # Nhận kết quả cuối cùng
        sock.settimeout(30)
        final_response = recv_json(sock)
        
        elapsed = time.time() - start_time
        speed = file_size / elapsed / (1024 * 1024) if elapsed > 0 else 0
        
        if final_response and final_response.get("status") == "complete":
            print(f"\n   ✅ Upload thành công!")
            print(f"   📊 Tốc độ: {final_response.get('speed_mbps', speed):.1f} MB/s")
            print(f"   ⏱️  Thời gian: {final_response.get('elapsed_seconds', elapsed):.1f}s")
            print(f"   🔒 Checksum: {final_response.get('checksum', '')[:32]}...")
            print(f"   ✅ Checksum đã được xác minh!")
            return True
        else:
            print(f"\n   ❌ Upload thất bại: {final_response}")
            return False
    
    except ConnectionRefusedError:
        print(f"   ❌ Không kết nối được TCP server tại {TCP_HOST}:{TCP_PORT}")
        print(f"   💡 Hãy chạy server.py trước")
        return False
    except Exception as e:
        print(f"\n   ❌ Lỗi: {e}")
        return False
    finally:
        sock.close()


def list_files(remote_path="/"):
    """Liệt kê file qua TCP"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((TCP_HOST, TCP_PORT))
        send_json(sock, {"cmd": "list", "path": remote_path})
        response = recv_json(sock)
        
        if response and response.get("status") == "ok":
            files = response.get("files", [])
            print(f"\n📂 Nội dung: {remote_path}")
            print("-" * 60)
            for f in files:
                icon = "📁" if f["type"] == "folder" else "📄"
                size = f"{f['size'] / 1024:.1f} KB" if f.get("size") else "-"
                print(f"  {icon} {f['name']:<30} {size:>10}")
            print("-" * 60)
            print(f"  Tổng: {len(files)} mục")
        else:
            print(f"❌ Lỗi: {response}")
    except ConnectionRefusedError:
        print(f"❌ Không kết nối được TCP server tại {TCP_HOST}:{TCP_PORT}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        sock.close()


def ping():
    """Kiểm tra kết nối TCP"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        start = time.time()
        sock.connect((TCP_HOST, TCP_PORT))
        send_json(sock, {"cmd": "ping"})
        response = recv_json(sock)
        elapsed = (time.time() - start) * 1000
        
        if response and response.get("status") == "pong":
            print(f"✅ TCP Server OK - Ping: {elapsed:.1f}ms")
        else:
            print(f"❌ Response không hợp lệ: {response}")
    except ConnectionRefusedError:
        print(f"❌ Không kết nối được TCP server tại {TCP_HOST}:{TCP_PORT}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("TCP Client cho Cloud Private")
        print()
        print("Cách dùng:")
        print("  python tcp_client.py upload <file> [remote_path]")
        print("  python tcp_client.py list [remote_path]")
        print("  python tcp_client.py ping")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "upload":
        if len(sys.argv) < 3:
            print("❌ Thiếu đường dẫn file")
            sys.exit(1)
        filepath = sys.argv[2]
        remote_path = sys.argv[3] if len(sys.argv) > 3 else "/"
        success = upload_file(filepath, remote_path)
        sys.exit(0 if success else 1)
    
    elif command == "list":
        remote_path = sys.argv[2] if len(sys.argv) > 2 else "/"
        list_files(remote_path)
    
    elif command == "ping":
        ping()
    
    else:
        print(f"❌ Lệnh không hợp lệ: {command}")
        sys.exit(1)
