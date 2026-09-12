/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的文件大小
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
};

/**
 * 格式化时间（秒转为 mm:ss）
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时间
 */
export const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

/**
 * 格式化日期
 * @param {string} dateString - ISO 日期字符串
 * @returns {string} 格式化后的日期
 */
export const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

/**
 * 验证视频文件格式
 * @param {File} file - 文件对象
 * @param {string[]} allowedFormats - 允许的格式列表
 * @returns {boolean} 是否有效
 */
export const isValidVideoFormat = (file, allowedFormats) => {
  return allowedFormats.includes(file.type);
};

/**
 * 验证文件大小
 * @param {File} file - 文件对象
 * @param {number} maxSize - 最大大小（字节）
 * @returns {boolean} 是否有效
 */
export const isValidFileSize = (file, maxSize) => {
  return file.size <= maxSize;
};

/**
 * 下载文件
 * @param {string} content - 文件内容
 * @param {string} filename - 文件名
 * @param {string} mimeType - MIME 类型
 */
export const downloadFile = (content, filename, mimeType = "text/plain") => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

/**
 * 触发浏览器/WebView 下载。
 *
 * 必须通过带 download 属性的 <a> 触发，不能用 window.open：
 * - 桌面客户端（pywebview/WKWebView）：window.open 的导航类型是 Other，
 *   不会被壳的「target=_blank 交给系统浏览器」逻辑接管，结果是静默无反应；
 *   而不带 download 属性的链接会被 WebView 当作普通导航，
 *   text/markdown、application/pdf 这类「可显示」的响应会把整个 SPA 替换掉 → 白屏。
 *   带 download 属性后走 WebView 的下载策略（与 MIME 类型无关）。
 * - 纯浏览器：效果等同普通下载。
 *
 * @param {string} url - 下载地址（同源相对路径即可）
 */
export const triggerDownload = (url) => {
  const a = document.createElement("a");
  a.href = url;
  // 空值表示沿用响应 Content-Disposition 里的文件名（含中文）
  a.download = "";
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

/**
 * 延迟函数
 * @param {number} ms - 延迟毫秒数
 * @returns {Promise}
 */
export const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * 截断文本
 * @param {string} text - 原始文本
 * @param {number} maxLength - 最大长度
 * @returns {string} 截断后的文本
 */
export const truncateText = (text, maxLength = 50) => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
};
