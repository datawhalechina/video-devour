---
name: videodevour
description: 使用 VideoDevour 把视频（B站/YouTube/抖音链接、微信视频号分享链接或本地文件）处理成中文图文报告。当用户要求"处理这个视频"、"视频转笔记/报告/图文大纲"、"下载并总结B站/YouTube/抖音/视频号视频"时使用。支持搜索视频、查询链接信息、一键生成带关键帧的图文报告（精简/详细），改写成量子速读/公众号文章/小红书笔记、导出 PDF，生成学习测试题（单选/多选/判断，判题与学习评估），并可检索项目本地已积累的文档库（历史任务报告/笔记，支持 BM25 搜索与导出，也可通过 MCP 服务供其他 LLM 调用）。
license: Apache-2.0
compatibility: 需要 Python 3.12+ 与项目 .venv（uv sync），ffmpeg；任何支持 .agents/skills 约定的 agent 均可调用
---

# VideoDevour 视频转图文报告

## Goal

调用 VideoDevour 项目（本仓库），把视频端到端处理为中文图文报告
（ASR 转写 → 大纲 → 视频切分 → 关键帧 → 图文报告），不依赖 Web 界面。
产出三层内容：**图文大纲 / 精简报告（结论先行）/ 详细报告（完整原文+笔记对照）**；
可按需改写成**量子速读 / 公众号文章 / 小红书笔记**，并导出 **PDF**。
项目同时把每次任务的产物沉淀为**本地文档库**，可跨任务检索复用（见第 11 节）。

## 必要输入

- **视频来源**：B站/YouTube/抖音链接、微信视频号分享链接（weixin.qq.com/sph/...，可直接粘贴含链接的分享文案）、或本地视频文件路径（MP4 等）
- 可选：学习阶段（自由学习[默认]/小学/初中/高中/大学/硕士/博士/深入研究/垂直领域研究）

## 使用前检查（首次使用时执行一次）

1. 项目根目录按以下顺序解析（脚本已内置，无需手动指定）：
   `--home 参数` → `VIDEO_DEVOUR_HOME` 环境变量 → 脚本所在仓库 → 默认安装路径。
2. 确认项目虚拟环境已就绪（不存在则执行 `cd <项目目录> && uv sync`，用 Python 3.12）；
   脚本会自动切换到 `.venv` 运行。
3. ASR/LLM/VLM 配置读取项目根目录 `settings.json`；LLM/VLM 需要 key。
   **ASR 默认走在线（云端识别，零模型下载）**；仅当用户要用本地离线 ASR 时，才需下载
   约 2GB 模型：设置页切到「离线」会显示自检结果与安装命令，或执行
   `bash scripts/install_offline_asr.sh`。缺 key 时提示用户在 WebUI 控制台（`/settings`）填写。
4. 导出 PDF 依赖 `reportlab`（已写入 `requirements.txt` / `requirements-lite.txt`），
   执行过 `uv sync` 即可用。

## Workflow

以下 `<skill目录>` 指本 SKILL.md 所在目录（`.agents/skills/videodevour`）。

### 1. 搜索视频（用户只给了关键词时）

```bash
# B站（默认）
python3 <skill目录>/scripts/devour.py search "关键词" --platform bilibili --max 5
# YouTube
python3 <skill目录>/scripts/devour.py search "关键词" --platform youtube --max 5
# 抖音（需要登录 Cookie，见第 4 节）
python3 <skill目录>/scripts/devour.py search "关键词" --platform douyin --max 5
```

输出 JSON 列表（标题/时长/UP主/链接），交给用户选择或选最匹配的一条。

- **抖音搜索需要登录态 Cookie**（匿名会返回「请先登录」）。未配置时脚本会明确提示；
  抖音另有 `a_bogus` 浏览器签名校验，若接口触发人机校验，脚本会给出「改用浏览器搜索后
  粘贴链接」的引导，而非静默返回空结果。
- 微信视频号不支持搜索，只能粘贴分享链接（见第 3 节）。

### 2. 查看链接信息（可选，用户想先预览时）

```bash
python3 <skill目录>/scripts/devour.py info "https://www.bilibili.com/video/BV..."
```

输出标题/UP主/时长/封面 JSON。注意：多P合集的 BV 链接，`info` 返回的时长是合集总时长，
而 `process` 只下载并处理**当前分P**（通常几分钟），不会被合集时长吓退。

### 3. 微信视频号（weixin.qq.com/sph/... 分享链接）

```bash
# 首次使用先检查元宝 Cookie（视频号解析依赖腾讯元宝接口登录态）
python3 <skill目录>/scripts/devour.py wechat --check
# 下载视频号视频到项目 uploads/（仅下载，返回 JSON：file_path/title/uploader）
python3 <skill目录>/scripts/devour.py wechat "https://weixin.qq.com/sph/..."
# 也可直接粘贴含链接的分享文案；下载后接 process 本地文件即得图文报告
```

- Cookie 未配置/失效时 `--check` 会明确返回并给出配置指引；配置方法见 README
  「微信视频号 Cookie 配置」一节（WebUI 设置页或 settings.json / 环境变量均可）
- `process` 命令同样直接支持视频号链接（自动先下载再处理），`wechat` 用于只要视频文件的场景
- 直播回放、已过期分享链接无法解析；解析失败会返回中文引导

### 4. 抖音（douyin.com/video/{id}、v.douyin.com 短链）

```bash
# 检查抖音登录 Cookie 是否已配置
python3 <skill目录>/scripts/devour.py douyin --check
# 下载抖音视频到项目 uploads/（仅下载，返回 JSON：file_path/title/uploader）
python3 <skill目录>/scripts/devour.py douyin "https://www.douyin.com/video/7624464836100967732"
# 短链与分享文案均可（自动跟随重定向、提取链接）
python3 <skill目录>/scripts/devour.py douyin "https://v.douyin.com/xxxxxx/"
```

- **下载需要登录态 Cookie**：在设置页「抖音 cookies」填写，或点「一键读取浏览器 Cookie」
  自动获取（需浏览器已登录抖音）；也可写入 `settings.json` 的 `douyin_cookies`。
  Cookie 缺失或失效时，脚本返回明确的配置指引（yt-dlp 会提示 Fresh cookies are needed）。
- 支持三种链接形态：`douyin.com/video/{id}` 视频页、`douyin.com/note/{id}` 图文、
  含 `?modal_id={id}` 的搜索页链接、`v.douyin.com` 短链（脚本自动归一化）。
- 下载默认取 720p H.264（抖音的 bytevc1/H.265 直链会 403，脚本已固定选 H.264 格式）。
- `process` 命令同样直接支持抖音链接（自动先下载再处理）；`douyin` 用于只要视频文件的场景。

### 5. 字幕速记（B站/YouTube，秒级纯文本笔记）

不下载视频、不走 ASR：直接读取平台已有字幕（B站 AI 字幕轨 / YouTube 手动或自动字幕），
LLM 整理为纯文本要点笔记。适合"只要文字内容、要快"的场景。

```bash
python3 <skill目录>/scripts/devour.py notes "https://www.bilibili.com/video/BV..." --level 高中
```

输出 JSON：`notes` 为 Markdown 笔记全文（含 ` ```mermaid ` 概念关系图）、
`file`（.txt 纯文本）/ `md_file`（.md 含关系图）落盘路径。注意：视频没有字幕轨时
报错并建议改走 `process` 完整流程；YouTube 无 cookies 或被 bot 检查拦截时提示配置
「YouTube cookies」（设置控制台，可一键读取浏览器 Cookie）。

### 6. 一键处理（核心流程）

```bash
python3 <skill目录>/scripts/devour.py process "https://www.bilibili.com/video/BV..." --level 高中
# 或抖音 / 视频号 / 本地文件：
python3 <skill目录>/scripts/devour.py process "https://www.douyin.com/video/..." --level 高中
python3 <skill目录>/scripts/devour.py process /path/to/video.mp4 --level 初中
```

- 命令是同步阻塞的，**bash 超时请设为 600000ms（10分钟）以上**；10 分钟内的视频一般 2-5 分钟完成
  （90 分钟以上的长视频，详细报告分段生成需 10 分钟以上，请把超时再放大）
- **下载缓存**：同一视频之前下载过会直接复用本地文件（`<数据根>/downloads/`，映射表
  `index.json` 记录来源 URL/平台/标题/命中次数），不重复下载；换链接形式（短链/搜索页链接）
  也能命中同一缓存（按「平台+视频ID」为键）。
- 处理前会自动把视频压到 **720p / 10fps / H.264** 再转写与抽帧（省时省存储）；压缩结果大于原文件时保留原文件
- 输出为逐阶段进度日志，成功结束时打印 JSON 结果，关键字段：
  - `report`：精简报告（结论先行，快速阅读）
  - `detailed_report`：详细报告（**完整视频原文 + 整理笔记**对照，原文不截断）
  - `outline`：图文大纲（章节 + 关键帧）
  - `keyframes`：关键帧图片路径数组
  - `media_profile`：压缩前后体积与分辨率（确认存储收益时看这个）
  - `styles`：已生成的衍生文体（未生成时不出现，见第 8 节）
- ASR 模式跟随 `settings.json`（**默认在线** DashScope/StepFun；离线=本地 MPS/CUDA/CPU，
  需先装模型），LLM/VLM 固定走云端
- 关键帧策略：按大纲章节**均匀采样固定帧数**（默认每章 10 帧，`VIDEO_DEVOUR_FRAMES_PER_CHAPTER`
  可调），再由 VLM 评分挑选每章最佳一张——不随视频长短暴增候选帧
- **思维导图/知识图谱/学习卡片默认不生成**（为不需要的用户节省时间）。用户明确需要时，
  加 `--extras "mindmap,graph,card"`（可任选其一或多个，逗号分隔）在报告完成后一次生成；
  也可事后用 `mindmap` / `graph` 子命令单独生成。**不要在用户未要求时主动生成**

### 7. 生成思维导图与知识图谱（仅用户需要时）

基于任务报告生成两种知识可视化（LLM 生成、浏览器渲染的交互页面）：

```bash
# 思维导图：三层分支结构（markmap 渲染，可缩放/折叠）
python3 <skill目录>/scripts/devour.py mindmap --latest --open
# 知识图谱：概念关系力导向网络（节点按类别着色、关系标注）
python3 <skill目录>/scripts/devour.py graph --latest --open
# 也可用 --dir 指定任务输出目录、--level 指定学习阶段
```

输出 JSON `{"html": "<输出目录>/mindmap.html", ...}`，将 html 路径呈现给用户（浏览器打开即用）。
若在 `process` 时已用 `--extras` 生成过，直接使用输出 JSON 中 extras 里的路径，无需重复生成。

### 8. 衍生文体：量子速读 / 公众号文章 / 小红书笔记（仅用户需要时）

把已有报告改写成可直接发布的成品文案（**不是分析报告**，基于精简报告改写，事实不跑偏）。
**不在处理流程里预生成**，按需生成并落盘缓存，重复调用直接复用。

```bash
S=<skill目录>/scripts/devour.py
# 三种全部生成（默认）
python3 $S styles --latest
# 只生成某一种
python3 $S styles --latest --kind xiaohongshu
# 指定任务目录
python3 $S styles --dir "<输出目录>" --kind quantum,wechat
```

- `quantum` 量子速读：30 秒看懂大意 + 一句可直接发朋友圈的话
- `wechat` 公众号文章：图文成稿（保留关键帧配图），可直接发布
- `xiaohongshu` 小红书笔记：emoji 分点的图文笔记，含话题标签

输出 JSON `{"styles": {"quantum": {"label": "...", "file": "..."}, ...}}`。
**用户没要求就不要主动生成**（每次约 10-30 秒）。

### 9. 导出 PDF（仅用户需要时）

```bash
python3 $S pdf --latest                        # 精简报告（默认）
python3 $S pdf --latest --type detailed        # 详细报告
python3 $S pdf --latest --type all             # 大纲+精简+详细 合并
python3 $S pdf --latest --out ~/Desktop/report.pdf   # 指定输出路径
```

服务端用 reportlab 排版（**内置中文字体**，不依赖浏览器/pandoc），关键帧图片内嵌。
输出 JSON `{"pdf": "...", "type": "...", "bytes": N}`。同样**按需使用**。

### 10. 读取报告

处理完成后读取打印的 `report` / `detailed_report` 路径，向用户呈现内容摘要。
默认看精简报告；要看**完整原文对照**用 `--type detailed`：

```bash
python3 <skill目录>/scripts/devour.py report --latest                # 精简报告
python3 <skill目录>/scripts/devour.py report --latest --type detailed # 详细报告（原文+笔记）
```

### 11. 检索本地文档库（复用历史任务成果）

项目把每次任务的产物沉淀为**本地文档库**（含 WebUI 历史 + skill 直跑的任务）。
当用户想要的内容**之前已处理过**、或问题可以在已有笔记里找到答案时，先检索文档库，
再决定是否重新处理视频，能省下大量时间。

```bash
S=<skill目录>/scripts/devour.py
# BM25 相关度检索（中英文混合），返回 doc_id/scope/相关度/摘要
python3 $S library search "沙箱隔离" --scope all --top 5
# 无关键词浏览全部（可按 scope 过滤）
python3 $S library list --scope report
# 按 doc_id + scope 取全文 Markdown（直接打印）
python3 $S library get <doc_id> --scope report
# 同一视频多次处理有多个版本时用 --run-id 指定
python3 $S library get <doc_id> --scope detailed --run-id <run_id>
# 导出单篇为 ZIP（md + 引用图片） / 导出整库
python3 $S library export <doc_id> --scope report --out ~/Desktop
python3 $S library export-all --out ~/Desktop
```

- `scope` 取值：`all`（默认）/ `outline` 图文大纲 / `report` 精简报告 / `detailed` 详细报告 /
  `quantum` 量子速读 / `wechat` 公众号文章 / `xiaohongshu` 小红书笔记
- 检索结果含 `doc_id`、`run_id`、`scope`、`label`、`version_label`（同一视频多版本）、
  `source_url`（原视频链接）、`score`、`snippet`；取全文时把 `doc_id` + `scope`（多版本再加
  `run_id`）传给 `library get` 即可。
- 搜索用 BM25（中文按字级、英文按词级分词），无需向量模型、离线可用。

### 12. MCP 服务（供其他 LLM 客户端调用文档库）

如果用户希望 **Claude Code / Claude Desktop / Cursor 等 MCP 客户端**直接检索本地文档库，
无需通过本 skill 脚本：项目内置 stdio MCP 服务 `mcp_server/videodevour_library_mcp.py`，
暴露 5 个工具：`search_library` / `get_article` / `list_library` / `export_article` / `export_library`。

接入配置（写入客户端的 mcpServers）：

```json
{
  "mcpServers": {
    "videodevour-library": {
      "command": "<项目目录>/.venv/bin/python",
      "args": ["<项目目录>/mcp_server/videodevour_library_mcp.py"]
    }
  }
}
```

- stdio 协议，无需端口；`command` 用项目 `.venv` 的 python，`args` 指向服务脚本绝对路径
- 端到端自测：`python mcp_server/test_mcp_client.py`（逐个调用全部工具并校验导出副作用）

### 13. 学习测试（出题 / 判题 / 评估）

依据任务报告生成测试习题（**单选题 / 多选题 / 判断题**）检验学习掌握情况：
服务端判题（答案不下发，防偷看）、逐题解析、分章掌握度、历次成绩，并可按需生成
LLM 学习建议（基于本次错题）。试卷落盘 `quiz.json` 复用，作答记录落盘 `quiz_attempts.json`。

```bash
S=<skill目录>/scripts/devour.py
# 出题（默认 10 题；--count 调整，--force 重新出题）。输出不含答案的题目列表
python3 $S quiz generate --latest --count 10
# 向用户呈现题目收集作答后判题：answers 格式 {"题目id": [选项下标...]}（多选多个下标）
python3 $S quiz grade --answers '{"q1":[0],"q2":[0,2]}' --latest
# 逐题对错/正确答案/解析 + 总分 + 分章掌握度；grade 输出含 attempt_id
# 基于本次错题生成学习建议（LLM，只生成一次并缓存）
python3 $S quiz advice --attempt-id <grade输出的attempt_id> --latest
```

- 判题规则：单选/判断全对得分；多选**全对满分、漏选得一半、错选不得分**；未答 0 分
- 用户说「考考我」「测试一下学习效果」「出几道题」时使用；**不要在用户未要求时主动生成**

## 推荐组合工作流

**默认（最快路径，适合只要报告的用户）**：

```bash
S=<skill目录>/scripts/devour.py
python3 $S process "https://www.bilibili.com/video/BV..." --level 高中   # 下载+处理，产出报告
python3 $S report --latest                                               # 精简报告全文
```

**先查库、避免重复处理（用户的问题可能已有现成笔记）**：

```bash
S=<skill目录>/scripts/devour.py
python3 $S library search "用户的关键词" --top 5   # 命中 → library get 取全文
# 没有命中 → 再走 process 处理视频
```

**要发内容时（在已有报告基础上改写，按需生成）**：

```bash
S=<skill目录>/scripts/devour.py
python3 $S styles --latest --kind quantum          # 量子速读（速览 + 朋友圈文案）
python3 $S styles --latest --kind wechat           # 公众号图文
python3 $S pdf --latest --type detailed            # 导出 PDF
```

**全套学习材料（仅当用户明确需要导图/图谱/卡片时）**：

```bash
S=<skill目录>/scripts/devour.py
python3 $S process "https://www.bilibili.com/video/BV..." --level 高中 --extras "mindmap,graph,card"
```

**检验学习效果（用户想自测时，先出题再判题）**：

```bash
S=<skill目录>/scripts/devour.py
python3 $S quiz generate --latest          # 出题 → 呈现给用户作答
python3 $S quiz grade --answers '...' --latest   # 判题 + 评估，必要时再 quiz advice
```

向用户交付时建议按「报告全文 → 思维导图 → 知识图谱」的顺序呈现：先细节后框架，便于学习理解。

## 注意事项

- 处理产物在 `<项目>/output/frames_*/` 目录，与 WebUI 历史共用（skill 直跑的任务不注册到 WebUI 任务列表）
- 项目自带 WebUI（知识库 / 视频学习页 / 衍生文体 / 导出 PDF）：`./start.sh` 后访问
  `http://localhost:8000`；默认监听 `0.0.0.0`，同一局域网的其他电脑用 `http://<本机IP>:8000` 也能打开
- 英文视频同样输出中文报告（内部已强制中文）。**详细报告对非中文原话会自动加「内容翻译」逐句译成中文，中文视频则跳过翻译**（避免多余）
- B站未登录只能取约 720p；高频调用可能触发平台风控，脚本已内置退避重试
- 下载默认即取 720p H.264，与处理档一致（不再下高清再重编码）；同视频重复处理走下载缓存，不重复下载
- 微信视频号无公开直链：优先走「元宝 Cookie 直连解析」（设置页填写后自动启用），也可配
  自建解析服务（`WECHAT_RESOLVER_URL`）；处理前可用 `wechat --check` 验证 Cookie；
  失败时引导用户用本地捕获工具（ltaoo/wx_channels_download）下载后按本地文件处理。
  视频号不支持搜索，只能粘贴分享链接
- 抖音下载与关键词搜索**都需要登录 Cookie**（设置页「抖音 cookies」/ 一键读取）；抖音搜索
  有 `a_bogus` 浏览器签名校验，触发时改用「浏览器搜索 → 复制链接 → 粘贴处理」。下载固定选
  H.264 格式（H.265 直链会 403）
- ASR **默认在线**（开箱即用、不烧本机）；本地离线 ASR 需自行安装约 2GB 模型，避免拖慢/烧热机器
- 仅处理拥有权利或已获授权的视频内容，用于个人学习

## Stop points

- 项目目录/venv 不存在且用户不愿安装 → 停止并说明依赖
- LLM/VLM key 未配置且用户不提供 → 停止（无法生成大纲与报告）
- 抖音/视频号下载所需的登录 Cookie 未配置，且用户无法提供 → 停止并说明配置方法
- 视频时长超过 60 分钟 → 先向用户确认再处理
