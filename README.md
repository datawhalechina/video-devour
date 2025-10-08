# 🍽️ VideoDevour | 智能视频到报告生成器

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🎯 **核心理念**：吃掉视频，输出一份图文并茂的报告！  
> 🚀 基于 ASR + VLM 技术的智能视频分析工具，能够将任何视频"吞噬"并生成包含关键帧图片、内容摘要和视频剪辑的结构化报告。

## 📋 目录

- [🎯 项目简介](#-项目简介)
- [✨ 核心功能](#-核心功能)
- [🔧 技术架构](#-技术架构)
- [📦 安装指南](#-安装指南)
- [🚀 快速开始](#-快速开始)
- [🏗️ 项目结构](#️-项目结构)
- [🤝 贡献指南](#-贡献指南)
- [📄 许可证](#-许可证)

## 🎯 项目简介

**VideoDevour（吃掉视频）** 是一个专注于从视频中提取和生成结构化报告的智能工具。我们的目标是自动完成从原始视频到高质量图文报告的转换过程。

### 💡 核心价值
> **"吃掉视频，输出一份报告"**  
> 将任何视频内容完全"消化"，提取其核心语音和视觉信息，生成一份包含文本大纲、关键帧图片和视频剪辑的高质量报告。

### 🎯 应用场景
- 📚 **学习笔记生成**：将线上课程或教学视频，自动整理成带章节、配图和文字记录的笔记。
- 📝 **会议记录整理**：快速将会议录像转化为带章节摘要、发言记录和关键画面的会议纪要。
- 🎬 **内容创作素材**：从长视频中自动提取关键片段和图片，为二次创作提供素材。

## ✨ 核心功能

### 🎙️ 语音识别 (ASR)
- **精准语音转写**：集成 **FunASR Paraformer V2** 模型，提供高准确度的语音识别，并自动添加标点。
- **说话人分离**：能够识别并区分视频中的不同说话人。
- **精确时间戳**：为每一句对话提供毫秒级精度的开始和结束时间戳。

### 📝 大纲生成与内容匹配
- **智能生成大纲**：利用大语言模型（LLM）分析语音转写内容，自动生成符合视频逻辑结构的Markdown层级大纲。
- **内容精准匹配**：通过文本相似度算法，将每一段对话文本块，精确地匹配到对应的大纲章节下。

### 🎬 视频与图像处理
- **自动视频切片**：根据生成的大纲章节，使用 **FFmpeg** 自动将原始视频分割成多个独立的片段。
- **关键帧提取**：从每个视频片段中，按固定速率（如1fps）提取所有帧图片。
- **图像去重**：通过图像相似度对比，去除冗余和高度相似的帧，保留有效视觉信息。
- **VLM智能筛选**：利用视觉语言模型（VLM）对去重后的候选帧进行评分，为每个章节挑选出最匹配、最具代表性的一张关键帧。

### 📜 报告生成
- **图文报告**：整合文本大纲和VLM筛选出的关键帧，生成一份图文并茂的 `detailed_outline.md`。
- **最终精加工**：再次调用LLM，对图文大纲进行最终的润色和扩写，生成一份语言更流畅、内容更丰富的 `final_report.md`。

## 🔧 技术架构

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| **核心流程** | Python | 项目的主要编程语言。 |
| **语音识别** | FunASR (Paraformer V2) | 阿里巴巴开源的高性能语音识别模型。 |
| **大模型交互** | Camel-AI | 一个用于与大语言模型（LLM）和视觉语言模型（VLM）交互的轻量级框架。 |
| **视频/图像处理** | FFmpeg, OpenCV | 用于视频切分、帧提取和图像处理。 |
| **文本匹配**| Sentence Transformers | 用于计算文本语义相似度。 |

## 📦 安装指南

### 环境要求
- Python 3.8+
- FFmpeg
- CUDA (可选, 用于GPU加速)

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-username/VideoDevour.git
cd VideoDevour

# 2. 创建并激活Python虚拟环境
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate

# 3. 安装所有依赖项
pip install -r requirements.txt
```
*注意：`requirements.txt` 应包含 `funasr`, `torch`, `camel-ai`, `opencv-python-headless` 等所有必需的库。*

## 🚀 快速开始

项目现在通过命令行启动，所有处理步骤都已自动化。不过需要提前到backend\algorithm\config copy.py配置llm和vlm的apikey。

### 执行处理流程

在项目根目录下，运行以下命令：

```bash
python backend/algorithm/main.py "path/to/your/video.mp4"
```

**示例：**
处理位于 `input_video` 文件夹下的 `minvideo.mp4`：
```bash
python backend/algorithm/main.py "input_video/minvideo.mp4"
```

程序执行完毕后，所有输出文件，包括日志、ASR结果、视频切片、关键帧图片和最终报告，都将保存在 `output` 目录下，一个以视频名和时间戳命名的新文件夹中。

## 🏗️ 项目结构

```
videodevour/
├── 📁 backend/
│   ├── 📁 algorithm/         # 核心处理算法和流程
│   │   ├── pipeline.py       # 封装了从头到尾的完整处理流程
│   │   ├── main.py           # 命令行启动入口
│   │   ├── config.py         # 配置文件
│   │   ├── data_processor.py   # ASR数据后处理
│   │   ├── llm_handler.py      # LLM交互处理器
│   │   ├── vlm_handler.py      # VLM交互处理器
│   │   ├── image_processor.py  # 图像处理与筛选
│   │   ├── video_handler.py    # 视频处理
│   │   └── outline_handler.py  # 大纲处理与报告生成
│   └── 📁 devour/
│       └── asr_engine_paraformer_v2.py # ASR引擎实现
├── 📁 input_video/            # 存放待处理的视频文件
├── 📁 output/                 # 存放所有处理结果
├── 📁 models/                 # (可选) 存放本地ASR/VLM模型文件
├── 📄 requirements.txt       # Python 依赖
└── 📄 README.md             # 项目文档
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请参考以下步骤：

1. 🍴 Fork 本项目
2. 🌟 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 💻 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 📤 推送到分支 (`git push origin feature/AmazingFeature`)
5. 🔄 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。