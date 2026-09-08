# 🍽️ VideoDevour | Turn Any Video into an Illustrated Report

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

**Language / 语言 / 言語**: [简体中文](../README.md) · [English](README_EN.md) · [日本語](README_JA.md)

> 🎯 **Core idea**: Devour the video, output an illustrated report!
> 🚀 An intelligent video analysis tool built on ASR + VLM. It "devours" any video and produces a structured report with keyframe images, content outline, and video clips.

## 📋 Table of Contents

- [🎯 Introduction](#-introduction)
- [✨ Features](#-features)
- [🤖 Agent Skill (works with any AI coding assistant)](#-agent-skill-works-with-any-ai-coding-assistant)
- [🖼️ Screenshots](#️-screenshots)
- [🔧 Tech Stack](#-tech-stack)
- [📦 Installation](#-installation)
- [🎛️ Configuration](#️-configuration)
- [🚀 Quick Start](#-quick-start)
- [🏗️ Project Structure](#️-project-structure)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

> 📖 Chinese-only docs: [新功能说明.md](新功能说明.md) (new features) and [运行模式与使用示例.md](运行模式与使用示例.md) (walkthrough with screenshots).

## 🎯 Introduction

**VideoDevour** focuses on extracting structured reports from videos. It automates the whole pipeline from a raw video to a high-quality illustrated report.

### 💡 Why VideoDevour
> **"Devour a video, output a report."**
> Fully "digest" any video: extract the spoken content and key visuals, and generate a high-quality report containing a text outline, keyframe images, and video clips.

### 🎯 Use Cases
- 📚 **Study notes**: Turn online courses or tutorials into chaptered, illustrated notes with transcripts.
- 📝 **Meeting minutes**: Convert meeting recordings into minutes with chapter summaries, speaker records, and key frames.
- 🎬 **Content creation**: Pull key segments and images from long videos as raw material for re-creation.

## ✨ Features

### 🎙️ Speech Recognition (ASR)
- **Accurate transcription**: Powered by **FunASR Paraformer V2** with automatic punctuation.
- **Speaker separation**: Distinguishes different speakers in the video.
- **Precise timestamps**: Millisecond-level start/end timestamps for every sentence.
- **Dual mode**: Run fully **offline** (local FunASR, no API needed) or **online** (DashScope / StepFun cloud ASR) — switchable in the settings console.

### 📝 Outline Generation & Content Matching
- **Smart outline**: An LLM analyzes the transcript and produces a hierarchical Markdown outline that mirrors the video's logic.
- **Precise matching**: Semantic similarity aligns each transcript chunk to the right outline section.

### 🎬 Video & Image Processing
- **Auto slicing**: **FFmpeg** splits the original video into segments according to the outline.
- **Frame extraction**: Frames are sampled from each segment (e.g. 1 fps).
- **Deduplication**: Visually similar frames are removed to keep only useful information.
- **VLM keyframe selection**: A vision-language model scores the candidate frames and picks the most representative one for each section.

### 📜 Report Generation
- **Illustrated outline**: Combines the text outline with selected keyframes into `detailed_outline.md`.
- **Final report**: A second LLM pass polishes and expands the outline into a richer `final_report.md`.
- **Chinese output guarantee**: Outlines and reports are always written in Simplified Chinese (proper nouns kept), regardless of the video's language.
- **Rate-limit retry**: Exponential backoff with jitter keeps long tasks stable.

### 🔗 Online Video Links (Bilibili / YouTube / WeChat Channels)
- **Paste a link**: The platform is auto-detected (pasting share text from the apps works too). An embedded player lets you preview before one-click download & processing.
- **Keyword search**: Built-in Bilibili (official API) and YouTube search, with cover/duration/uploader cards.
- **WeChat Channels (视频号)**: Supports `weixin.qq.com/sph/...` share links. After pasting a Tencent Yuanbao cookie in the settings page, downloads go through a **direct pipeline** (Yuanbao parse → Channels feed API → local ISAAC64 decryption, no third-party service). A self-hosted resolver (`WECHAT_RESOLVER_URL`) or the desktop capture tool ([ltaoo/wx_channels_download](https://github.com/ltaoo/wx_channels_download)) also works.
- Driven by `yt-dlp`, with Bilibili rate-limit backoff and YouTube cookies support (`YTDLP_COOKIES_FILE`).

### 🎓 Learning Enhancements
- **Optional add-ons**: Mind map / knowledge graph / learning card are **opt-in** — tick "generate when finished" at upload or link processing, or generate manually from the report page anytime.
- **Nine education levels**: Self-paced (default) / Primary / Junior high / Senior high / University / Master's / Doctoral / In-depth research / Vertical-domain research — the content depth adapts accordingly.
- **Learning card**: One-click conversion of the report into a mobile-sized Bento-grid HTML card.
- **Mind map**: An interactive three-level map (zoom/collapse) for a quick overview.
- **Knowledge graph**: Concepts and relations rendered as a force-directed network (color-coded categories, labeled edges, hover for details).
- **Markdown export**: Merges outline + report into a single `.md` file with base64-embedded images — fully offline-readable.

### 🤖 Agent Skill (works with any AI coding assistant)

The core capabilities are packaged as a skill following the open [Agent Skills](https://agentskills.io) convention (`.agents/skills`). Any conforming agent — Codex, Claude Code, Cursor, etc. — can call it directly without the web UI:

```bash
# Search videos
python3 .agents/skills/videodevour/scripts/devour.py search "keyword" --platform bilibili
# Get link metadata (title/uploader/duration/cover)
python3 .agents/skills/videodevour/scripts/devour.py info "https://www.bilibili.com/video/BV..."
# WeChat Channels: check the Yuanbao cookie / download a share link
python3 .agents/skills/videodevour/scripts/devour.py wechat --check
python3 .agents/skills/videodevour/scripts/devour.py wechat "https://weixin.qq.com/sph/..."
# One-click processing: download → ASR → outline → keyframes → illustrated report
python3 .agents/skills/videodevour/scripts/devour.py process "https://www.bilibili.com/video/BV..." --level 高中
# Read the latest report
python3 .agents/skills/videodevour/scripts/devour.py report --latest
```

- Education levels: Self-paced (default) / Primary / Junior high / Senior high / University / Master's / Doctoral / In-depth research / Vertical-domain research
- The script automatically re-executes inside the project `.venv`; the project root is resolved via `--home` → `VIDEO_DEVOUR_HOME` → script location.
- Local install: `ln -s <repo>/.agents/skills/videodevour ~/.agents/skills/videodevour`
- `process` is blocking; agents should use a timeout of 10 minutes or more.

## 🖼️ Screenshots

All screenshots come from a full run on the Bilibili video [Andrew Ng's Agentic AI course, part 1](https://www.bilibili.com/video/BV1DfrdByE2H)
(see [docs/运行模式与使用示例.md](运行模式与使用示例.md) for the complete illustrated walkthrough; the page is in Chinese).

**Paste a Bilibili/YouTube link, preview in an embedded player, one-click download & process:**

![Link processing](images/05-链接预览.png)

**Real-time pipeline progress (download → transcribe → outline → keyframes → report):**

![Processing progress](images/04-处理进度.png)

**Illustrated outline: the VLM picks the most representative frame for every section:**

![Illustrated outline](images/06-图文大纲-关键帧.png)

**AI learning card: the report becomes a mobile-sized Bento-grid review card:**

![Learning card](images/08-学习卡片.png)

**Mind map: the course content as a zoomable/collapsible three-level tree:**

![Mind map](images/09-思维导图.png)

**Knowledge graph: concepts and relations as a force-directed network:**

![Knowledge graph](images/10-知识图谱.png)

## 🔧 Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Core pipeline** | Python | Main language. |
| **Speech recognition** | FunASR (Paraformer V2) | Alibaba's open-source high-accuracy ASR model. |
| **LLM/VLM access** | Camel-AI | Lightweight framework for LLM and VLM interaction. |
| **Video/image processing** | FFmpeg, OpenCV | Video slicing, frame extraction, image processing. |
| **Text matching** | Sentence Transformers | Semantic text similarity. |

## 📦 Installation

### Requirements
- Python 3.12+ ([uv](https://docs.astral.sh/uv/) recommended for environment/dependency management)
- FFmpeg (`brew install ffmpeg` / `apt install ffmpeg`)
- GPU optional: NVIDIA CUDA or Apple Silicon MPS is auto-detected; falls back to CPU.

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/datawhalechina/video-devour.git
cd video-devour

# 2. Install dependencies (uv recommended — creates .venv and installs from uv.lock)
uv sync

# Or without uv:
pip install -r requirements.txt
```

## 🎛️ Configuration

The **settings console** is the recommended way to configure everything (see below) — no file editing required. If you prefer manual configuration, copy `backend/algorithm/config.template.py` to `config.py` and edit it; API keys can also be injected via the `LLM_API_KEY` / `VLM_API_KEY` environment variables.

## 🚀 Quick Start

### Settings console (recommended)

After starting the services, click the ⚙ floating button at the bottom-right of any page (or open `/settings`):

- **ASR mode**: `Offline` (local FunASR Paraformer, no API) or `Online` (DashScope / StepFun cloud, zero model downloads)
- **LLM / VLM**: API key, base URL (any OpenAI-compatible service), and model name — with one-click provider presets and connectivity tests
- **Default education level**: nine levels (Self-paced / Primary / … / Vertical-domain research)
- **WeChat Channels**: paste the Yuanbao cookie to enable Channels share-link downloads (see below)

Settings are stored in `settings.json` at the project root (gitignored — never commit secrets) and injected at each task run. The backend starts even if `backend/algorithm/config.py` is missing.

### Online video links (Bilibili / YouTube / WeChat Channels)

The "Link processing" page builds reports directly from a URL — no file upload needed:

- **Paste a link**: platform auto-detected with an embedded preview player; share text from the apps works too.
- **Keyword search**: Bilibili (official API) and YouTube; result cards show cover/duration/uploader.
- **One-click download & process**: yt-dlp download (auto-merged mp4) → standard pipeline (ASR → outline → keyframes → report).

Notes:
- Bilibili without login caps at ~720p; high-frequency requests may trigger risk control (cookie fingerprint + retries built in).
- YouTube has bot checks: metadata falls back to oEmbed; downloads need exported cookies (Netscape format) via `YTDLP_COOKIES_FILE`.
- **WeChat Channels**: paste a `weixin.qq.com/sph/...` share link (no search or embedded preview). Channels have no public direct URL, so three paths are tried in order:
  1. **Direct resolution (recommended)**: paste a Tencent Yuanbao cookie in the settings page (see "[WeChat Channels cookie setup](#wechat-channels-cookie-setup)"). The backend calls the Yuanbao parse API for an exportId+token → the Channels feed API for the media URL → if a `decodeKey` is present, the first 128 KB are decrypted locally with ISAAC64 (WechatSphDecrypt algorithm, cross-verified against an independent implementation) → validated with ffprobe. No third-party service involved.
  2. **Self-hosted resolver**: set `WECHAT_RESOLVER_URL` (optional Bearer token) — compatible with the sph worker of [ltaoo/wx_channels_download](https://github.com/ltaoo/wx_channels_download).
  3. **Local capture**: fall back to the wx_channels_download desktop tool (requires the WeChat desktop client + root certificate + local proxy; workflow reference [joeseesun/qiaomu-wx-video](https://github.com/joeseesun/qiaomu-wx-video)), then upload the downloaded file.
- Only process content you own or are authorized to use, for personal learning.

### WeChat Channels cookie setup

Channels resolution relies on a logged-in Tencent Yuanbao ([yuanbao.tencent.com](https://yuanbao.tencent.com)) session. Configure once; the cookie typically lasts a few weeks:

1. Open [yuanbao.tencent.com](https://yuanbao.tencent.com) in a browser and sign in (WeChat scan works).
2. Press `F12` to open developer tools → **Network** tab → refresh the page.
3. Click any request to `yuanbao.tencent.com` → copy the **full** value of the `Cookie:` field under Request Headers.
4. Open the VideoDevour settings console (⚙ floating button on any page) → "WeChat Channels" → paste into **Yuanbao Cookie** → save.

Without the web UI (either one):

- Write it to `settings.json` at the project root: `"wechat_yuanbao_cookie": "<cookie>"`
- Or set an environment variable: `export YUANBAO_COOKIE="<cookie>"`

> The cookie stays on your machine (`settings.json` is gitignored; the UI masks it) and is never uploaded anywhere.
> Agent Skill users can verify the cookie with `devour.py wechat --check`; on a 401 error, re-copy as above.

### Learning enhancements (optional)

- **Mind map / knowledge graph / learning card**: **not** generated by default — tick "generate when finished" during upload or link processing, or generate manually from the report page anytime.
- **Markdown export**: merges outline + report into a single `.md` download (base64-embedded images, offline-readable).
- **Education levels**: nine levels (Self-paced is the general default); LLM output depth adapts accordingly.
- LLM calls retry automatically on rate limits (exponential backoff + jitter).

### Start the services

#### 1. Backend
From the project root:
```bash
# Install deps and activate the virtualenv
uv sync
source .venv/bin/activate

# Start the backend
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

The backend runs at `http://localhost:8000`.

#### 2. Frontend
In a new terminal:
```bash
cd frontend
npm run dev
```

The frontend runs at `http://localhost:3000`.

### Using the web UI

1. **Upload a video**: select or drag & drop files on the main page.
2. **Monitor processing**: the page switches automatically and shows live progress and timings.
3. **View the report**: when finished, you are taken to the illustrated report.
4. **History**: manage all past tasks from the history page.

### Command line (optional)

To process a video directly from the CLI:

```bash
python backend/algorithm/main.py "path/to/your/video.mp4"
```

All outputs (logs, ASR results, video clips, keyframes, and the final report) are written to a timestamped folder under `output/`.

## 🏗️ Project Structure

```
video-devour/
├── 📁 backend/
│   ├── 📁 algorithm/            # Core processing algorithms & pipeline
│   │   ├── pipeline.py          # End-to-end processing pipeline
│   │   ├── main.py              # CLI entry point
│   │   ├── settings_store.py    # Runtime settings (settings.json read/write & injection)
│   │   ├── report_viz.py        # Mind map / knowledge graph / learning card generation
│   │   ├── config.template.py   # Manual-config template (config.py is gitignored)
│   │   ├── data_processor.py    # ASR post-processing
│   │   ├── llm_handler.py       # LLM handler (retry / Chinese-output guarantee)
│   │   ├── vlm_handler.py       # VLM handler
│   │   ├── image_processor.py   # Frame processing & keyframe selection
│   │   ├── video_handler.py     # Video slicing & frame extraction
│   │   ├── outline_handler.py   # Outline processing & report generation
│   │   └── text_similarity_matcher.py  # Heading-to-chunk semantic matching
│   ├── 📁 api/
│   │   └── main.py              # FastAPI app (all API endpoints)
│   └── 📁 devour/               # Video acquisition & ASR engines
│       ├── video_downloader.py  # Link downloads (Bilibili/YouTube/WeChat Channels)
│       ├── asr_factory.py       # ASR engine factory (offline/online switching)
│       ├── asr_engine_paraformer_v2.py  # Local FunASR engine
│       ├── asr_engine_dashscope.py      # DashScope online engine
│       ├── asr_engine_stepfun.py        # StepFun online engine
│       └── ...                  # Other engines
├── 📁 frontend/                 # React frontend
│   ├── 📁 src/
│   │   ├── 📁 components/       # React components (upload/link/report/settings)
│   │   └── 📁 api/              # API client helpers
│   ├── package.json             # Frontend dependencies
│   └── vite.config.js           # Vite build config
├── 📁 .agents/skills/videodevour/  # Agent Skill (cross-agent entry point)
├── 📁 docs/                     # Feature notes & usage walkthroughs
├── 📁 output/                   # Processing results (created at runtime)
├── 📁 models/                   # (Optional) local ASR model files
├── 📄 pyproject.toml            # uv project config (Python ≥3.12)
├── 📄 requirements.txt          # pip dependencies (equivalent)
└── 📄 README.md                 # Project docs (Chinese)
```

## 🤝 Contributing

All kinds of contributions are welcome!

1. 🍴 Fork this project
2. 🌟 Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. 💻 Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. 📤 Push to the branch (`git push origin feature/AmazingFeature`)
5. 🔄 Open a Pull Request

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](../LICENSE) file for details.
