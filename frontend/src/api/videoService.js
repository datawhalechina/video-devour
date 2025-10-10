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
 * @returns {Promise} 返回任务ID
 */
export const uploadVideo = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("video", file);

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
    return response;
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
    const response = await api.delete(`/report/${reportId}`);
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

export default api;
