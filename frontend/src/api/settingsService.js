import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 120000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail || error.message || "请求失败";
    return Promise.reject(new Error(message));
  }
);

/**
 * 获取当前设置（密钥脱敏）
 */
export const getSettings = async () => {
  return api.get("/settings");
};

/**
 * 更新设置（离线/在线模式、API Key、模型等）
 * @param {object} updates - 需要更新的字段，空值/脱敏值会被后端忽略
 */
export const updateSettings = async (updates) => {
  return api.put("/settings", updates);
};

/**
 * 测试 API 连通性
 * @param {string} target - asr | llm | vlm | all
 */
export const testSettings = async (target = "all") => {
  return api.post("/settings/test", { target });
};

/**
 * 生成学习卡片
 * @param {string} taskId - 任务ID
 * @returns {Promise} 返回 { html, cached }
 */
export const generateCard = async (taskId) => {
  return api.post(`/task/${taskId}/card`);
};

/**
 * 获取已生成的学习卡片
 */
export const getCard = async (taskId) => {
  return api.get(`/task/${taskId}/card`);
};
