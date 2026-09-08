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

/**
 * 生成思维导图（markmap HTML）
 */
export const generateMindmap = async (taskId) => {
  return api.post(`/task/${taskId}/mindmap`);
};

/**
 * 生成知识图谱（ECharts 力导向图 HTML）
 */
export const generateKnowledgeGraph = async (taskId) => {
  return api.post(`/task/${taskId}/knowledge-graph`);
};

/**
 * 一键读取本机浏览器中的 B站 / YouTube / 元宝 Cookie 并写入设置
 * @param {string} browser - 指定浏览器（空 = 自动按序尝试）
 */
export const importCookiesFromBrowser = async (browser = "") => {
  return api.post("/settings/cookies/from-browser", { browser }, { timeout: 480000 });
};

/**
 * YouTube 下载环境自检（yt-dlp 版本 / cookies / PO Token / node）
 */
export const youtubeEnvCheck = async () => {
  return api.get("/video/link/youtube-check", { timeout: 60000 });
};
