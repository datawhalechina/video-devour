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
    const message =
      error.response?.data?.message || error.message || "请求失败";
    return Promise.reject(new Error(message));
  }
);

/**
 * 上传视频文件
 * @param {File} file - 视频文件
 * @param {Function} onProgress - 进度回调函数
 * @param {string} educationLevel - 学习阶段（小学/初中/高中），默认"高中"
 * @returns {Promise} 返回任务ID
 */
export const uploadVideo = async (file, onProgress, educationLevel = "高中") => {
  const formData = new FormData();
  formData.append("file", file);  // 修改字段名从 "video" 到 "file"
  formData.append("education_level", educationLevel);

  try {
    const response = await api.post("/video/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress?.(percentCompleted);
      },
    });

    return response;
  } catch (error) {
    throw error;
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
      status: item.status,
      createdAt: item.created_at,
      progress: item.progress || 0
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
export const searchLinkVideos = async (query, platform = "bilibili", maxResults = 8) => {
  try {
    const response = await api.post("/video/link/search", {
      query, platform, max_results: maxResults,
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
export const processLink = async (url, educationLevel = "高中") => {
  try {
    const response = await api.post("/video/link", {
      url, education_level: educationLevel,
    }, { timeout: 60000 });
    return response;
  } catch (error) {
    throw error;
  }
};
