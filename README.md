# 🍽️ VideoDevour | 吃掉视频 - 智能视频笔记生成器

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-13+-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🎯 **核心理念**：吃掉视频，输出一份报告！  
> 🚀 基于 ASR + VLM 技术的智能视频笔记工具，能够将任何视频"吞噬"并生成包含图文内容和视频剪影的结构化笔记报告

## 📋 目录

- [🎯 项目简介](#-项目简介)
- [✨ 核心功能](#-核心功能)
- [🔧 技术架构](#-技术架构)
- [📦 安装指南](#-安装指南)
- [🚀 快速开始](#-快速开始)
- [📖 使用示例](#-使用示例)
- [🏗️ 项目结构](#️-项目结构)
- [🤝 贡献指南](#-贡献指南)
- [📄 许可证](#-许可证)

## 🎯 项目简介

**VideoDevour（吃掉视频）** 是一个专注于视频笔记生成的智能工具，我们的使命是：

### 💡 核心价值观
> **"吃掉视频，突出一份报告"**  
> 将任何视频内容完全"消化"，提取精华，生成包含图文内容和视频剪影的高质量笔记报告

### 🎯 产品定位
VideoDevour 是你的**智能视频笔记助手**，通过先进的 ASR（自动语音识别）和 VLM（视觉语言模型）技术，能够：

- 📚 **学习笔记生成**：将教学视频转化为结构化学习笔记
- 📝 **会议记录整理**：自动生成会议要点和行动项
- 🎬 **内容摘要提取**：从长视频中提取关键信息点
- 📊 **多媒体报告**：生成包含时间轴、对话内容和视觉描述的完整报告
- ⏱️ **精准定位**：提供精确到单词级别的时间戳，便于回溯查找

## ✨ 核心功能

### 🍽️ 视频"吞噬"能力
VideoDevour 的核心在于将视频内容完全"消化"，就像吃掉视频一样，提取出有价值的笔记内容：

### 🎙️ 语音"消化" (ASR)
- **快速吞噬**：基于 WhisperX，以高达 70x 实时速度"吃掉"视频中的语音内容
- **说话人识别**：智能区分不同说话人，为每段对话打上身份标签
- **精准时间戳**：通过 wav2vec2.0 技术提供单词级精确定位，便于快速回溯
- **多语言消化**：支持多种语言的语音内容"消化"

### 🖼️ 视觉"提取" (VLM)
- **关键帧捕获**：每秒智能提取 12 张关键视觉信息
- **场景分割**：通过相似度算法（阈值 70%）自动识别场景切换点
- **内容理解**：使用 GLM-4.1 模型深度理解视觉内容，生成描述性笔记
- **视频剪影**：提取视频精华片段，形成可视化笔记摘要

### 📝 笔记"输出"
- **结构化笔记**：生成包含时间轴、对话内容、视觉描述的完整学习笔记
- **多格式导出**：支持导出为 PDF、HTML、Markdown 等格式的笔记文档
- **智能摘要**：自动提取关键信息点，生成视频内容摘要
- **可搜索索引**：为笔记内容建立索引，支持关键词快速检索

## 🔧 技术架构

### 核心技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| **视频处理** | FFmpeg | 视频剪辑和格式转换 |
| **语音识别** | WhisperX | 高性能 ASR 引擎 |
| **视觉理解** | GLM-4.1 | 多模态大语言模型 |
| **Agent框架** | AgentScope | 智能代理编排 |
| **大模型** | Kimi V2 | 对话和推理能力 |
| **后端API** | FastAPI | 高性能异步 Web 框架 |
| **前端界面** | Next.js | 现代化 React 框架 |

### WhisperX 核心优势

- 🚀 **快速转录**：使用 faster-whisper 后端，支持批量推理
- 🎯 **精确对齐**：wav2vec2.0 技术实现单词级时间戳
- 👥 **说话人分离**：集成 pyannote-audio 进行说话人识别
- 🔇 **噪声抑制**：VAD 预处理减少幻听现象
- 🌍 **多语言**：支持 99+ 种语言识别

## 📦 安装指南

### 环境要求

- Python 3.8+
- Node.js 16+
- FFmpeg
- CUDA 11.8+ (可选，用于 GPU 加速)

### 后端安装

```bash
# 克隆项目
git clone https://github.com/your-username/video2report.git
cd video2report

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 WhisperX
pip install whisperx

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的 API 密钥
```

### 前端安装

```bash
cd frontend
npm install
# 或使用 yarn
yarn install
```

## 🚀 快速开始

### 启动后端服务

```bash
# 进入项目根目录
cd video2report

# 启动 FastAPI 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 启动前端服务

```bash
cd frontend
npm run dev
# 或
yarn dev
```

访问 `http://localhost:3000` 开始使用！

## 📖 使用示例

### 🍽️ 典型"吃掉视频"场景

#### 场景1：学习笔记生成
```python
import requests

# 上传一个教学视频（比如：Python编程教程）
with open('python_tutorial.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/devour',  # "吃掉"视频
        files={'file': f},
        data={'note_type': 'learning', 'subject': 'Python编程'}
    )

video_id = response.json()['video_id']

# VideoDevour 开始"消化"视频
devour_response = requests.post(
    f'http://localhost:8000/api/digest/{video_id}'
)

# 获取生成的学习笔记
notes = requests.get(
    f'http://localhost:8000/api/notes/{video_id}'
)

print("📚 学习笔记已生成：")
print(f"- 知识点总数：{notes.json()['key_points_count']}")
print(f"- 代码示例：{notes.json()['code_examples_count']}")
print(f"- 重要时间点：{notes.json()['important_timestamps']}")
```

#### 场景2：会议记录整理
```python
# 上传会议录像
with open('team_meeting.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/devour',
        files={'file': f},
        data={'note_type': 'meeting', 'participants': ['Alice', 'Bob', 'Charlie']}
    )

# 获取会议笔记
meeting_notes = requests.get(f'http://localhost:8000/api/notes/{video_id}')
print("📝 会议纪要：")
print(f"- 讨论议题：{meeting_notes.json()['topics']}")
print(f"- 行动项：{meeting_notes.json()['action_items']}")
print(f"- 决策点：{meeting_notes.json()['decisions']}")
```

### 🖥️ 命令行"吞噬"模式

```bash
# 吃掉单个视频，生成笔记
python videodevour.py devour --input lecture.mp4 --output-format markdown --note-type learning

# 批量"吞噬"视频文件夹
python videodevour.py batch-devour --input-dir ./course_videos --output-dir ./course_notes

# 生成特定主题的笔记摘要
python videodevour.py summarize --input conference.mp4 --focus-keywords "AI,机器学习,深度学习"
```

### 📱 Web界面快速体验

1. **上传视频** → 拖拽视频文件到"吞噬区域"
2. **选择笔记类型** → 学习笔记 | 会议记录 | 内容摘要
3. **一键吞噬** → VideoDevour 开始"消化"你的视频
4. **获取笔记** → 下载生成的结构化笔记文档

## 🏗️ 项目结构

```
videodevour/
├── 📁 backend/              # 后端 FastAPI 应用
│   ├── 📁 api/             # API 路由（devour, digest, notes）
│   ├── 📁 core/            # 核心"吞噬"逻辑
│   ├── 📁 devour/          # 视频消化引擎
│   │   ├── asr_engine.py   # 语音"消化"模块
│   │   ├── vlm_engine.py   # 视觉"提取"模块
│   │   └── note_generator.py # 笔记生成器
│   ├── 📁 models/          # 数据模型
│   └── 📁 services/        # 服务层
├── 📁 frontend/            # Next.js 前端应用
│   ├── 📁 components/      # React 组件
│   │   ├── DevourZone.tsx  # 视频上传"吞噬区域"
│   │   ├── NoteViewer.tsx  # 笔记查看器
│   │   └── DigestProgress.tsx # 消化进度显示
│   ├── 📁 pages/          # 页面路由
│   └── 📁 styles/         # 样式文件
├── 📁 scripts/            # 工具脚本
├── 📁 tests/              # 测试文件
├── 📄 requirements.txt    # Python 依赖
├── 📄 package.json       # Node.js 依赖
├── 📄 videodevour.py     # 命令行工具
└── 📄 README.md          # 项目文档
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请参考以下步骤：

1. 🍴 Fork 本项目
2. 🌟 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 💻 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 📤 推送到分支 (`git push origin feature/AmazingFeature`)
5. 🔄 创建 Pull Request

### 开发规范

- 遵循 PEP 8 代码风格
- 添加适当的测试用例
- 更新相关文档
- 确保所有测试通过

## 📄 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

---

<div align="center">

**🍽️ VideoDevour - 让每个视频都成为有价值的笔记 🍽️**

**⭐ 如果 VideoDevour 帮你"吃掉"了有用的视频，请给个 Star！⭐**

> *"不要让好的视频内容白白流逝，让 VideoDevour 帮你把它们都'吃掉'变成笔记！"*

Made with ❤️ by the VideoDevour Team

</div>