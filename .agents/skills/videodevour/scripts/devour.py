#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VideoDevour skill 入口脚本（跨 agent 通用，遵循 .agents/skills 约定）

把视频（B站/YouTube/抖音 链接、微信视频号分享链接或本地文件）端到端处理为中文图文报告。
自动切换到 VideoDevour 项目的 .venv 运行，无需手动激活环境。
另可检索项目本地积累的「文档库」（历史任务的全部报告/笔记），供 agent 复用已有成果。

项目根目录解析顺序:
  1. --home 参数 / VIDEO_DEVOUR_HOME 环境变量
  2. 脚本所在仓库（本文件位于 <repo>/.agents/skills/videodevour/scripts/ 时自动识别）
  3. 默认安装路径

用法:
  devour.py search "关键词" [--platform bilibili|youtube|douyin] [--max N]
  devour.py info <url>
  devour.py notes <url> [--level 学习阶段]
  devour.py wechat <视频号分享链接> [--check]
  devour.py douyin <抖音链接> [--check]
  devour.py process <url|本地视频路径> [--level 高中|初中|小学] [--home 项目目录]
  devour.py mindmap [--latest | --dir 输出目录] [--open] [--level 学习阶段]
  devour.py graph   [--latest | --dir 输出目录] [--open] [--level 学习阶段]
  devour.py styles  [--latest | --dir 输出目录] [--kind quantum,wechat,xiaohongshu]
  devour.py pdf     [--latest | --dir 输出目录] [--type report|detailed|outline|all] [--out 文件]
  devour.py report  [--latest | --dir 输出目录] [--type report|detailed|outline]
  devour.py library search "关键词" [--scope all|outline|report|detailed] [--top 5]
  devour.py library list [--scope ...]
  devour.py library get <doc_id> --scope report [--run-id RUN]
  devour.py library export <doc_id> --scope report [--out 目录]
  devour.py library export-all [--out 目录]
  devour.py quiz generate [--latest | --dir 输出目录] [--count 10] [--force]
  devour.py quiz grade --answers '{"q1":[0],"q2":[0,2]}' [--latest | --dir 输出目录]
  devour.py quiz advice --attempt-id ID [--latest | --dir 输出目录]
"""
import argparse
import json
import os
import sys
from pathlib import Path

FALLBACK_HOME = os.environ.get(
    "VIDEO_DEVOUR_HOME", "/Volumes/拓展/workspace/videodevour/video-devour"
)


def project_home(override=None) -> Path:
    candidates = []
    if override:
        candidates.append(Path(override))
    if os.environ.get("VIDEO_DEVOUR_HOME"):
        candidates.append(Path(os.environ["VIDEO_DEVOUR_HOME"]))
    # 脚本位于 <repo>/.agents/skills/videodevour/scripts/ 时，向上回溯定位仓库
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir, *script_dir.parents]:
        if (parent / "backend" / "algorithm").exists():
            candidates.append(parent)
            break
    candidates.append(Path(FALLBACK_HOME).expanduser())

    for home in candidates:
        home = home.expanduser().resolve()
        if (home / "backend").exists():
            return home
    print("错误: 未找到 VideoDevour 项目目录，请用 --home 或 VIDEO_DEVOUR_HOME 指定",
          file=sys.stderr)
    sys.exit(1)


def reexec_with_venv(home: Path):
    """若项目自带 .venv 且当前不是它，切换后重新执行自身"""
    if os.environ.get("VD_IN_VENV") == "1":
        return
    venv_python = home / ".venv" / "bin" / "python"
    if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
        env = dict(os.environ, VD_IN_VENV="1")
        os.execve(str(venv_python), [str(venv_python), __file__] + sys.argv[1:], env)


def setup_project(home: Path):
    sys.path.insert(0, str(home))
    os.chdir(home)
    # 引导 config 模块与 sys.path（与后端启动逻辑一致）
    from backend.algorithm import settings_store  # noqa

    settings_store.apply_to_config()


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------

def cmd_search(args):
    setup_project(project_home(args.home))
    from backend.devour.video_downloader import search_videos

    results = search_videos(args.query, platform=args.platform, max_results=args.max)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_info(args):
    setup_project(project_home(args.home))
    from backend.devour.video_downloader import probe_video_info

    info = probe_video_info(args.url)
    duration = info.get("duration")
    if duration and duration > 1800:
        print(f"提示: 时长约 {duration // 60} 分钟（多P合集为总时长，process 只处理当前分P）。\n",
              file=sys.stderr)
    print(json.dumps(info, ensure_ascii=False, indent=2))


def _collect_artifacts(out_dir: Path) -> dict:
    """汇总一个任务目录里的产物：报告 / 详细报告 / 大纲 / 关键帧 / 压缩信息 / 文体。

    与 WebUI 的产物保持一致，便于 agent 直接取用，不必自己猜文件名。
    """
    def _p(name):
        f = out_dir / name
        return str(f) if f.exists() and f.stat().st_size > 0 else None

    arts = {
        "report": _p("final_report.md"),            # 精简报告
        "detailed_report": _p("detailed_report.md"),  # 详细报告（原文+笔记）
        "outline": _p("detailed_outline.md"),       # 图文大纲
    }
    kf = out_dir / "keyframes"
    arts["keyframes"] = [str(p) for p in sorted(kf.glob("*.jpg"))] if kf.exists() else []

    # 处理时压缩到 720p/10fps 的实际结果（原体积 vs 压缩后）
    mp = out_dir / "media_profile.json"
    if mp.exists():
        try:
            d = json.loads(mp.read_text(encoding="utf-8"))
            arts["media_profile"] = {
                "profile": d.get("profile"),
                "original_bytes": d.get("original_bytes"),
                "size": d.get("size"),
                "width": d.get("width"),
                "height": d.get("height"),
                "fps": d.get("fps"),
            }
        except Exception:
            pass

    # 已生成的衍生文体（按需生成，未生成则不列出）。
    # 用 document_library 的静态映射取文件名，避免为读名字而导入依赖 config 的模块。
    try:
        from backend.algorithm.document_library import ARTICLE_TYPES, GENERATABLE_SCOPES
        styles = {}
        for scope in GENERATABLE_SCOPES:
            fname, label = ARTICLE_TYPES[scope][0], ARTICLE_TYPES[scope][1]
            f = out_dir / fname
            if f.exists() and f.stat().st_size > 0:
                styles[scope] = {"label": label, "file": str(f)}
        if styles:
            arts["styles"] = styles
    except Exception:
        pass
    return arts


def cmd_process(args):
    home = project_home(args.home)
    setup_project(home)

    from backend.algorithm.pipeline import run_full_pipeline

    source = args.source
    # 支持直接粘贴含链接的分享文案（微信/B站 App 分享格式）
    from backend.devour.video_downloader import extract_share_url
    url = extract_share_url(source)
    if url.startswith(("http://", "https://")):
        print(f"[1/2] 下载视频: {url}")
        from backend.devour.video_downloader import download_video

        # 默认取 720p H.264：与处理阶段的轻量档一致，避免下高清再重编码（更省流量与时间）
        result = download_video(url, str(home / "uploads"), max_height=720)
        video_path = result["file_path"]
        print(f"下载完成: {video_path}")
    else:
        video_path = str(Path(source).expanduser().resolve())
        if not Path(video_path).exists():
            print(f"错误: 文件不存在 {video_path}", file=sys.stderr)
            sys.exit(1)
        print(f"[1/2] 使用本地视频: {video_path}")

    print(f"[2/2] 启动处理流水线 (学习阶段: {args.level}) ...")
    run_full_pipeline(video_path, education_level=args.level)

    # 定位本次输出目录（pipeline 以视频名命名，取最新一个）
    video_name = Path(video_path).stem
    candidates = sorted(
        (home / "output").glob(f"frames_{video_name}_*"), key=lambda p: p.stat().st_mtime
    )
    if not candidates:
        print(json.dumps({"error": "流水线未产生输出目录，请检查日志"}, ensure_ascii=False))
        sys.exit(2)
    out_dir = candidates[-1]

    # 可选附加产物：--extras mindmap,graph,card（默认不生成，节省时间）
    extras_result = {}
    extras = [x.strip() for x in (getattr(args, "extras", "") or "").split(",") if x.strip()]
    labels = {"mindmap": "思维导图", "graph": "知识图谱", "card": "学习卡片"}
    for kind in extras:
        if kind not in labels:
            continue
        print(f"生成{labels[kind]}（LLM 生成约 10-30 秒）...")
        try:
            from backend.algorithm import report_viz
            if kind == "card":
                path = report_viz.generate_learning_card(out_dir, args.level)
            else:
                fn = report_viz.generate_mindmap if kind == "mindmap" else report_viz.generate_knowledge_graph
                path = fn(out_dir, args.level)
            extras_result[kind] = str(path)
        except Exception as e:
            extras_result[kind] = f"生成失败: {e}"

    outcome = {"output_dir": str(out_dir), **_collect_artifacts(out_dir)}
    if extras_result:
        outcome["extras"] = extras_result
    if not outcome.get("report"):
        outcome["error"] = "处理未完成：final_report.md 未生成，请检查 processing.log"
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        sys.exit(2)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))


def cmd_wechat(args):
    """视频号：检查元宝 Cookie 状态（--check），或下载分享链接视频（仅下载不处理）"""
    home = project_home(args.home)
    setup_project(home)

    from backend.devour.video_downloader import (
        _wechat_setting, _wechat_parse_share, extract_share_url, detect_platform,
        download_video,
    )

    if args.check:
        cookie = _wechat_setting("wechat_yuanbao_cookie", "YUANBAO_COOKIE")
        if not cookie:
            print(json.dumps({
                "configured": False, "valid": None,
                "message": "未配置元宝 Cookie。登录 yuanbao.tencent.com → F12 → Network → "
                           "复制任意请求的 Cookie，填入 WebUI 设置页「微信视频号」，或写入 "
                           "settings.json 的 wechat_yuanbao_cookie / 环境变量 YUANBAO_COOKIE",
            }, ensure_ascii=False, indent=2))
            sys.exit(1)
        # 探测原理：格式合法但无效的分享 id —— Cookie 失效时元宝返回 401/403，
        # Cookie 有效时能进入解析（返回"未找到 export id"类业务错误）
        try:
            _wechat_parse_share("https://weixin.qq.com/sph/CookieCheckProbe00", cookie)
            print(json.dumps({"configured": True, "valid": True,
                              "message": "元宝 Cookie 已配置且有效"}, ensure_ascii=False, indent=2))
        except Exception as e:
            msg = str(e)
            if "401" in msg or "403" in msg:
                print(json.dumps({"configured": True, "valid": False,
                                  "message": "元宝 Cookie 已失效，请重新复制并更新设置"},
                                 ensure_ascii=False, indent=2))
                sys.exit(1)
            print(json.dumps({"configured": True, "valid": True,
                              "message": "元宝 Cookie 已配置且有效"}, ensure_ascii=False, indent=2))
        return

    url = extract_share_url(args.url or "")
    if detect_platform(url) != "wechat":
        print("错误: 请提供微信视频号分享链接（weixin.qq.com/sph/...，可直接粘贴分享文案）",
              file=sys.stderr)
        sys.exit(1)
    print(f"[1/1] 解析并下载视频号视频: {url}")
    result = download_video(url, str(home / "uploads"))
    info = result.get("info", {})
    print(json.dumps({
        "file_path": result["file_path"],
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "hint": "可继续用 process 命令处理该本地文件生成图文报告",
    }, ensure_ascii=False, indent=2))


def cmd_douyin(args):
    """抖音：检查登录 Cookie 状态（--check），或下载分享链接视频（仅下载不处理）。

    抖音下载需要登录态 Cookie（设置页「抖音 cookies」或一键读取浏览器 Cookie）。
    下载走 App 接口直连（aweme.snssdk.com）：web 接口自 2026 起受 Argus 浏览器
    签名校验拦截，仅带 Cookie 也会返回 403；yt-dlp 会把它误报成
    「Fresh cookies are needed」，看到该提示时不必反复重配 Cookie。
    """
    home = project_home(args.home)
    setup_project(home)

    from backend.devour.video_downloader import (
        _load_douyin_cookies_header, extract_share_url, detect_platform, download_video,
    )

    if args.check:
        cookie = _load_douyin_cookies_header()
        if cookie:
            print(json.dumps({
                "configured": True,
                "message": "抖音 Cookie 已配置（下载与关键词搜索需要登录态）",
            }, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({
                "configured": False,
                "message": "未配置抖音 Cookie。请在 WebUI 设置页「抖音 cookies」填写，"
                           "或点「一键读取浏览器 Cookie」自动获取（需浏览器已登录抖音）；"
                           "也可写入 settings.json 的 douyin_cookies",
            }, ensure_ascii=False, indent=2))
            sys.exit(1)
        return

    url = extract_share_url(args.url or "")
    if detect_platform(url) != "douyin":
        print("错误: 请提供抖音链接（douyin.com/video/{id} 或 v.douyin.com 短链，"
              "可直接粘贴含链接的分享文案）", file=sys.stderr)
        sys.exit(1)
    print(f"[1/1] 解析并下载抖音视频: {url}")
    result = download_video(url, str(home / "uploads"), max_height=720)
    info = result.get("info", {})
    print(json.dumps({
        "file_path": result["file_path"],
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "hint": "可继续用 process 命令处理该本地文件生成图文报告",
    }, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 文档库（历史任务成果复用 / 检索）
# ---------------------------------------------------------------------------

def cmd_library(args):
    """检索项目本地「文档库」：全部历史任务产出的报告/笔记/衍生文体。

    子命令：
      search       BM25 相关度检索（返回 doc_id/scope/摘要）
      list         无关键词浏览全部文档索引
      get          按 doc_id + scope 取全文 Markdown
      export       导出单篇为 ZIP（md + 引用图片）
      export-all   导出整库为 ZIP
    """
    home = project_home(args.home)
    setup_project(home)

    from backend.algorithm import document_library as dl

    action = args.action
    if action == "search":
        result = dl.search_library(args.query, scope=args.scope, top_k=args.top)
    elif action == "list":
        result = dl.list_library(scope=args.scope)
    elif action == "get":
        result = dl.get_article(args.doc_id, args.scope, run_id=args.run_id or "")
        if not result:
            print(f"文章不存在: doc_id={args.doc_id} scope={args.scope}",
                  file=sys.stderr)
            sys.exit(1)
    elif action == "export":
        result = dl.export_article_zip(args.doc_id, args.scope, run_id=args.run_id or "")
        if not result:
            print(f"文章不存在: doc_id={args.doc_id} scope={args.scope}",
                  file=sys.stderr)
            sys.exit(1)
        content, name = result
        out_dir = Path(args.out).expanduser() if args.out else Path.home() / "Downloads"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / name
        out_path.write_bytes(content)
        result = {"zip": str(out_path), "bytes": len(content)}
    else:  # export-all
        content, name = dl.export_library_zip()
        out_dir = Path(args.out).expanduser() if args.out else Path.home() / "Downloads"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / name
        out_path.write_bytes(content)
        result = {"zip": str(out_path), "bytes": len(content)}

    # 「取全文」直接打印 Markdown；其余输出 JSON
    if action == "get":
        print(result["content"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def cmd_notes(args):
    """字幕速记：直接用 B站/YouTube 已有字幕生成纯文本笔记（秒级，不下载视频）"""
    home = project_home(args.home)
    setup_project(home)

    from backend.devour.video_downloader import detect_platform, extract_share_url
    from backend.devour.subtitles import generate_subtitle_notes

    url = extract_share_url(args.url or "")
    platform = detect_platform(url)
    if platform not in ("bilibili", "youtube"):
        print("错误: 字幕笔记仅支持 B站 / YouTube 链接（可直接粘贴分享文案）", file=sys.stderr)
        sys.exit(1)

    result = generate_subtitle_notes(url, platform, args.level)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _resolve_task_dir(home: Path, args) -> Path:
    """定位任务输出目录：--dir 优先，否则取最新 frames_* 目录"""
    if getattr(args, "dir", None):
        out = Path(args.dir).expanduser().resolve()
    else:
        candidates = sorted((home / "output").glob("frames_*"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            print("暂无任何处理产物", file=sys.stderr)
            sys.exit(1)
        out = candidates[-1]
    if not out.exists():
        print(f"输出目录不存在: {out}", file=sys.stderr)
        sys.exit(1)
    return out


def cmd_viz(args, kind: str):
    """生成思维导图 / 知识图谱（复用 API 同款逻辑，结果缓存到任务目录）"""
    home = project_home(args.home)
    setup_project(home)
    out_dir = _resolve_task_dir(home, args)
    label = "思维导图" if kind == "mindmap" else "知识图谱"
    print(f"正在为 {out_dir.name} 生成{label}（LLM 生成约 10-30 秒）...")

    from backend.algorithm import report_viz
    if kind == "mindmap":
        path = report_viz.generate_mindmap(out_dir, education_level=args.level or None)
    else:
        path = report_viz.generate_knowledge_graph(out_dir, education_level=args.level or None)

    result = {"html": str(path), "output_dir": str(out_dir)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.open:
        import webbrowser
        webbrowser.open(path.as_uri())
        print("已在浏览器打开")


def cmd_list(args):
    """列出视频存储目录里待处理的本地视频（作为信息源，供选一个用 process 处理）。"""
    home = project_home(args.home)
    setup_project(home)
    from backend.runtime import paths as _rt
    exts = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v")
    items = []
    for src in ("downloads", "uploads"):
        d = _rt.media_subdir(src)
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in exts:
                st = f.stat()
                items.append({"file": str(f), "source": src,
                              "size_mb": round(st.st_size / 1024 / 1024, 1),
                              "mtime": st.st_mtime})
    print(json.dumps({"count": len(items), "videos": items}, ensure_ascii=False, indent=2))


def cmd_report(args):
    home = project_home(args.home)
    if args.dir:
        out_dir = Path(args.dir)
    else:
        candidates = sorted(
            (home / "output").glob("frames_*"), key=lambda p: p.stat().st_mtime
        )
        if not candidates:
            print("暂无任何处理产物", file=sys.stderr)
            sys.exit(1)
        out_dir = candidates[-1]
    # 默认看精简报告；--type detailed 看详细报告（原文+笔记对照）
    name = {"report": "final_report.md", "detailed": "detailed_report.md",
            "outline": "detailed_outline.md"}[args.type]
    report = out_dir / name
    if not report.exists():
        print(f"该任务尚未生成 {name}: {out_dir}", file=sys.stderr)
        sys.exit(1)
    print(f"# 输出目录: {out_dir}\n")
    print(report.read_text(encoding="utf-8"))


def cmd_styles(args):
    """生成衍生文体：量子速读 / 公众号文章 / 小红书笔记（基于已有报告改写）。

    默认三种都生成；已生成的会直接复用（落盘缓存）。
    """
    home = project_home(args.home)
    setup_project(home)
    out_dir = _resolve_task_dir(home, args)

    from backend.algorithm.style_articles import generate_style, STYLE_TYPES
    kinds = [k.strip() for k in (args.kind or "").split(",") if k.strip()] or list(STYLE_TYPES)
    result = {"output_dir": str(out_dir), "styles": {}}
    for scope in kinds:
        if scope not in STYLE_TYPES:
            result["styles"][scope] = "不支持的文体（可选 quantum/wechat/xiaohongshu）"
            continue
        label = STYLE_TYPES[scope][1]
        try:
            path = generate_style(out_dir, scope, args.level or None, force=getattr(args, "force", False))
            result["styles"][scope] = {"label": label, "file": str(path)}
            print(f"已生成{label}: {path}")
        except Exception as e:
            result["styles"][scope] = f"生成失败: {e}"
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_pdf(args):
    """把报告导出为 PDF（内置中文字体，无需外部依赖）。

    --type：report 精简报告(默认) / detailed 详细报告 / outline 图文大纲 / all 合并
    """
    home = project_home(args.home)
    setup_project(home)
    out_dir = _resolve_task_dir(home, args)

    from backend.algorithm.pdf_export import markdown_to_pdf, safe_pdf_name
    sources = {"report": ("final_report.md", "精简报告"),
               "detailed": ("detailed_report.md", "详细报告"),
               "outline": ("detailed_outline.md", "图文大纲")}
    if args.type == "all":
        parts = []
        for key in ("outline", "report", "detailed"):
            f = out_dir / sources[key][0]
            if f.exists() and f.stat().st_size > 0:
                parts.append(f.read_text(encoding="utf-8"))
        if not parts:
            print("该任务暂无可导出的报告", file=sys.stderr)
            sys.exit(1)
        md, label = "\n\n".join(parts), "合并报告"
    else:
        fname, label = sources[args.type]
        f = out_dir / fname
        if not f.exists() or f.stat().st_size == 0:
            print(f"该任务没有{label}（{fname}）", file=sys.stderr)
            sys.exit(1)
        md = f.read_text(encoding="utf-8")

    title = out_dir.name
    pdf_bytes = markdown_to_pdf(md, title=title, base_dir=out_dir, extra_roots=(home,))
    out_path = Path(args.out).expanduser() if args.out else out_dir / safe_pdf_name(title, label)
    out_path.write_bytes(pdf_bytes)
    print(json.dumps({"pdf": str(out_path), "type": args.type, "label": label,
                      "bytes": len(pdf_bytes), "output_dir": str(out_dir)},
                     ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 学习测试（生成 / 判题 / 评估；逻辑在 backend/algorithm/quiz.py）
# ---------------------------------------------------------------------------

def cmd_quiz(args):
    """学习测试：generate 出题（单选/多选/判断）、grade 判题、advice 学习建议。

    出题基于任务报告（LLM），落盘 quiz.json 复用；判题纯本地（秒级）。
    answers 支持 JSON 字符串或指向 .json 文件的路径，格式 {"题目id": [选项下标...]}。
    """
    home = project_home(args.home)
    setup_project(home)
    out_dir = _resolve_task_dir(home, args)

    from backend.algorithm import quiz as quiz_module

    action = args.action
    if action == "generate":
        quiz = quiz_module.generate_quiz(
            out_dir, education_level=args.level or None,
            count=args.count, force=args.force,
        )
        result = {**quiz_module.quiz_public(quiz),
                  "file": str(out_dir / quiz_module.QUIZ_FILE),
                  "attempts": quiz_module.attempts_summary(out_dir),
                  "hint": "作答格式 {'题目id': [选项下标...]}，用 quiz grade 提交判题",
                  }
    elif action == "grade":
        raw = (args.answers or "").strip()
        if raw.endswith(".json") or raw.startswith(("/", "~")):
            raw = Path(raw).expanduser().read_text(encoding="utf-8")
        try:
            answers = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"错误: answers 不是合法 JSON（{e}）", file=sys.stderr)
            sys.exit(1)
        result = quiz_module.grade_quiz(out_dir, answers)
    else:  # advice
        result = quiz_module.quiz_advice(out_dir, args.attempt_id)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="VideoDevour 视频转图文报告")
    parser.add_argument("--home", default=None, help="VideoDevour 项目根目录")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="搜索B站/YouTube/抖音视频")
    p_search.add_argument("query")
    p_search.add_argument("--platform", default="bilibili",
                          choices=["bilibili", "youtube", "douyin"])
    p_search.add_argument("--max", type=int, default=5)
    p_search.set_defaults(func=cmd_search)

    p_info = sub.add_parser("info", help="查看链接视频元数据")
    p_info.add_argument("url")
    p_info.set_defaults(func=cmd_info)

    p_proc = sub.add_parser("process", help="一键下载并处理视频")
    p_proc.add_argument("source", help="视频链接或本地文件路径")
    p_proc.add_argument("--level", default="自由学习",
                        choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_proc.add_argument("--extras", default="",
                        help="报告完成后附加生成（可选，默认不生成），逗号分隔：mindmap,graph,card")
    p_proc.set_defaults(func=cmd_process)

    p_wx = sub.add_parser("wechat", help="微信视频号：下载分享链接视频 / 检查元宝 Cookie")
    p_wx.add_argument("url", nargs="?", default=None,
                      help="视频号分享链接（weixin.qq.com/sph/...）或含链接的分享文案")
    p_wx.add_argument("--check", action="store_true", help="检查元宝 Cookie 是否已配置且有效")
    p_wx.set_defaults(func=cmd_wechat)

    p_dy = sub.add_parser("douyin", help="抖音：下载分享链接视频 / 检查登录 Cookie")
    p_dy.add_argument("url", nargs="?", default=None,
                      help="抖音链接（douyin.com/video/{id}、v.douyin.com 短链）或含链接的分享文案")
    p_dy.add_argument("--check", action="store_true", help="检查抖音 Cookie 是否已配置")
    p_dy.set_defaults(func=cmd_douyin)

    p_list = sub.add_parser("list", help="列出视频存储目录里待处理的本地视频（信息源）")
    p_list.set_defaults(func=cmd_list)

    p_lib = sub.add_parser("library", help="检索项目本地文档库（历史任务报告/笔记复用）")
    lib_sub = p_lib.add_subparsers(dest="action", required=True)
    _scope_choices = ["all", "outline", "report", "detailed", "quantum", "wechat", "xiaohongshu"]

    lib_s = lib_sub.add_parser("search", help="BM25 相关度检索（返回 doc_id/scope/摘要）")
    lib_s.add_argument("query")
    lib_s.add_argument("--scope", default="all", choices=_scope_choices)
    lib_s.add_argument("--top", type=int, default=5)
    lib_s.set_defaults(func=cmd_library)

    lib_l = lib_sub.add_parser("list", help="无关键词浏览全部文档索引")
    lib_l.add_argument("--scope", default="all", choices=_scope_choices)
    lib_l.set_defaults(func=cmd_library)

    lib_g = lib_sub.add_parser("get", help="按 doc_id + scope 取全文 Markdown")
    lib_g.add_argument("doc_id")
    lib_g.add_argument("--scope", required=True, choices=_scope_choices)
    lib_g.add_argument("--run-id", default=None, help="同一任务多次处理时指定版本")
    lib_g.set_defaults(func=cmd_library)

    lib_e = lib_sub.add_parser("export", help="导出单篇为 ZIP（md + 引用图片）")
    lib_e.add_argument("doc_id")
    lib_e.add_argument("--scope", required=True, choices=_scope_choices)
    lib_e.add_argument("--run-id", default=None)
    lib_e.add_argument("--out", default=None, help="导出目录（默认 ~/Downloads）")
    lib_e.set_defaults(func=cmd_library)

    lib_ea = lib_sub.add_parser("export-all", help="导出整库为 ZIP")
    lib_ea.add_argument("--out", default=None, help="导出目录（默认 ~/Downloads）")
    lib_ea.set_defaults(func=cmd_library)

    p_quiz = sub.add_parser("quiz", help="学习测试：出题（单选/多选/判断）/ 判题 / 学习建议")
    quiz_sub = p_quiz.add_subparsers(dest="action", required=True)

    quiz_g = quiz_sub.add_parser("generate", help="依据任务报告出题（落盘 quiz.json，复用缓存）")
    quiz_g.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    quiz_g.add_argument("--dir", default=None, help="指定任务输出目录")
    quiz_g.add_argument("--count", type=int, default=10, help="题目数量（3-30，默认 10）")
    quiz_g.add_argument("--force", action="store_true", help="重新出题（覆盖已有试卷）")
    quiz_g.add_argument("--level", default=None,
                        choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    quiz_g.set_defaults(func=cmd_quiz)

    quiz_gr = quiz_sub.add_parser("grade", help="提交作答并判题（本地判题，秒级）")
    quiz_gr.add_argument("--answers", required=True,
                         help="JSON 字符串或 .json 文件路径，格式 {\"q1\": [0], \"q2\": [0,2]}")
    quiz_gr.add_argument("--latest", action="store_true")
    quiz_gr.add_argument("--dir", default=None)
    quiz_gr.set_defaults(func=cmd_quiz)

    quiz_a = quiz_sub.add_parser("advice", help="基于某次作答生成 LLM 学习建议")
    quiz_a.add_argument("--attempt-id", required=True, help="作答记录 ID（grade 输出里的 attempt_id）")
    quiz_a.add_argument("--latest", action="store_true")
    quiz_a.add_argument("--dir", default=None)
    quiz_a.set_defaults(func=cmd_quiz)

    p_notes = sub.add_parser("notes", help="字幕速记：用平台字幕生成纯文本笔记（B站/YouTube，秒级）")
    p_notes.add_argument("url", help="B站/YouTube 视频链接或分享文案")
    p_notes.add_argument("--level", default="自由学习",
                         choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_notes.set_defaults(func=cmd_notes)

    p_mm = sub.add_parser("mindmap", help="为任务报告生成思维导图（markmap HTML）")
    p_mm.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_mm.add_argument("--dir", default=None, help="指定任务输出目录")
    p_mm.add_argument("--level", default=None,
                      choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_mm.add_argument("--open", action="store_true", help="生成后在浏览器打开")
    p_mm.set_defaults(func=lambda a: cmd_viz(a, "mindmap"))

    p_kg = sub.add_parser("graph", help="为任务报告生成知识图谱（ECharts 力导向图 HTML）")
    p_kg.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_kg.add_argument("--dir", default=None, help="指定任务输出目录")
    p_kg.add_argument("--level", default=None,
                      choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_kg.add_argument("--open", action="store_true", help="生成后在浏览器打开")
    p_kg.set_defaults(func=lambda a: cmd_viz(a, "graph"))

    p_report = sub.add_parser("report", help="查看任务报告（默认精简报告，--type 可选详细报告/大纲）")
    p_report.add_argument("--latest", action="store_true")
    p_report.add_argument("--dir", default=None)
    p_report.add_argument("--type", default="report",
                          choices=["report", "detailed", "outline"],
                          help="report=精简报告(默认) / detailed=详细报告 / outline=图文大纲")
    p_report.set_defaults(func=cmd_report)

    p_styles = sub.add_parser(
        "styles", help="生成衍生文体：量子速读 / 公众号文章 / 小红书笔记")
    p_styles.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_styles.add_argument("--dir", default=None, help="指定任务输出目录")
    p_styles.add_argument("--kind", default="",
                          help="逗号分隔，可选：quantum,wechat,xiaohongshu（默认全部）")
    p_styles.add_argument("--force", action="store_true",
                          help="忽略已有缓存重新生成（修复处理中途生成导致的缺图产物）")
    p_styles.add_argument("--level", default=None,
                          choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_styles.set_defaults(func=cmd_styles)

    p_pdf = sub.add_parser("pdf", help="把报告导出为 PDF（内置中文字体）")
    p_pdf.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_pdf.add_argument("--dir", default=None, help="指定任务输出目录")
    p_pdf.add_argument("--type", default="report",
                       choices=["report", "detailed", "outline", "all"],
                       help="report=精简报告(默认) / detailed=详细报告 / outline=图文大纲 / all=合并")
    p_pdf.add_argument("--out", default=None, help="输出文件路径（默认写入任务目录）")
    p_pdf.set_defaults(func=cmd_pdf)

    args = parser.parse_args()
    home = project_home(args.home)
    reexec_with_venv(home)
    args.func(args)


if __name__ == "__main__":
    main()
