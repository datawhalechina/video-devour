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
