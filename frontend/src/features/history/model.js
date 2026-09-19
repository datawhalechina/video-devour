export const STATUS_OPTIONS = [
  ["all", "全部"],
  ["processing", "处理中"],
  ["completed", "已完成"],
  ["failed", "失败"],
];
export function groupHistory(records, now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const groups = new Map();
  for (const item of [...records].sort(
    (a, b) => (Date.parse(b.createdAt) || 0) - (Date.parse(a.createdAt) || 0),
  )) {
    const date = new Date(item.createdAt);
    const key = Number.isNaN(date.getTime())
      ? "时间未知"
      : date.toLocaleDateString("zh-CN");
    const label =
      key === today.toLocaleDateString("zh-CN")
        ? "今天"
        : key === yesterday.toLocaleDateString("zh-CN")
          ? "昨天"
          : key;
    if (!groups.has(key)) groups.set(key, { key, label, items: [] });
    groups.get(key).items.push(item);
  }
  return [...groups.values()];
}
export const historySamples = [
  ...[
    ["queued", "城市漫步：从街道观察公共空间", 0, "等待开始，正在准备处理环境", "06:28", "B站"],
    ["downloading", "建筑与自然光：室内空间的光影实验", 12, "正在下载视频 · 18.6 / 156 MB", "32:10", "YouTube"],
    ["extras", "从复杂系统到实践：跨学科研究中的知识关联与长期学习方法", 95, "报告已整理，正在生成思维导图与学习卡片", "01:26:45", "B站"],
    ["finishing", "一杯咖啡的风味实验", 99, "正在保存报告与关键帧，即将完成", "09:36", "本地上传"],
  ].map(([key, videoName, progress, message, duration, platform], index) => ({
    id: `preview-${key}`, videoName, status: "processing", progress, message,
    duration, platform, createdAt: new Date(Date.now() - index * 60000).toISOString(), preview: true,
  })),
  {
    id: "preview-transcribing",
    videoName: "海洋的另一面：探索深海世界",
    status: "processing",
    progress: 38,
    message: "正在识别语音，整理字幕",
    duration: "18:24",
    createdAt: "2026-09-16T10:30:00+08:00",
    preview: true,
  },
  {
    id: "preview-generating",
    videoName: "设计，源于对生活的理解",
    status: "processing",
    progress: 76,
    message: "正在提炼核心观点",
    duration: "24:17",
    createdAt: "2026-09-16T10:25:00+08:00",
    preview: true,
  },
  {
    id: "preview-network-failed",
    videoName: "如何建立持续学习的习惯",
    status: "failed",
    message: "网络连接中断",
    duration: "12:01",
    createdAt: "2026-09-15T10:20:00+08:00",
    preview: true,
  },
  {
    id: "preview-model-failed",
    videoName: "人工智能的下一种可能",
    status: "failed",
    message: "模型 API Key 无效，请检查配置",
    duration: "16:37",
    createdAt: "2026-09-15T10:15:00+08:00",
    preview: true,
  },
];
