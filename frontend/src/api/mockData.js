// 模拟数据 - 用于开发测试，后端完成后可以删除

export const mockReport = {
  id: "123456",
  videoName: "示例视频.mp4",
  createdAt: new Date().toISOString(),
  duration: "15:30",
  status: "completed",
  description: "这是一个关于人工智能技术的教学视频",
  detailedOutline: `# 视频分析报告

## 概述
本视频主要介绍了人工智能技术的基本概念和应用场景。

## 第一章：什么是人工智能

![关键帧1](https://via.placeholder.com/800x450/0ea5e9/ffffff?text=AI+Introduction)

人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。

### 核心要点
- 机器学习是AI的重要组成部分
- 深度学习推动了AI的快速发展
- AI应用广泛，包括图像识别、自然语言处理等

## 第二章：AI的发展历程

![关键帧2](https://via.placeholder.com/800x450/0369a1/ffffff?text=AI+History)

从1956年达特茅斯会议开始，人工智能经历了多次起伏。

### 重要里程碑
1. 1956年：AI概念诞生
2. 1997年：深蓝击败国际象棋世界冠军
3. 2012年：深度学习在图像识别领域取得突破
4. 2016年：AlphaGo战胜围棋世界冠军

## 第三章：当前应用

![关键帧3](https://via.placeholder.com/800x450/075985/ffffff?text=AI+Applications)

当前AI技术已经广泛应用于各个领域：

- **医疗健康**：疾病诊断、药物研发
- **金融服务**：风险评估、智能投顾
- **自动驾驶**：环境感知、路径规划
- **智能客服**：自然语言理解、对话系统

## 总结

人工智能正在改变我们的生活和工作方式，未来还有更广阔的发展空间。
`,
  finalReport: `# AI技术概览

## 核心内容

本视频系统介绍了人工智能技术的基础知识、发展历程和实际应用。主要包含以下要点：

1. **AI定义**：能够执行智能任务的计算机系统
2. **发展历程**：从1956年至今的重要里程碑
3. **当前应用**：医疗、金融、自动驾驶、客服等领域

## 关键洞察

- 机器学习和深度学习是当前AI发展的核心驱动力
- AI技术已经从实验室走向实际应用
- 未来AI将在更多领域发挥重要作用

## 结论

人工智能技术正处于快速发展阶段，其应用前景广阔，值得持续关注。
`,
  assets: [
    { name: "视频片段1.mp4", type: "video", url: "#" },
    { name: "视频片段2.mp4", type: "video", url: "#" },
    { name: "关键帧1.jpg", type: "image", url: "#" },
    { name: "关键帧2.jpg", type: "image", url: "#" },
  ],
};

export const mockHistory = [
  {
    id: "1",
    videoName: "AI技术讲座.mp4",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    duration: "15:30",
    status: "completed",
    description: "人工智能技术基础介绍",
  },
  {
    id: "2",
    videoName: "产品发布会.mp4",
    createdAt: new Date(Date.now() - 172800000).toISOString(),
    duration: "45:20",
    status: "completed",
    description: "2024年度产品发布会完整记录",
  },
  {
    id: "3",
    videoName: "团队会议录像.mp4",
    createdAt: new Date(Date.now() - 259200000).toISOString(),
    duration: "32:15",
    status: "processing",
    description: "季度总结会议",
  },
];

// 模拟API延迟
export const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
