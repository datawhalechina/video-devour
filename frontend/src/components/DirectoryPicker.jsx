import { useEffect, useState } from "react";
import { ArrowUp, Check, Folder, Loader2, X } from "lucide-react";

/**
 * 服务端目录选择弹窗：点选路径（进入子目录 / 上一级 / 选中当前目录）。
 * 走 GET /api/fs/dirs，网页与桌面客户端通用——目录在运行服务的机器上，
 * 浏览器无法直接给绝对路径，因此由后端列出子目录供点选。
 */
export default function DirectoryPicker({ open, initialPath = "", onClose, onPick }) {
  const [path, setPath] = useState("");
  const [parent, setParent] = useState("");
  const [dirs, setDirs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    browse(initialPath || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialPath]);

  const browse = async (p) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/fs/dirs?path=${encodeURIComponent(p)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setPath(data.path);
      // 记录后端返回的父目录（绝对路径）。「上一级」绝不能发相对路径（如 ".."）：
      // 后端按其工作目录解析会指到完全无关的位置，且后续导航全部失效。
      setParent(data.parent || "");
      setDirs(data.dirs || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[300] bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg flex flex-col overflow-hidden"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 flex-shrink-0">
          <h3 className="text-base font-bold text-gray-900">选择目录</h3>
          <button onClick={onClose} className="p-1 rounded-lg text-gray-500 hover:bg-gray-100"><X size={16} /></button>
        </div>

        <div className="px-5 py-3 border-b border-gray-100 text-xs font-mono text-gray-700 truncate" title={path}>
          {path || "…"}
        </div>

        <div className="h-72 overflow-y-auto px-2 py-1">
          {loading ? (
            <div className="py-10 text-center text-gray-400 flex items-center justify-center gap-2">
              <Loader2 size={16} className="animate-spin" /> 加载中…
            </div>
          ) : error ? (
            <p className="py-6 text-center text-rose-600 text-sm">{error}</p>
          ) : (
            <>
              <button onClick={() => browse(parent)}
                      disabled={!parent}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
                <ArrowUp size={15} className="text-gray-400" /> 上一级
              </button>
              {dirs.map((d) => (
                <button key={d} onClick={() => browse(`${path.replace(/\/$/, "")}/${d}`)}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-800 hover:bg-primary-50">
                  <Folder size={15} className="text-primary-500 flex-shrink-0" />
                  <span className="truncate">{d}</span>
                </button>
              ))}
              {dirs.length === 0 && <p className="py-4 text-center text-xs text-gray-400">没有子目录</p>}
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-200 flex-shrink-0">
          <button onClick={onClose}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50">取消</button>
          <button onClick={() => { if (path) { onPick(path); onClose(); } }} disabled={!path || loading}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-bold hover:bg-primary-700 disabled:opacity-50">
            <Check size={15} /> 选择此目录
          </button>
        </div>
      </div>
    </div>
  );
}
