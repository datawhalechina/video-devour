# 🍽️ VideoDevour | 智能视频到报告生成器

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**语言 / Language / 言語**：[简体中文](README.md) · [English](docs/README_EN.md) · [日本語](docs/README_JA.md)

> 🎯 **核心理念**：吃掉视频，输出一份图文并茂的报告！  
> 🚀 基于 ASR + VLM 技术的智能视频分析工具，能够将任何视频"吞噬"并生成包含关键帧图片、内容摘要和视频剪辑的结构化报告。

## 📋 目录

> 📖 本次版本新增能力（双模式 ASR / 设置控制台 / 链接处理 / 学习卡片等）详见 [docs/新功能说明.md](docs/新功能说明.md)
> 🖼️ 图文运行全流程示例（以吴恩达课程为例）详见 [docs/运行模式与使用示例.md](docs/运行模式与使用示例.md)

- [🎯 项目简介](#-项目简介)
- [✨ 核心功能](#-核心功能)
- [🤖 Agent Skill（任意 AI 编码助手可调用）](#-agent-skill任意-ai-编码助手可调用)
- [🖼️ 系统预览](#️-系统预览)
- [🔧 技术架构](#-技术架构)
- [📦 安装指南](#-安装指南)
- [🎛️ 配置](#️-配置)
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
- **中文输出保障**：无论视频原语言是什么，大纲与报告一律输出简体中文（专有名词保留原文）。
- **LLM 限流重试**：限流/超时自动指数退避重试，保证长任务稳定性。

### 🔗 在线视频链接处理（B站 / YouTube / 微信视频号）
- **粘贴链接直接处理**：自动识别平台（可直接粘贴 App 分享文案），预览窗口内嵌官方播放器在线播放，一键下载并进入完整处理流水线。
- **关键词搜索**：内置 B站官方搜索与 YouTube 搜索，封面/时长/UP主卡片式展示。
- **微信视频号**：支持 `weixin.qq.com/sph/...` 分享链接。在设置页填入腾讯元宝 Cookie 后走**直连解析**（元宝解析 → 视频号 feed 接口 → 本地 ISAAC64 解密，无第三方依赖）；也可选配自建解析服务（`WECHAT_RESOLVER_URL`）或使用本地捕获工具（[ltaoo/wx_channels_download](https://github.com/ltaoo/wx_channels_download)）下载后上传处理。
- 由 `yt-dlp` 驱动，含 B站风控退避重试与 YouTube cookies 支持（`YTDLP_COOKIES_FILE`）。

### 🎓 学习增强
- **附加产物可选**：上传/链接处理时可勾选「完成后生成」——思维导图 / 知识图谱 / 学习卡片，勾选才生成（默认不勾，报告完成即结束，最快出结果）；报告页也保留手动生成按钮。
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
# 微信视频号：检查元宝 Cookie / 下载分享链接视频
python3 .agents/skills/videodevour/scripts/devour.py wechat --check
python3 .agents/skills/videodevour/scripts/devour.py wechat "https://weixin.qq.com/sph/..."
# 一键处理：下载 → ASR → 大纲 → 关键帧 → 中文图文报告（同样支持视频号链接）
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
- Python 3.12+（推荐用 [uv](https://docs.astral.sh/uv/) 管理环境与依赖）
- FFmpeg（macOS: `brew install ffmpeg` / Ubuntu: `apt install ffmpeg` / Windows: `winget install ffmpeg`）
- GPU 可选：NVIDIA CUDA 或 Apple Silicon MPS 自动启用，无 GPU 时回退 CPU

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/datawhalechina/video-devour.git
cd video-devour

# 2. 安装依赖（推荐 uv，自动创建 .venv 并按 uv.lock 精确安装）
uv sync

# 或者不用 uv 的话：
pip install -r requirements.txt
```

## 🎛️ 配置

所有配置都在**设置控制台**完成（见下文），无需手动编辑任何配置文件。项目不依赖 `config.py`——缺失时后端会自动使用内置默认值并接入控制台设置。高级用户如需调整输出目录等内部默认值，可参考 `backend/algorithm/config.template.py`（可选，通常不需要）。

## 🚀 快速开始

### 设置控制台（推荐）

启动后在任意页面点击右下角 ⚙ 悬浮按钮（或访问 `/settings`）完成全部配置：

- **语音识别模式**：`离线`（本地 FunASR Paraformer，无需 API）或 `在线`（DashScope / StepFun 云端识别，零模型下载、启动即用）
- **LLM / VLM**：填写 API Key、接口地址（任意 OpenAI 兼容服务）与模型名称，支持常用供应商一键填入，并可一键连通性测试
- **默认学习阶段**：九档可选（自由学习/小学/初中/高中/大学/硕士/博士/深入研究/垂直领域研究）
- **微信视频号**：填入元宝 Cookie 以启用视频号分享链接下载（配置方法见下文）

配置保存在项目根目录的 `settings.json`（已被 gitignore，含密钥请勿提交），并在每次任务执行时注入运行时配置。

### 在线视频链接处理（B站 / YouTube / 微信视频号）

前端「链接处理」页面支持不上传文件、直接通过视频链接生成报告：

- **粘贴链接**：自动识别平台并展示预览窗口（B站用官方播放器嵌入，YouTube 用 embed 播放器），可在线播放预览；直接粘贴 App 分享文案也可以（自动提取其中的纯链接）
- **关键词搜索**：内置 B站（官方搜索接口）与 YouTube（ytsearch）搜索，结果卡片含封面/时长/UP主，点击即预览
- **一键下载处理**：yt-dlp 下载（自动合并 mp4）→ 接入标准处理流水线（ASR → 大纲 → 关键帧 → 报告）

说明：
- B站未登录最高可取 720p 左右画质，高清晰度需自行配置登录态；短时间高频请求可能触发平台风控，服务端已带 cookie 指纹与自动重试
- YouTube 存在 bot 检查：元数据自动回退 oEmbed 获取；下载需在设置控制台配置「YouTube cookies」（或 `YTDLP_COOKIES_FILE` 指向 cookies 文件），也可在设置页「一键读取浏览器 Cookie」自动获取。部分网络环境（数据中心/代理 IP）会被 YouTube 强制 SABR 流限制，需额外安装 PO Token 支持：`bash scripts/install_yt_pot.sh`（依赖 node），并建议更新 yt-dlp 至最新版
- **微信视频号**：粘贴 `weixin.qq.com/sph/...` 分享链接即可（不支持搜索与内嵌预览）。视频号没有公开直链，按优先级走三条链路：
  1. **直连解析（推荐）**：在设置页「微信视频号」填入腾讯元宝 Cookie（配置步骤见下文「[微信视频号 Cookie 配置](#微信视频号-cookie-配置)」），后端调用元宝解析接口换取 exportId+token → 视频号 feed 接口取媒体地址 → 若带 `decodeKey` 则本地 ISAAC64 解密前 128KB（WechatSphDecrypt 算法，已与独立参考实现交叉验证）→ ffprobe 校验。全程无第三方服务
  2. **自建解析服务**：设置页填 `WECHAT_RESOLVER_URL`（可选 Bearer Token），兼容 [ltaoo/wx_channels_download](https://github.com/ltaoo/wx_channels_download) 的 sph worker（支持其 feed 结构返回）
  3. **本地捕获**：解析均失败时的兜底——用 wx_channels_download 桌面工具（依赖微信客户端 + 根证书 + 本地代理，工作流参考 [joeseesun/qiaomu-wx-video](https://github.com/joeseesun/qiaomu-wx-video)）下载到本机后，在「上传视频」页直接处理
- 请确保对所处理的视频内容拥有相应权利或已获得授权，仅用于个人学习用途

### 微信视频号 Cookie 配置

视频号解析依赖腾讯元宝（[yuanbao.tencent.com](https://yuanbao.tencent.com)）的登录态，首次使用配置一次即可（Cookie 一般数周内有效，失效后重新复制更新）：

1. 浏览器打开 [yuanbao.tencent.com](https://yuanbao.tencent.com) 并登录（微信扫码即可）
2. 按 `F12` 打开开发者工具 → 切到 **Network（网络）** 标签 → 刷新页面
3. 在请求列表中点击任意一条发往 `yuanbao.tencent.com` 的请求 → 找到 **Request Headers（请求标头）** 下的 `Cookie:` → 右键/手动复制**完整**值
4. 打开 VideoDevour 设置控制台（主页入口，或任意页面右下角 ⚙ 悬浮按钮）→「微信视频号」→ 粘贴到 **元宝 Cookie** → 保存设置

不走 WebUI 的等价方式（二选一即可）：

- 写入项目根目录 `settings.json`：`"wechat_yuanbao_cookie": "粘贴的Cookie"`
- 设置环境变量：`export YUANBAO_COOKIE="粘贴的Cookie"`

> Cookie 仅保存在本机（`settings.json` 已被 gitignore 排除，页面上脱敏显示），不会上传到任何服务。
> Agent Skill 用户可用 `devour.py wechat --check` 一键验证 Cookie 是否有效；解析报 401 时按上述步骤重新复制即可。

### 学习增强（可选生成）

- **思维导图 / 知识图谱 / 学习卡片**：默认不自动生成——上传或链接处理时按需勾选「完成后生成」，报告完成时自动产出；报告页也保留手动生成按钮
- **导出 Markdown**：报告页一键将大纲与最终报告合并为单个 Markdown 文件下载（本地图片内嵌 base64，离线可看）
- **学习阶段**：九档可选（自由学习为默认通用模式），LLM 生成内容随阶段调整深度
- LLM 调用内置限流自动重试（指数退避 + 随机抖动）

### 启动服务

#### 1. 启动后端服务
在项目根目录下启动后端。

macOS / Linux：
```bash
# 安装依赖并激活虚拟环境
uv sync
source .venv/bin/activate

# 启动后端服务
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

Windows（PowerShell）：
```powershell
uv sync
.venv\Scripts\activate

uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

> 提示：不想激活虚拟环境的话，任何平台都可以直接用 `uv run uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000`（uv 会自动使用 `.venv` 中的环境）。Windows CMD 的激活命令为 `.venv\Scripts\activate.bat`。若 PowerShell 提示脚本被禁止运行，先执行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`。

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
处理位于 `uploads` 文件夹下的 `demo.mp4`：
```bash
python backend/algorithm/main.py "uploads/demo.mp4"
```

程序执行完毕后，所有输出文件，包括日志、ASR结果、视频切片、关键帧图片和最终报告，都将保存在 `output` 目录下，一个以视频名和时间戳命名的新文件夹中。

## 🏗️ 项目结构

```
video-devour/
├── 📁 backend/
│   ├── 📁 algorithm/            # 核心处理算法和流程
│   │   ├── pipeline.py          # 端到端完整处理流程
│   │   ├── main.py              # 命令行启动入口
│   │   ├── settings_store.py    # 运行时设置（settings.json 读写与注入）
│   │   ├── report_viz.py        # 思维导图/知识图谱/学习卡片生成
│   │   ├── config.template.py   # （可选）内部默认值参考模板，通常无需使用
│   │   ├── data_processor.py    # ASR 数据后处理
│   │   ├── llm_handler.py       # LLM 交互（含限流重试/中文输出保障）
│   │   ├── vlm_handler.py       # VLM 交互
│   │   ├── image_processor.py   # 帧处理与关键帧选择
│   │   ├── video_handler.py     # 视频切分与抽帧
│   │   ├── outline_handler.py   # 大纲处理与报告生成
│   │   └── text_similarity_matcher.py  # 标题-文本块语义匹配
│   ├── 📁 api/
│   │   └── main.py              # FastAPI 主应用（全部 API 端点）
│   └── 📁 devour/               # 视频获取与 ASR 引擎
│       ├── video_downloader.py  # 链接下载（B站/YouTube/微信视频号）
│       ├── asr_factory.py       # ASR 引擎工厂（离线/在线切换）
│       ├── asr_engine_paraformer_v2.py  # 本地 FunASR 引擎
│       ├── asr_engine_dashscope.py      # DashScope 在线引擎
│       ├── asr_engine_stepfun.py        # StepFun 在线引擎
│       └── ...                  # 其他引擎实现
├── 📁 frontend/                 # React 前端应用
│   ├── 📁 src/
│   │   ├── 📁 components/       # React 组件（上传/链接/报告/设置等）
│   │   └── 📁 api/              # API 调用封装
│   ├── package.json             # 前端依赖配置
│   └── vite.config.js           # Vite 构建配置
├── 📁 .agents/skills/videodevour/  # Agent Skill（跨 agent 通用入口）
├── 📁 docs/                     # 功能说明与使用示例文档
├── 📁 output/                   # 处理结果输出目录（运行时生成）
├── 📁 models/                   # (可选) 本地 ASR 模型文件
├── 📄 pyproject.toml            # uv 项目配置（Python ≥3.12）
├── 📄 requirements.txt          # pip 依赖（与 pyproject 等价）
└── 📄 README.md                 # 项目文档
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