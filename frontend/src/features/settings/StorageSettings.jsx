import { motion } from "framer-motion";
import { HardDriveDownload } from "lucide-react";

export default function StorageSettings({ model, activeSection }) {
  const { cacheInfo, loadCache } = model;
  return (
    <>
      {/* 下载缓存 */}
      <motion.section
        hidden={activeSection !== "storage"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-2 flex items-center space-x-2">
          <HardDriveDownload className="w-5 h-5 text-primary-600" />
          <span>下载缓存</span>
        </h2>
        <p className="text-xs text-gray-500 leading-relaxed mb-4">
          处理过的视频会缓存到本地，再次处理同一视频时直接复用、不再下载。
          下方是存储映射表（来源 → 本地文件）。
        </p>
        {cacheInfo ? (
          <>
            <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
              <span className="text-gray-600">
                已缓存{" "}
                <b className="text-gray-900">{cacheInfo.stats.entries}</b>{" "}
                个视频
              </span>
              <span className="text-gray-600">
                占用{" "}
                <b className="text-gray-900">
                  {cacheInfo.stats.total_size_human}
                </b>
              </span>
              <span className="text-gray-600">
                已复用{" "}
                <b className="text-primary-600">
                  {cacheInfo.stats.reused_downloads}
                </b>{" "}
                次
              </span>
              <button
                onClick={loadCache}
                className="ml-auto px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium hover:bg-gray-50"
              >
                刷新
              </button>
            </div>
            {cacheInfo.entries.length > 0 ? (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 text-gray-500 sticky top-0">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium">
                          视频
                        </th>
                        <th className="text-left px-3 py-2 font-medium">
                          平台
                        </th>
                        <th className="text-right px-3 py-2 font-medium">
                          大小
                        </th>
                        <th className="text-right px-3 py-2 font-medium">
                          复用
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {cacheInfo.entries.map((e) => (
                        <tr
                          key={e.key}
                          className="border-t border-gray-100 hover:bg-gray-50"
                        >
                          <td
                            className="px-3 py-2 text-gray-800 max-w-[17.5rem] truncate"
                            title={e.title}
                          >
                            {e.title || e.key}
                          </td>
                          <td className="px-3 py-2 text-gray-500">
                            {e.platform}
                          </td>
                          <td className="px-3 py-2 text-right text-gray-500">
                            {(e.size / 1024 / 1024).toFixed(1)}MB
                          </td>
                          <td className="px-3 py-2 text-right text-primary-600">
                            {e.hit_count} 次
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <p className="text-xs text-gray-400">暂无缓存视频。</p>
            )}
            <p className="mt-3 text-xs text-gray-400">
              缓存目录：{cacheInfo.stats.cache_dir}
            </p>
          </>
        ) : (
          <p className="text-xs text-gray-400">加载中…</p>
        )}
      </motion.section>
    </>
  );
}
