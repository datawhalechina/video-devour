// 处理阶段定义
export const PROCESSING_STAGES = {
  UPLOADING: "uploading",
  EXTRACTING_AUDIO: "extracting_audio",
  ASR: "asr",
  GENERATING_OUTLINE: "generating_outline",
  EXTRACTING_FRAMES: "extracting_frames",
  VLM_ANALYSIS: "vlm_analysis",
  GENERATING_REPORT: "generating_report",
  COMPLETED: "completed",
  ERROR: "error",
};

// 任务状态
export const TASK_STATUS = {
  PENDING: "pending",
  PROCESSING: "processing",
  COMPLETED: "completed",
  FAILED: "failed",
};

// 支持的视频格式
export const SUPPORTED_VIDEO_FORMATS = [
  "video/mp4",
  "video/avi",
  "video/mov",
  "video/mkv",
  "video/wmv",
  "video/flv",
  "video/webm",
];

// 文件大小限制（2GB）
export const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024;

// API 轮询间隔（毫秒）
export const POLLING_INTERVAL = 2000;

// 报告类型
export const REPORT_TYPES = {
  DETAILED: "detailed",
  FINAL: "final",
};
