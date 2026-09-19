import axios from "axios";

// 创建 axios 实例
const api = axios.create({
  baseURL: "/api",
  timeout: 300000, // 5分钟超时
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 这里可以添加认证 token 等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // FastAPI 错误体是 {detail: ...}，旧代码只读 data.message 会丢掉后端的中文提示
    const detail = error.response?.data?.detail;
    const message =
      (typeof detail === "string" ? detail : detail?.message) ||
      error.response?.data?.message ||
      error.message ||
      "请求失败";
    return Promise.reject(new Error(message));
  }
);

/**
 * 上传视频文件
 * @param {File} file - 视频文件
 * @param {Function} onProgress - 进度回调函数
 * @param {string} educationLevel - 学习阶段，默认"自由学习"
 * @returns {Promise} 返回任务ID
 */
export const uploadVideo = async (file, onProgress, educationLevel = "自由学习", extras = []) => {
  const formData = new FormData();
  formData.append("file", file);  // 修改字段名从 "video" 到 "file"
  formData.append("education_level", educationLevel);
  if (extras?.length) formData.append("extras", extras.join(","));

  // 大文件（直播回放等可达数 GB）不能受 axios 全局 5 分钟超时限制：
  // 上传请求不限总时长，改用「速率看门狗」止损——
  // ① 启动宽限 20s 后平均速率仍 < 100KB/s → 中止（照此速度还要传数小时）
  // ② 连续 45s 完全无进度 → 中止（连接已停滞）
  const controller = new AbortController();
  let abortReason = null;
  const startedAt = Date.now();
  let lastLoaded = 0;
  let lastProgressAt = startedAt;
  const MIN_AVG_BPS = 100 * 1024;   // 100 KB/s
  const GRACE_MS = 20 * 1000;
  const STALL_MS = 45 * 1000;

  const watchdog = setInterval(() => {
    const elapsed = Date.now() - startedAt;
    if (lastLoaded <= 0) return                       // 还没开始传数据，不判
    const avgBps = lastLoaded / Math.max(elapsed, 1) * 1000
    const stalledFor = Date.now() - lastProgressAt
    if (elapsed > GRACE_MS && avgBps < MIN_AVG_BPS) {
      abortReason = new Error(`上传速率过低（平均 ${Math.round(avgBps / 1024)} KB/s），按此速度剩余内容还需约 ` +
        `${Math.max(1, Math.round((file.size - lastLoaded) / avgBps / 60))} 分钟，已自动中止。` +
        `请检查网络后重试，或改用更快的网络。`)
      controller.abort()
    } else if (stalledFor > STALL_MS) {
      abortReason = new Error(`上传已停滞 ${Math.round(stalledFor / 1000)} 秒无进度，已自动中止。请检查网络后重试。`)
      controller.abort()
    }
  }, 2000);

  try {
    const response = await api.post("/video/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      timeout: 0,            // 覆盖全局 5 分钟超时：上传不限总时长，止损交给速率看门狗
      signal: controller.signal,
      onUploadProgress: (progressEvent) => {
        const now = Date.now()
        if (progressEvent.loaded > lastLoaded) lastProgressAt = now
        const elapsed = now - startedAt
        const avgBps = progressEvent.loaded / Math.max(elapsed, 1) * 1000
        lastLoaded = progressEvent.loaded
        const percentCompleted = progressEvent.total
          ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
          : 0;
        const etaSec = avgBps > 1024 ? Math.round((progressEvent.total - progressEvent.loaded) / avgBps) : null
        onProgress?.({
          percent: percentCompleted,
          speedText: avgBps > 1024
            ? (avgBps >= 1024 * 1024 ? `${(avgBps / 1024 / 1024).toFixed(1)} MB/s` : `${Math.round(avgBps / 1024)} KB/s`)
            : null,
          etaText: etaSec != null ? (etaSec >= 60 ? `约 ${Math.ceil(etaSec / 60)} 分钟` : `${etaSec} 秒`) : null,
        });
      },
    });

    return response;
  } catch (error) {
    // 看门狗中止：把 axios 的 CanceledError 转成给用户的明确原因
    if (abortReason) throw abortReason
    if (error?.code === 'ERR_CANCELED') throw new Error('上传已中止')
    throw error;
  } finally {
    clearInterval(watchdog);
  }
};

/**
 * 获取任务处理状态
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回任务状态信息
 */
export const getTaskStatus = async (taskId) => {
  try {
    const response = await api.get(`/task/${taskId}/status`);
    return response;
  } catch (error) {
    throw error;
  }
};

/**
 * 获取历史记录列表
 * @returns {Promise} 返回历史记录数组
 */
export const getHistory = async () => {
  try {
    const response = await api.get("/history");
    // 确保返回的数据包含正确的字段映射
    return response.map(item => ({
      id: item.task_id,
      videoName: item.filename,
      displayName: item.display_name || '',
      status: item.status,
      createdAt: item.created_at,
      progress: item.progress || 0,
      message: item.message || ''
    }));
  } catch (error) {
    throw error;
  }
};

/**
 * 删除报告
 * @param {string} reportId - 报告ID
 * @returns {Promise}
 */
export const deleteReport = async (reportId) => {
  try {
    const response = await api.delete(`/task/${reportId}`);
    return response;
  } catch (error) {
    throw error;
  }
};

/**
 * 下载报告文件
 * @param {string} reportId - 报告ID
 * @param {string} type - 文件类型 (detailed, final, video, etc.)
 * @returns {Promise}
 */
export const downloadFile = async (reportId, type) => {
  try {
    const response = await api.get(`/report/${reportId}/download/${type}`, {
      responseType: "blob",
    });
    return response;
  } catch (error) {
    throw error;
  }
};

export const getTaskReport = async (taskId) => {
  try {
    const response = await api.get(`/task/${taskId}/report`);
    return response;
  } catch (error) {
    console.error('获取报告详情失败:', error);
    throw error;
  }
};

export default api;

/**
 * 获取链接视频元数据（不下载，用于预览）
 * @param {string} url - 视频链接（B站/YouTube）
 */
export const getLinkInfo = async (url) => {
  try {
    const response = await api.post("/video/link/info", { url });
    return response;
  } catch (error) {
    throw error;
  }
};

/**
 * 按关键词搜索 B站/YouTube 视频
 * @param {string} query - 搜索关键词
 * @param {string} platform - bilibili | youtube
 * @param {number} maxResults - 返回条数
 */
export const searchLinkVideos = async (query, platform = "bilibili", maxResults = 8, page = 1) => {
  try {
    const response = await api.post("/video/link/search", {
      query, platform, max_results: maxResults, page,
    }, { timeout: 60000 });
    return response;
  } catch (error) {
    throw error;
  }
};

/**
 * 通过链接一键下载并处理视频
 * @param {string} url - 视频链接
 * @param {string} educationLevel - 学习阶段
 */
export const processLink = async (url, educationLevel = "自由学习", extras = []) => {
  try {
    const response = await api.post("/video/link", {
      url, education_level: educationLevel, extras,
    }, { timeout: 60000 });
    return response;
  } catch (error) {
    throw error;
  }
};

export const generateSubtitleNotes = async (url, educationLevel = '自由学习') => {
  try {
    return await api.post('/video/link/notes', { url, education_level: educationLevel }, { timeout: 180000 });
  } catch (error) {
    const message =
      error.response?.data?.detail || error.message || '字幕笔记生成失败';
    return Promise.reject(new Error(message));
  }
};
