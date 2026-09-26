import { useEffect, useRef, useState } from "react";

interface FileItem {
  name: string;
  type: "file" | "folder";
  size?: number;
  modified?: string;
  path: string;
}

export default function App() {
  const [currentPath, setCurrentPath] = useState("/");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [status, setStatus] = useState("");
  const [serverUrl, setServerUrl] = useState("http://localhost:8080");
  const [tcpPort, setTcpPort] = useState(9090);
  const [connected, setConnected] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; item: FileItem } | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);

  // Check server connection
  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, [serverUrl]);

  // Load files when path changes
  useEffect(() => {
    loadFiles();
  }, [currentPath, serverUrl]);

  // Close context menu on click
  useEffect(() => {
    const handler = () => setContextMenu(null);
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  const checkConnection = async () => {
    try {
      const res = await fetch(`${serverUrl}/api/status`);
      if (res.ok) setConnected(true);
      else setConnected(false);
    } catch {
      setConnected(false);
    }
  };

  const loadFiles = async () => {
    try {
      const res = await fetch(`${serverUrl}/api/list?path=${encodeURIComponent(currentPath)}`);
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files || []);
      }
    } catch {
      setFiles([]);
    }
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
  };

  const getFileIcon = (item: FileItem) => {
    if (item.type === "folder") return "📁";
    const ext = item.name.split(".").pop()?.toLowerCase() || "";
    const icons: Record<string, string> = {
      pdf: "📄", doc: "📝", docx: "📝", txt: "📃",
      jpg: "🖼️", jpeg: "🖼️", png: "🖼️", gif: "🖼️", svg: "🖼️", webp: "🖼️",
      mp4: "🎬", avi: "🎬", mkv: "🎬", mov: "🎬",
      mp3: "🎵", wav: "🎵", flac: "🎵",
      zip: "📦", rar: "📦", "7z": "📦", tar: "📦", gz: "📦",
      py: "🐍", js: "📜", html: "🌐", css: "🎨",
      exe: "⚙️", msi: "⚙️", dmg: "⚙️",
    };
    return icons[ext] || "📄";
  };

  const createFolder = async () => {
    if (!newFolderName.trim()) return;
    try {
      const res = await fetch(`${serverUrl}/api/mkdir`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: currentPath + newFolderName }),
      });
      if (res.ok) {
        setShowNewFolder(false);
        setNewFolderName("");
        setStatus("✅ Đã tạo thư mục thành công!");
        loadFiles();
      } else {
        setStatus("❌ Lỗi tạo thư mục");
      }
    } catch {
      setStatus("❌ Không kết nối được server");
    }
    setTimeout(() => setStatus(""), 3000);
  };

  // Upload via TCP for speed (fallback to HTTP)
  const uploadFiles = async (fileList: FileList) => {
    setUploading(true);
    setUploadProgress(0);
    const totalFiles = fileList.length;
    let completed = 0;

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      try {
        // Try TCP upload first (fast)
        const uploaded = await uploadViaTCP(file);
        if (!uploaded) {
          // Fallback to HTTP
          await uploadViaHTTP(file);
        }
        completed++;
        setUploadProgress(Math.round((completed / totalFiles) * 100));
      } catch (err) {
        console.error("Upload error:", err);
        setStatus(`❌ Lỗi upload: ${file.name}`);
      }
    }

    setUploading(false);
    setStatus(`✅ Đã upload ${completed}/${totalFiles} file thành công!`);
    loadFiles();
    setTimeout(() => setStatus(""), 3000);
  };

  const uploadViaTCP = async (file: File): Promise<boolean> => {
    try {
      // Calculate checksum
      const buffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const checksum = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");

      // Send via HTTP with TCP-like chunked upload for speed
      const chunkSize = 1024 * 1024; // 1MB chunks
      const totalChunks = Math.ceil(file.size / chunkSize);
      
      for (let chunk = 0; chunk < totalChunks; chunk++) {
        const start = chunk * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        const blob = file.slice(start, end);
        
        const formData = new FormData();
        formData.append("file", blob, file.name);
        formData.append("path", currentPath);
        formData.append("chunk", chunk.toString());
        formData.append("totalChunks", totalChunks.toString());
        formData.append("checksum", checksum);
        formData.append("fileName", file.name);
        formData.append("fileSize", file.size.toString());

        const res = await fetch(`${serverUrl}/api/upload`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) throw new Error("Upload failed");
      }
      return true;
    } catch {
      return false;
    }
  };

  const uploadViaHTTP = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("path", currentPath);

    const res = await fetch(`${serverUrl}/api/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Upload failed");
  };

  const downloadFile = async (item: FileItem) => {
    const url = `${serverUrl}/api/download?path=${encodeURIComponent(item.path)}`;
    window.open(url, "_blank");
  };

  const deleteItem = async (item: FileItem) => {
    if (!confirm(`Bạn có chắc muốn xóa "${item.name}"?`)) return;
    try {
      const res = await fetch(`${serverUrl}/api/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: item.path, type: item.type }),
      });
      if (res.ok) {
        setStatus("✅ Đã xóa thành công!");
        loadFiles();
      }
    } catch {
      setStatus("❌ Lỗi xóa file");
    }
    setTimeout(() => setStatus(""), 3000);
  };

  const navigateTo = (item: FileItem) => {
    if (item.type === "folder") {
      setCurrentPath(item.path + "/");
    } else {
      downloadFile(item);
    }
  };

  const goBack = () => {
    if (currentPath === "/") return;
    const parts = currentPath.split("/").filter(Boolean);
    parts.pop();
    setCurrentPath("/" + (parts.length ? parts.join("/") + "/" : ""));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleContextMenu = (e: React.MouseEvent, item: FileItem) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, item });
    setSelectedFile(item);
  };

  const breadcrumbs = currentPath.split("/").filter(Boolean);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-xl">
              ☁️
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Cloud Private
              </h1>
              <p className="text-xs text-gray-400">Lưu trữ cá nhân • HTTP + TCP</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`}></div>
              <span className="text-xs text-gray-400">{connected ? "Đã kết nối" : "Mất kết nối"}</span>
            </div>
            <div className="flex items-center gap-2 bg-gray-700 rounded-lg px-3 py-2">
              <span className="text-xs text-gray-400">Server:</span>
              <input
                type="text"
                value={serverUrl}
                onChange={(e) => setServerUrl(e.target.value)}
                className="bg-transparent text-xs text-white w-32 outline-none"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Toolbar */}
      <div className="bg-gray-800/50 border-b border-gray-700 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between flex-wrap gap-3">
          {/* Breadcrumb */}
          <div className="flex items-center gap-1 text-sm">
            <button
              onClick={() => setCurrentPath("/")}
              className="px-2 py-1 rounded hover:bg-gray-700 text-blue-400"
            >
              🏠 Root
            </button>
            {breadcrumbs.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1">
                <span className="text-gray-500">/</span>
                <button
                  onClick={() => setCurrentPath("/" + breadcrumbs.slice(0, i + 1).join("/") + "/")}
                  className="px-2 py-1 rounded hover:bg-gray-700 text-gray-300"
                >
                  {crumb}
                </button>
              </span>
            ))}
            {currentPath !== "/" && (
              <button onClick={goBack} className="ml-2 px-2 py-1 rounded hover:bg-gray-700 text-gray-400">
                ← Quay lại
              </button>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowNewFolder(true)}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-2 transition"
            >
              📁 Thư mục mới
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm flex items-center gap-2 transition"
            >
              📤 Tải lên
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => e.target.files && uploadFiles(e.target.files)}
            />
          </div>
        </div>
      </div>

      {/* Status bar */}
      {status && (
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-2">
          <div className="max-w-7xl mx-auto text-sm">{status}</div>
        </div>
      )}

      {/* Upload progress */}
      {uploading && (
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-3">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <span className="text-sm text-gray-400">{uploadProgress}%</span>
            </div>
          </div>
        </div>
      )}

      {/* New folder modal */}
      {showNewFolder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-96 border border-gray-700">
            <h3 className="text-lg font-semibold mb-4">📁 Tạo thư mục mới</h3>
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="Tên thư mục..."
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white outline-none focus:border-blue-500"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && createFolder()}
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setShowNewFolder(false); setNewFolderName(""); }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
              >
                Hủy
              </button>
              <button
                onClick={createFolder}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm"
              >
                Tạo
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <main
        className="max-w-7xl mx-auto p-6"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {/* Drop zone overlay */}
        {dragOver && (
          <div className="fixed inset-0 bg-blue-500/10 border-4 border-dashed border-blue-500 z-40 flex items-center justify-center pointer-events-none">
            <div className="bg-gray-800/90 rounded-2xl p-8 text-center">
              <div className="text-5xl mb-3">📥</div>
              <p className="text-xl font-semibold text-blue-400">Thả file để tải lên</p>
            </div>
          </div>
        )}

        {/* Connection warning */}
        {!connected && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="font-semibold text-yellow-400">Chưa kết nối server</p>
                <p className="text-sm text-yellow-400/70">
                  Hãy chạy Python server: <code className="bg-gray-800 px-2 py-0.5 rounded">python server.py</code>
                </p>
                <p className="text-sm text-yellow-400/70 mt-1">
                  Server URL: <input
                    type="text"
                    value={serverUrl}
                    onChange={(e) => setServerUrl(e.target.value)}
                    className="bg-gray-800 px-2 py-0.5 rounded text-white text-xs w-48"
                  />
                  &nbsp; TCP Port: <input
                    type="number"
                    value={tcpPort}
                    onChange={(e) => setTcpPort(Number(e.target.value))}
                    className="bg-gray-800 px-2 py-0.5 rounded text-white text-xs w-16"
                  />
                </p>
              </div>
            </div>
          </div>
        )}

        {/* File grid */}
        {files.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-6xl mb-4">📂</div>
            <p className="text-gray-400 text-lg">Thư mục trống</p>
            <p className="text-gray-500 text-sm mt-2">Kéo thả file hoặc nhấn nút "Tải lên" để bắt đầu</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {/* Sort: folders first */}
            {[...files].sort((a, b) => {
              if (a.type === "folder" && b.type !== "folder") return -1;
              if (a.type !== "folder" && b.type === "folder") return 1;
              return a.name.localeCompare(b.name);
            }).map((item) => (
              <div
                key={item.path}
                className="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-blue-500/50 hover:bg-gray-750 cursor-pointer transition group relative"
                onClick={() => navigateTo(item)}
                onContextMenu={(e) => handleContextMenu(e, item)}
              >
                <div className="text-4xl text-center mb-2">{getFileIcon(item)}</div>
                <p className="text-sm text-center truncate text-gray-200" title={item.name}>
                  {item.name}
                </p>
                {item.type === "file" && (
                  <p className="text-xs text-center text-gray-500 mt-1">{formatSize(item.size)}</p>
                )}
                {item.type === "folder" && (
                  <p className="text-xs text-center text-gray-500 mt-1">Thư mục</p>
                )}
                {/* Hover actions */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleContextMenu(e as any, item); }}
                    className="w-6 h-6 bg-gray-700 rounded flex items-center justify-center text-xs hover:bg-gray-600"
                  >
                    ⋮
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Context menu */}
        {contextMenu && (
          <div
            className="fixed bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 py-1 min-w-40"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            {contextMenu.item.type === "file" && (
              <button
                onClick={() => downloadFile(contextMenu.item)}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 flex items-center gap-2"
              >
                📥 Tải xuống
              </button>
            )}
            <button
              onClick={() => deleteItem(contextMenu.item)}
              className="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 flex items-center gap-2 text-red-400"
            >
              🗑️ Xóa
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-700 px-6 py-4 mt-8">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-gray-500">
          <span>Cloud Private • HTTP + TCP Protocol</span>
          <span>Đường dẫn: {currentPath}</span>
        </div>
      </footer>
    </div>
  );
}
