# 🍽️ VideoDevour | 智能视频到报告生成器

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🎯 **核心理念**：吃掉视频，输出一份图文并茂的报告！  
> 🚀 基于 ASR + VLM 技术的智能视频分析工具，能够将任何视频"吞噬"并生成包含关键帧图片、内容摘要和视频剪辑的结构化报告。

## 📋 目录

> 📖 本次版本新增能力（双模式 ASR / 设置控制台 / 链接处理 / 学习卡片等）详见 [docs/新功能说明.md](docs/新功能说明.md)
> 🖼️ 图文运行全流程示例（以吴恩达课程为例）详见 [docs/运行模式与使用示例.md](docs/运行模式与使用示例.md)

- [🍽️ VideoDevour | 智能视频到报告生成器](#️-videodevour--智能视频到报告生成器)
  - [📋 目录](#-目录)
  - [🎯 项目简介](#-项目简介)
    - [💡 核心价值](#-核心价值)
    - [🎯 应用场景](#-应用场景)
  - [✨ 核心功能](#-核心功能)
    - [🎙️ 语音识别 (ASR)](#️-语音识别-asr)
    - [📝 大纲生成与内容匹配](#-大纲生成与内容匹配)
    - [🎬 视频与图像处理](#-视频与图像处理)
    - [📜 报告生成](#-报告生成)
  - [🔧 技术架构](#-技术架构)
  - [📦 安装指南](#-安装指南)
    - [环境要求](#环境要求)
    - [安装步骤](#安装步骤)
  - [🎛️ 模型概览与配置](#️-模型概览与配置)
  - [🚀 快速开始](#-快速开始)
    - [执行处理流程](#执行处理流程)
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
- **中文输出保障**：无论视频原语言是什么，大纲与报告一律输出简体中文（专有名词保留原文）。
- **LLM 限流重试**：限流/超时自动指数退避重试，保证长任务稳定性。

### 🔗 在线视频链接处理（B站 / YouTube）
- **粘贴链接直接处理**：自动识别平台，预览窗口内嵌官方播放器在线播放，一键下载并进入完整处理流水线。
- **关键词搜索**：内置 B站官方搜索与 YouTube 搜索，封面/时长/UP主卡片式展示。
- 由 `yt-dlp` 驱动，含 B站风控退避重试与 YouTube cookies 支持（`YTDLP_COOKIES_FILE`）。

### 🎓 学习增强
- **学习阶段**：九档可选——自由学习（默认）/ 小学 / 初中 / 高中 / 大学 / 硕士 / 博士 / 深入研究 / 垂直领域研究，内容深度随之调整。
- **学习卡片**：一键将报告转换为手机尺寸 Bento Grid 风格 HTML 学习卡片。
- **思维导图**：报告自动整理为三层分支结构的交互式导图（缩放/折叠），快速建立整体框架。
- **知识图谱**：自动抽取课程概念与关系，渲染力导向网络图（节点按类别着色、关系标注、悬停查看说明）。
- **导出 Markdown**：大纲+报告合并导出，图片内嵌 base64，单文件即可本地查阅。

### 🤖 Agent Skill（任意 AI 编码助手可调用）

项目核心能力已封装为遵循 [Agent Skills](https://agentskills.io) 开放约定（`.agents/skills`）的技能，
Codex / Claude Code / Cursor 等任何支持该约定的 agent 均可直接调用，无需启动 Web 界面：

```bash
# 搜索视频
python3 .agents/skills/videodevour/scripts/devour.py search "关键词" --platform bilibili
# 查看链接信息（标题/UP主/时长/封面）
python3 .agents/skills/videodevour/scripts/devour.py info "https://www.bilibili.com/video/BV..."
# 一键处理：下载 → ASR → 大纲 → 关键帧 → 中文图文报告
python3 .agents/skills/videodevour/scripts/devour.py process "https://www.bilibili.com/video/BV..." --level 高中
# 读取最新报告
python3 .agents/skills/videodevour/scripts/devour.py report --latest
```

- 学习阶段可选：自由学习（默认）/ 小学 / 初中 / 高中 / 大学 / 硕士 / 博士 / 深入研究 / 垂直领域研究
- 脚本自动切换到项目 `.venv` 运行；项目根按 `--home` → `VIDEO_DEVOUR_HOME` → 脚本位置 自动解析
- 本机安装：软链到用户级技能目录 `ln -s <repo>/.agents/skills/videodevour ~/.agents/skills/videodevour`
- `process` 为同步阻塞命令，agent 调用时请将超时设为 10 分钟以上

## 🖼️ 系统预览

以下截图来自一次完整运行：以 B站视频 [吴恩达 Agentic AI 课程 p1](https://www.bilibili.com/video/BV1DfrdByE2H) 为例
（完整图文流程见 [docs/运行模式与使用示例.md](docs/运行模式与使用示例.md)）。

**粘贴 B站 / YouTube 链接，内嵌播放器在线预览，一键下载处理：**

![链接处理](docs/images/05-链接预览.png)

**处理过程八阶段实时可视（下载 → 转写 → 大纲 → 关键帧 → 报告）：**

![处理进度](docs/images/04-处理进度.png)

**图文大纲：VLM 为每个章节挑选最具代表性的视频画面：**

![图文大纲](docs/images/06-图文大纲-关键帧.png)

**AI 学习卡片：报告一键转换为手机尺寸 Bento Grid 复习卡片：**

![学习卡片](docs/images/08-学习卡片.png)

**思维导图：课程内容整理为三层分支结构，可缩放/折叠，快速建立整体框架：**

![思维导图](docs/images/09-思维导图.png)

**知识图谱：自动抽取概念与关系构建力导向网络（节点按类别着色、边标注关系、悬停看说明）：**

![知识图谱](docs/images/10-知识图谱.png)

> 更多截图（首页 / 设置控制台 / 上传页 / 精简报告）见 [docs/运行模式与使用示例.md](docs/运行模式与使用示例.md)。

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

## 🎛️ 模型概览与配置
```
# config.py

# LLM 配置
LLM_MODEL_TYPE = "deepseek-chat"
LLM_API_URL = "https://api.deepseek.com"
LLM_TEMPERATURE = 0.4
LLM_TOKEN_COUNTER = 128000

# VLM 配置
VLM_MODEL_TYPE = "doubao-seed-1-6-flash-250828"
VLM_API_URL = "https://ark.cn-beijing.volces.com/api/v3"
```

## 🚀 快速开始

项目现在提供了完整的Web界面，包括前端和后端服务。出于安全保护，需要提前将**API_KEY**注入环境变量，而不是直接在代码中硬编码。

### 环境变量配置
```bash
echo "export LLM_API_KEY=your-llm-api-key" >> ~/.bashrc
echo "export VLM_API_KEY=your-vlm-api-key" >> ~/.bashrc
source ~/.bashrc
```

### 设置控制台（推荐）

也可以不修改任何配置文件，启动后在前端页面点击「控制台」（或访问 `/settings`）完成全部配置：

- **语音识别模式**：`离线`（本地 FunASR Paraformer，无需 API）或 `在线`（DashScope 云端识别，零模型下载、启动即用）
- **LLM / VLM**：填写 API Key、接口地址（任意 OpenAI 兼容服务）与模型名称，并可一键连通性测试
- **默认学习阶段**：小学 / 初中 / 高中，影响大纲与报告的语言风格

配置保存在项目根目录的 `settings.json`（已被 gitignore，含密钥请勿提交），并会在每次任务执行时注入运行时配置；`backend/algorithm/config.py` 缺失时后端也可直接启动。`config.template.py` 为手动配置的参考模板（`cp config.template.py config.py`）。

### 在线视频链接处理（B站 / YouTube）

前端「链接处理」页面支持不上传文件、直接通过视频链接生成报告：

- **粘贴链接**：自动识别平台并展示预览窗口（B站用官方播放器嵌入，YouTube 用 embed 播放器），可在线播放预览
- **关键词搜索**：内置 B站（官方搜索接口）与 YouTube（ytsearch）搜索，结果卡片含封面/时长/UP主，点击即预览
- **一键下载处理**：yt-dlp 下载（自动合并 mp4）→ 接入标准处理流水线（ASR → 大纲 → 关键帧 → 报告）

说明：
- B站未登录最高可取 720p 左右画质，高清晰度需自行配置登录态；短时间高频请求可能触发平台风控，服务端已带 cookie 指纹与自动重试
- YouTube 存在 bot 检查：元数据自动回退 oEmbed 获取；下载需浏览器导出 cookies（Netscape 格式）并设置环境变量 `YTDLP_COOKIES_FILE` 指向该文件
- 请确保对所处理的视频内容拥有相应权利或已获得授权，仅用于个人学习用途

### 学习卡片与导出

- 报告页新增「生成学习卡片」：由 LLM 将报告转换为手机尺寸的 Bento Grid 风格 HTML 学习卡片
- 报告页新增「导出 Markdown」：将大纲与最终报告合并为单个 Markdown 文件下载
- 上传视频时可选择学习阶段（小学/初中/高中），LLM 生成内容会相应调整深度
- LLM 调用内置限流自动重试（指数退避 + 随机抖动）

### 启动服务

#### 1. 启动后端服务
在项目根目录下，使用 `uv` 激活虚拟环境并启动后端：
```bash
# 激活虚拟环境
uv sync
source .venv/bin/activate

# 启动后端服务
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 `http://localhost:8000` 启动。

#### 2. 启动前端服务
在新的终端窗口中，启动前端开发服务器：
```bash
cd frontend
npm run dev
```

前端服务将在 `http://localhost:3000` 启动。

### Web界面使用

1. **上传视频**：在主页面选择或拖拽视频文件进行上传
2. **处理监控**：上传后自动跳转到处理页面，实时显示处理进度和耗时
3. **查看报告**：处理完成后自动跳转到报告页面，查看生成的图文报告
4. **历史记录**：在历史记录页面管理所有已处理的视频任务

### 命令行使用（可选）

如果需要直接通过命令行处理视频：

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
│   ├── 📁 api/               # Web API 接口
│   │   ├── main.py           # FastAPI 主应用
│   │   ├── routes/           # API 路由
│   │   └── models/           # 数据模型
│   └── 📁 devour/
│       └── asr_engine_paraformer_v2.py # ASR引擎实现
├── 📁 frontend/              # React 前端应用
│   ├── 📁 src/
│   │   ├── 📁 components/    # React 组件
│   │   ├── 📁 api/           # API 调用
│   │   └── 📁 utils/         # 工具函数
│   ├── package.json          # 前端依赖配置
│   └── vite.config.js        # Vite 构建配置
├── 📁 input_video/            # 存放待处理的视频文件
├── 📁 output/                 # 存放所有处理结果
├── 📁 models/                 # (可选) 存放本地ASR/VLM模型文件
├── 📄 requirements.txt       # Python 依赖
├── 📄 pyproject.toml         # uv 项目配置
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