---
name: videodevour
description: 使用 VideoDevour 把视频（B站/YouTube 链接或本地文件）处理成中文图文报告。当用户要求"处理这个视频"、"视频转笔记/报告/图文大纲"、"下载并总结B站/YouTube视频"时使用。支持搜索视频、查询链接信息、一键生成带关键帧的图文报告。
license: Apache-2.0
compatibility: 需要 Python 3.12+ 与项目 .venv（uv sync），ffmpeg；任何支持 .agents/skills 约定的 agent 均可调用
---

# VideoDevour 视频转图文报告

## Goal

调用 VideoDevour 项目（本仓库），把视频端到端处理为中文图文报告
（ASR 转写 → 大纲 → 视频切分 → 关键帧 → 图文报告），不依赖 Web 界面。

## 必要输入

- **视频来源**：B站/YouTube 链接、或本地视频文件路径（MP4 等）
- 可选：学习阶段（自由学习[默认]/小学/初中/高中/大学/硕士/博士/深入研究/垂直领域研究）

## 使用前检查（首次使用时执行一次）

1. 项目根目录按以下顺序解析（脚本已内置，无需手动指定）：
   `--home 参数` → `VIDEO_DEVOUR_HOME` 环境变量 → 脚本所在仓库 → 默认安装路径。
2. 确认项目虚拟环境已就绪（不存在则执行 `cd <项目目录> && uv sync`，用 Python 3.12）；
   脚本会自动切换到 `.venv` 运行。
3. ASR/LLM/VLM 配置读取项目根目录 `settings.json`；LLM/VLM 需要 key，离线 ASR 需要
   本地模型（`models/iic/` 下四个目录）。缺 key 时提示用户在 WebUI 控制台（`/settings`）填写。

## Workflow

以下 `<skill目录>` 指本 SKILL.md 所在目录（`.agents/skills/videodevour`）。

### 1. 搜索视频（用户只给了关键词时）

```bash
python3 <skill目录>/scripts/devour.py search "关键词" --platform bilibili --max 5
```

输出 JSON 列表（标题/时长/UP主/链接），交给用户选择或选最匹配的一条。

### 2. 查看链接信息（可选，用户想先预览时）

```bash
python3 <skill目录>/scripts/devour.py info "https://www.bilibili.com/video/BV..."
```

输出标题/UP主/时长/封面 JSON。注意：多P合集的 BV 链接，`info` 返回的时长是合集总时长，
而 `process` 只下载并处理**当前分P**（通常几分钟），不会被合集时长吓退。

### 3. 一键处理（核心流程）

```bash
python3 <skill目录>/scripts/devour.py process "https://www.bilibili.com/video/BV..." --level 高中
# 或本地文件：
python3 <skill目录>/scripts/devour.py process /path/to/video.mp4 --level 初中
```

- 命令是同步阻塞的，**bash 超时请设为 600000ms（10分钟）以上**；10 分钟内的视频一般 2-5 分钟完成
- 输出为逐阶段进度日志，成功结束时打印 JSON 结果：
  `{"report": ".../final_report.md", "outline": ".../detailed_outline.md", ...}`
- ASR 模式跟随 `settings.json`（离线=本地 MPS/CPU，在线=DashScope），LLM/VLM 固定走云端

### 4. 生成思维导图与知识图谱（对学习场景推荐）

基于任务报告生成两种知识可视化（LLM 生成、浏览器渲染的交互页面）：

```bash
# 思维导图：三层分支结构（markmap 渲染，可缩放/折叠）
python3 <skill目录>/scripts/devour.py mindmap --latest --open
# 知识图谱：概念关系力导向网络（节点按类别着色、关系标注）
python3 <skill目录>/scripts/devour.py graph --latest --open
# 也可用 --dir 指定任务输出目录、--level 指定学习阶段
```

输出 JSON `{"html": "<输出目录>/mindmap.html", ...}`，将 html 路径呈现给用户（浏览器打开即用）。

### 5. 读取报告

处理完成后读取打印的 `final_report.md` 路径，向用户呈现报告内容摘要（含关键帧图片的相对路径引用）。
也可手动查看：

```bash
python3 <skill目录>/scripts/devour.py report --latest
```

## 推荐组合工作流（一次视频 → 全套学习材料）

```bash
S=<skill目录>/scripts/devour.py
python3 $S process "https://www.bilibili.com/video/BV..." --level 高中   # 1. 下载+处理
python3 $S mindmap --latest --open        # 2. 思维导图（建立框架）
python3 $S graph --latest --open          # 3. 知识图谱（概念关联）
python3 $S report --latest                # 4. 报告全文
```

向用户交付时建议按「报告全文 → 思维导图 → 知识图谱」的顺序呈现：先细节后框架，便于学习理解。

## 注意事项

- 处理产物在 `<项目>/output/frames_*/` 目录，与 WebUI 历史共用（skill 直跑的任务不注册到 WebUI 任务列表）
- 英文视频同样输出中文报告（内部已强制中文），但中文 ASR 模型对英文转写质量有限，内容深度受影响
- B站未登录只能取约 720p；高频调用可能触发平台风控，脚本已内置退避重试
- 仅处理拥有权利或已获授权的视频内容，用于个人学习

## Stop points

- 项目目录/venv 不存在且用户不愿安装 → 停止并说明依赖
- LLM/VLM key 未配置且用户不提供 → 停止（无法生成大纲与报告）
- 视频时长超过 60 分钟 → 先向用户确认再处理
