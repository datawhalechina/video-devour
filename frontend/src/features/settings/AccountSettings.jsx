import { motion } from "framer-motion";
import { Input } from "antd";
import { WorkspaceSelect } from "../../components/ui/Controls";
import { isDesktopClient } from "../../api/desktopBridge";
import { inputClass } from "./fieldStyles";
import { labelClass } from "./fieldStyles";
import { Loader2, Globe } from "lucide-react";

export default function AccountSettings({ model, activeSection }) {
  const {
    form,
    cookieImport,
    loginCapture,
    ytCheck,
    setField,
    handleYtCheck,
    handleImportCookies,
    handleCaptureLogin,
    LOGIN_TARGETS,
  } = model;
  return (
    <>
      {/* 抖音 cookies */}
      <motion.section
        hidden={activeSection !== "accounts"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.16 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-2">
          抖音 cookies（下载 + 搜索都需要登录态）
        </h2>
        <p className="text-xs text-gray-500 leading-relaxed mb-4">
          抖音的下载与关键词搜索都要求登录态（匿名搜索返回「请先登录」）。配置后可：①
          下载抖音视频； ② 在「在线视频」页用关键词搜索抖音。获取方式：登录
          douyin.com 后用浏览器扩展导出 cookies.txt （Netscape 格式，需含
          sessionid），粘贴到下方；也可用上方「一键读取浏览器 Cookie」自动获取。
        </p>
        <div>
          <label htmlFor="setting-douyin_cookies" className={labelClass}>
            cookies.txt 内容（Netscape 格式）
          </label>
          <textarea
            id="setting-douyin_cookies"
            value={form.douyin_cookies || ""}
            onChange={(e) => setField("douyin_cookies", e.target.value)}
            placeholder="# Netscape HTTP Cookie File&#10;.douyin.com	TRUE	/	TRUE	0	sessionid	..."
            rows={5}
            className={`${inputClass} font-mono text-xs`}
          />
        </div>
      </motion.section>

      {/* 应用内登录读取（桌面客户端，Windows 推荐） */}
      <motion.section
        hidden={activeSection !== "accounts"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.11 }}
        className="bg-white rounded-2xl shadow-sm border border-primary-200 p-6"
      >
        <div className="flex items-center space-x-2 mb-2">
          <Globe className="w-5 h-5 text-primary-600" />
          <h2 className="text-base font-bold text-gray-900">
            应用内登录读取 Cookie（推荐）
          </h2>
        </div>
        <p className="text-xs text-gray-500 leading-relaxed mb-4">
          点击对应平台，会弹出一个登录窗口；在其中登录成功后自动读取登录态并填入下方卡片，
          随后窗口自动关闭（仅本机处理，不上传）。此方式读的是应用自身的登录会话，
          <span className="text-primary-600">
            不受 Windows 下 Chrome/Edge 的 App-Bound 加密与 Cookie 文件锁限制
          </span>
          ， 是 Windows 客户端最可靠的方式。
        </p>
        <div className="flex flex-wrap items-center gap-3">
          {LOGIN_TARGETS.map((t) => (
            <button
              key={t.key}
              onClick={() => handleCaptureLogin(t.key)}
              disabled={!!loginCapture.loading || !isDesktopClient()}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-bold shadow-md hover:shadow-lg disabled:opacity-50"
            >
              {loginCapture.loading === t.key && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              <span>
                {loginCapture.loading === t.key ? "等待登录…" : t.label}
              </span>
            </button>
          ))}
        </div>
        {!isDesktopClient() && (
          <p className="mt-3 text-xs text-amber-600">
            应用内登录读取仅在桌面客户端（VideoDevour
            应用）中可用；当前为浏览器模式，请使用下方一键读取或手动粘贴。
          </p>
        )}
        {loginCapture.message && (
          <p
            className={`mt-3 text-sm ${loginCapture.ok ? "text-green-700" : "text-gray-600"}`}
          >
            {loginCapture.message}
          </p>
        )}
      </motion.section>

      {/* 一键读取浏览器 Cookie */}
      <motion.section
        hidden={activeSection !== "accounts"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.115 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-2">
          从浏览器数据库读取 Cookie
        </h2>
        <p className="text-xs text-gray-500 leading-relaxed mb-4">
          直接读取本机浏览器（Chrome/Edge/Firefox 等）已保存的登录 Cookie
          并填入下方各卡片 （仅读取目标站的 cookie，本机处理，不上传）。macOS
          首次读取 Chrome/Edge 会弹出钥匙串授权， 请点「允许」；Windows 下
          Chrome/Edge 127+ 受 App-Bound 加密限制无法读取，
          请改用上方「应用内登录读取」或 Firefox / 手动粘贴。
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <WorkspaceSelect
            aria-label="读取 Cookie 的浏览器"
            value={form.cookie_browser || ""}
            onChange={(value) => setField("cookie_browser", value)}
            style={{ width: 240 }}
            options={[
              { value: "", label: "自动检测（按序尝试）" },
              ...[
                "chrome",
                "edge",
                "firefox",
                "safari",
                "brave",
                "opera",
                "vivaldi",
              ].map((value) => ({
                value,
                label: value[0].toUpperCase() + value.slice(1),
              })),
            ]}
          />
          <button
            onClick={handleImportCookies}
            disabled={cookieImport.loading}
            className="flex items-center space-x-2 px-5 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-bold shadow-md hover:shadow-lg disabled:opacity-50"
          >
            {cookieImport.loading && (
              <Loader2 className="w-4 h-4 animate-spin" />
            )}
            <span>{cookieImport.loading ? "读取中…" : "一键读取"}</span>
          </button>
        </div>
        {cookieImport.message && (
          <p
            className={`mt-3 text-sm ${cookieImport.attempts.some((a) => a.includes("✅")) ? "text-green-700" : "text-gray-600"}`}
          >
            {cookieImport.message}
          </p>
        )}
        {cookieImport.attempts.length > 0 && (
          <details className="mt-2">
            <summary className="text-xs text-gray-400 cursor-pointer">
              读取明细
            </summary>
            <ul className="mt-1 space-y-0.5">
              {cookieImport.attempts.map((a, i) => (
                <li key={i} className="text-xs text-gray-500 font-mono">
                  {a}
                </li>
              ))}
            </ul>
          </details>
        )}
      </motion.section>

      {/* 微信视频号 */}
      <motion.section
        hidden={activeSection !== "accounts"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-2">
          微信视频号（分享链接解析）
        </h2>
        <p className="text-xs text-gray-500 leading-relaxed mb-4">
          视频号没有公开直链，下载需通过腾讯元宝接口解析：登录
          <span className="text-primary-600"> yuanbao.tencent.com </span>
          后按 F12 打开开发者工具 → Network → 任选请求复制 Cookie 填入下方
          （仅保存在本机
          settings.json）。未配置时自动尝试公共解析服务，或使用本地工具下载后直接上传。
        </p>
        <div className="space-y-4">
          <div>
            <label
              htmlFor="setting-wechat_yuanbao_cookie"
              className={labelClass}
            >
              元宝 Cookie（用于解析分享链接）
            </label>
            <Input.Password
              id="setting-wechat_yuanbao_cookie"
              value={form.wechat_yuanbao_cookie || ""}
              onChange={(e) =>
                setField("wechat_yuanbao_cookie", e.target.value)
              }
              placeholder="粘贴 yuanbao.tencent.com 的 Cookie"
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="setting-wechat_resolver_url"
                className={labelClass}
              >
                自建解析服务 URL（可选）
              </label>
              <Input
                id="setting-wechat_resolver_url"
                type="text"
                value={form.wechat_resolver_url || ""}
                onChange={(e) =>
                  setField("wechat_resolver_url", e.target.value)
                }
                placeholder="https://your-worker.workers.dev"
                className={inputClass}
              />
            </div>
            <div>
              <label
                htmlFor="setting-wechat_resolver_token"
                className={labelClass}
              >
                解析服务 Token（可选）
              </label>
              <Input.Password
                id="setting-wechat_resolver_token"
                value={form.wechat_resolver_token || ""}
                onChange={(e) =>
                  setField("wechat_resolver_token", e.target.value)
                }
                placeholder="sph worker 的 ACCESS_CREDENTIAL"
                className={inputClass}
              />
            </div>
          </div>
        </div>
      </motion.section>

      {/* B站账号 */}
      <motion.section
        hidden={activeSection !== "accounts"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.13 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-2">
          B站账号（可选，解锁 AI 字幕）
        </h2>
        <p className="text-xs text-gray-500 leading-relaxed mb-4">
          B站 AI 字幕轨仅对登录态可见：配置 SESSDATA
          后「字幕笔记」功能可用（仅保存在本机）。 获取：登录 bilibili.com → F12
          → Application（应用）→ Cookies → 复制 SESSDATA 的值。
        </p>
        <div>
          <label htmlFor="setting-bilibili_sessdata" className={labelClass}>
            SESSDATA
          </label>
          <Input.Password
            id="setting-bilibili_sessdata"
            value={form.bilibili_sessdata || ""}
            onChange={(e) => setField("bilibili_sessdata", e.target.value)}
            placeholder="粘贴 SESSDATA 的值"
            className={inputClass}
          />
        </div>
      </motion.section>

      {/* YouTube cookies */}
      <motion.section
        hidden={activeSection !== "accounts"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.14 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-2">
          YouTube cookies（下载防 bot 检查）
        </h2>
        <p className="text-xs text-gray-500 leading-relaxed mb-4">
          YouTube 对部分 IP 强制登录验证，未配置 cookies
          时下载会失败。获取方法：登录 youtube.com 后， 使用浏览器扩展（如 Get
          cookies.txt LOCALLY）导出 cookies.txt（Netscape 格式），
          把文件内容完整粘贴到下方（仅保存在本机
          settings.json，脱敏显示）。也可通过环境变量 YTDLP_COOKIES_FILE 指向
          cookies 文件。
        </p>
        <div>
          <label htmlFor="setting-youtube_cookies" className={labelClass}>
            cookies.txt 内容（Netscape 格式）
          </label>
          <textarea
            id="setting-youtube_cookies"
            value={form.youtube_cookies || ""}
            onChange={(e) => setField("youtube_cookies", e.target.value)}
            placeholder="# Netscape HTTP Cookie File&#10;.youtube.com	TRUE	/	TRUE	0	KEY	VALUE..."
            rows={6}
            className={`${inputClass} font-mono text-xs`}
          />
        </div>
        <div className="mt-4 border-t border-gray-100 pt-4">
          <button
            onClick={handleYtCheck}
            disabled={ytCheck.loading}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            {ytCheck.loading && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>下载环境自检</span>
          </button>
          {ytCheck.result && (
            <div className="mt-3 space-y-1.5 text-xs">
              {(() => {
                const c = ytCheck.result.checks || {};
                const items = [
                  [
                    !!c.yt_dlp_version,
                    `yt-dlp ${c.yt_dlp_version || "未安装"}`,
                  ],
                  [!!c.cookies_configured, "YouTube cookies 已配置"],
                  [!!c.pot_script, "PO Token 脚本已安装"],
                  [
                    !!c.node_available,
                    `node 运行时${c.node_version ? ` ${c.node_version}` : ""}`,
                  ],
                ];
                return items.map(([ok, text], i) => (
                  <p
                    key={i}
                    className={ok ? "text-green-700" : "text-gray-500"}
                  >
                    {ok ? "✓" : "○"} {text}
                  </p>
                ));
              })()}
              {(ytCheck.result.suggestions || []).length > 0 && (
                <div className="pt-1 border-t border-gray-100">
                  <p className="font-semibold text-gray-700 mt-1">建议：</p>
                  {(ytCheck.result.suggestions || []).map((s, i) => (
                    <p key={i} className="text-gray-500 leading-relaxed">
                      · {s}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </motion.section>
    </>
  );
}
