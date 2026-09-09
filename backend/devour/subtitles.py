# -*- coding: utf-8 -*-
"""
B站 / YouTube 字幕速记：直接读取平台已有字幕生成纯文本笔记

不下载视频、不做 ASR——B站读取 AI 字幕轨，YouTube 读取手动/自动字幕
（需要 YouTube cookies 时自动使用设置控制台中的配置），
字幕转写经 LLM 整理为纯文本学习笔记，秒级完成。
"""
import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

MAX_TRANSCRIPT_CHARS = 24000


def _mmss(seconds: float) -> str:
    m, s = int(seconds // 60), int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def _load_settings_text(key: str) -> str:
    try:
        from backend.algorithm.settings_store import load_settings
        return (load_settings().get(key) or "").strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# B站：AI 字幕轨
# ---------------------------------------------------------------------------

def fetch_bilibili_transcript(url: str) -> Dict:
    """返回 {"title", "transcript", "lang"}，字幕行带 [mm:ss] 时间前缀"""
    from backend.devour.video_downloader import _bilibili_session, _extract_video_id

    bvid = _extract_video_id(url, "bilibili")
    if not bvid:
        raise ValueError("无法从链接解析 B站 BV 号")
    session = _bilibili_session()
    # B站 AI 字幕轨仅对登录态可见：配置了 SESSDATA（设置控制台/环境变量）才拿得到
    sessdata = _load_settings_text("bilibili_sessdata") or os.getenv("BILIBILI_SESSDATA", "")
    if sessdata:
        session.cookies.set("SESSDATA", sessdata, domain=".bilibili.com")
    resp = session.get("https://api.bilibili.com/x/web-interface/view",
                       params={"bvid": bvid}, timeout=10)
    payload = resp.json()
    if payload.get("code") != 0:
        raise ValueError(f"B站视频信息获取失败: {payload.get('message')}")
    data = payload["data"]
    title = data.get("title") or bvid
    cid = data.get("cid")

    resp2 = session.get("https://api.bilibili.com/x/player/v2",
                        params={"bvid": bvid, "cid": cid}, timeout=10)
    subs = (((resp2.json().get("data") or {}).get("subtitle") or {}).get("subtitles")) or []
    if not subs:
        raise ValueError(
            "该视频在B站没有可用的字幕轨（AI 字幕未生成）。"
            "可改用完整处理流程（下载+ASR）生成图文报告。"
        )
    # 优先中文字幕轨
    subs.sort(key=lambda s: 0 if str(s.get("lan", "")).startswith("zh") else 1)
    sub_url = subs[0].get("subtitle_url") or ""
    if sub_url.startswith("//"):
        sub_url = "https:" + sub_url
    if not sub_url:
        raise ValueError("字幕轨地址为空")
    body = session.get(sub_url, timeout=15).json().get("body") or []
    lines = [f"[{_mmss(item.get('from', 0))}] {str(item.get('content', '')).strip()}"
             for item in body if item.get("content")]
    if not lines:
        raise ValueError("字幕内容为空")
    return {"title": title,
            "transcript": "\n".join(lines),
            "lang": subs[0].get("lan_doc") or subs[0].get("lan") or "未知"}


# ---------------------------------------------------------------------------
# YouTube：手动/自动字幕（yt-dlp，需 cookies 时自动使用控制台配置）
# ---------------------------------------------------------------------------

def _parse_vtt_or_srt(raw: str) -> str:
    """把 vtt/srt 字幕解析为纯文本（去时间轴/标签/滚动重复行）"""
    out, seen = [], set()
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        if re.match(r"^\d+$", line) or "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line)          # <c>、<00:00:00.000> 等标签
        line = line.replace("&nbsp;", " ").strip()
        if not line or line in seen:                  # 自动字幕的滚动重复行
            continue
        seen.add(line)
        out.append(line)
    return "\n".join(out)


def get_youtube_cookiefile() -> Optional[str]:
    """YouTube cookies：环境变量文件优先，其次设置控制台粘贴的 cookies.txt"""
    env_cookies = os.getenv("YTDLP_COOKIES_FILE")
    if env_cookies and os.path.exists(env_cookies):
        return env_cookies
    text = _load_settings_text("youtube_cookies")
    if text and "youtube.com" in text.lower():
        fd, path = tempfile.mkstemp(prefix="yt_notes_cookies_", suffix=".txt")
        with os.fdopen(fd, "w") as f:
            f.write(text if text.endswith("\n") else text + "\n")
        return path
    return None


def fetch_youtube_transcript(url: str) -> Dict:
    import shutil
    from backend.devour.video_downloader import _get_ydl

    tmp = tempfile.mkdtemp(prefix="yt_subs_")
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["zh-Hans", "zh-CN", "zh", "en", "ja"],
        "subtitlesformat": "vtt/srt/best",
        "outtmpl": os.path.join(tmp, "subs"),
    }
    cookiefile = get_youtube_cookiefile()
    if cookiefile:
        opts["cookiefile"] = cookiefile
        logging.info("使用 YouTube cookies 获取字幕")
    # 与下载链路保持一致：PO Token 脚本 + JS 运行时（否则 bot 检查/n challenge 会拦）
    from backend.devour.video_downloader import _bgutil_script_path, _youtube_js_runtime
    pot_script = _bgutil_script_path()
    if pot_script:
        opts["extractor_args"] = {"youtubepot-bgutilscript": {"script_path": [pot_script]}}
    js_runtime = _youtube_js_runtime()
    if js_runtime:
        opts["js_runtimes"] = {js_runtime: {}}
    try:
        with _get_ydl(referer="https://www.youtube.com/", **opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        msg = str(e)
        if "Sign in" in msg or "not a bot" in msg:
            raise ValueError(
                "YouTube 要求登录验证（bot 检查）。请在设置控制台「YouTube cookies」"
                "配置 cookies（可用「一键读取浏览器 Cookie」自动获取）后重试。"
            )
        if "Requested format is not available" in msg or "needs to be reloaded" in msg:
            raise ValueError(
                "YouTube 拒绝了当前网络请求（可能缺少 JS 运行时/PO Token 或网络受限）。"
                "请在设置页点「下载环境自检」按提示补齐依赖。"
            )
        raise
    finally:
        if cookiefile and "yt_notes_cookies_" in str(cookiefile):
            try:
                os.remove(cookiefile)
            except Exception:
                pass
    title = (info or {}).get("title") or "YouTube 视频"
    files = sorted(Path(tmp).glob("*.vtt")) + sorted(Path(tmp).glob("*.srt"))
    if not files:
        message = "该视频没有可用字幕（含自动字幕）"
        if not cookiefile:
            message += "；当前 IP 受 YouTube bot 检查限制，请在设置控制台配置「YouTube cookies」后重试"
        raise ValueError(message + "。也可改用完整处理流程（下载+ASR）。")
    text = _parse_vtt_or_srt(files[0].read_text(encoding="utf-8", errors="ignore"))
    lang = files[0].stem.split(".")[-1] if "." in files[0].stem else "未知"
    shutil.rmtree(tmp, ignore_errors=True)
    if not text:
        raise ValueError("字幕内容为空")
    return {"title": title, "transcript": text, "lang": lang}


# ---------------------------------------------------------------------------
# LLM 笔记生成
# ---------------------------------------------------------------------------

_NOTES_SYSTEM_PROMPT = (
    "你是一位专业的学习笔记整理专家，擅长把口语化的视频字幕转写整理为"
    "条理清晰、要点突出的纯文本学习笔记。必须全程使用简体中文输出"
    "（专有名词保留原文）。只输出笔记正文，不要任何解释。"
)

_NOTES_PROMPT_TEMPLATE = """请根据以下视频字幕转写内容，整理成一份 Markdown 学习笔记。

输出结构（严格遵循）：
1. 开头用 `# {title}` 作为一级标题
2. 用 `## 内容概览` 写 2-4 句整体概括
3. 用 `## 核心要点` 分节：每个主题一个 `### 小标题`，正文用「-」要点式罗列
4. 用 `## 概念关系图` 输出一个 Mermaid 图，展示概念之间的关系：

```mermaid
graph TD
    A[核心概念A] --> B[相关概念B]
    A --> C[应用场景C]
    B --> D[具体方法D]
```

Mermaid 要求：
- 用 `graph TD`（自上而下）；节点标签用中文，方括号 `[名称]`；关系箭头 `-->` 可加说明 `-->|包含|`
- 节点 6-14 个，覆盖笔记主要概念；只画字幕中真实出现的关系，不要编造
- 禁止使用圆括号、方括号、引号等会破坏 Mermaid 语法的字符出现在节点标签内

其他要求：
1. 全程简体中文（专有名词、技术术语保留原文）
2. 保留关键概念、论据、结论与重要数字细节；不要添加字幕中没有的内容
3. 当前学习阶段为：{level}，请据此调整内容深度
4. 只输出 Markdown 正文，不要额外解释

视频标题：{title}

字幕转写：
---
{transcript}
---
"""


def generate_subtitle_notes(url: str, platform: str, education_level: str = "自由学习") -> Dict:
    """
    统一入口：抓取字幕 → LLM 整理纯文本笔记 → 落盘。

    Returns:
        {"title", "platform", "lang", "notes", "file", "file_url"}
    """
    if platform == "bilibili":
        meta = fetch_bilibili_transcript(url)
    elif platform == "youtube":
        meta = fetch_youtube_transcript(url)
    else:
        raise ValueError("字幕笔记仅支持 B站 / YouTube 链接")

    transcript = meta["transcript"]
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n... (内容过长，已截取)"

    from backend.algorithm.llm_handler import LLMHandler
    llm = LLMHandler(education_level=education_level)
    prompt = _NOTES_PROMPT_TEMPLATE.format(
        level=education_level, title=meta["title"], transcript=transcript)
    notes = llm.get_response(prompt, system_message=_NOTES_SYSTEM_PROMPT).strip()
    if not notes:
        raise ValueError("笔记生成结果为空，请重试")

    # 落盘到 output/subtitle_notes/，可通过 /static/subtitle_notes/ 访问
    from backend.algorithm import settings_store
    from backend.runtime import paths as _rt_paths
    output_root = _rt_paths.data_root() / "output" / "subtitle_notes"
    output_root.mkdir(parents=True, exist_ok=True)
    # URL 安全文件名：仅保留中文/字母/数字/-/_，其余（含全角标点、#、空格）一律转下划线，
    # 否则中文标点会让静态路径需要编码、前端下载/新窗口打开都会失败
    safe_title = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9_-]+", "_", meta["title"]).strip("_")[:50] or "notes"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{platform}_{safe_title}_{ts}"
    file_path = output_root / f"{stem}.txt"
    md_path = output_root / f"{stem}.md"

    # 提示词已要求 LLM 输出以 `# 标题` 开头，这里只补一行来源元信息，避免标题重复
    meta_line = (f"> 来源：{platform} 字幕（{meta['lang']}） · 学习阶段：{education_level}\n\n")
    # 纯文本版：去掉 Markdown 标记（供纯文本场景）
    txt_body = re.sub(r"^#{1,6}\s*", "", notes, flags=re.MULTILINE)
    txt_body = re.sub(r"```mermaid[\s\S]*?```", "", txt_body)   # 纯文本版去掉 mermaid 代码块
    file_path.write_text(meta_line.replace("> ", "") + txt_body, encoding="utf-8")
    # Markdown 版（标题 + 来源 + 正文 + Mermaid 图，笔记工具可直接用）
    md_path.write_text(meta_line + notes, encoding="utf-8")
    logging.info(f"字幕笔记已生成: {md_path}")

    return {"title": meta["title"], "platform": platform, "lang": meta["lang"],
            "notes": notes,
            "file": str(file_path),
            "file_url": f"/static/subtitle_notes/{file_path.name}",
            "md_file": str(md_path),
            "md_url": f"/api/subtitle-notes/download?name={file_path.stem}&fmt=md",
            "txt_url": f"/api/subtitle-notes/download?name={file_path.stem}&fmt=txt",
            "stem": file_path.stem}
