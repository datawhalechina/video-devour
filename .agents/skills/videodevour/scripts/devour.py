#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VideoDevour skill 入口脚本（跨 agent 通用，遵循 .agents/skills 约定）

把视频（B站/YouTube/抖音/X/小宇宙 链接、微信视频号分享链接、腾讯会议短链/会议号或本地文件）
端到端处理为中文图文报告。
自动切换到 VideoDevour 项目的 .venv 运行，无需手动激活环境。
另可检索项目本地积累的「文档库」（历史任务的全部报告/笔记），供 agent 复用已有成果；
报告可一键发布为微信公众号图文草稿。

项目根目录解析顺序:
  1. --home 参数 / VIDEO_DEVOUR_HOME 环境变量
  2. 脚本所在仓库（本文件位于 <repo>/.agents/skills/videodevour/scripts/ 时自动识别）
  3. 默认安装路径

用法:
  devour.py search "关键词" [--platform bilibili|youtube|douyin] [--max N]
  devour.py info <url>                          # 支持 B站/YouTube/抖音/X/小宇宙/视频号/腾讯会议
  devour.py notes <url|会议号> [--level 学习阶段]  # B站/YouTube/腾讯会议，秒级纯文本笔记
  devour.py wechat <视频号分享链接> [--check]
  devour.py douyin <抖音链接> [--check]
  devour.py meeting <会议短链|会议号|meeting_id> [--check]
  devour.py process <url|会议号|本地视频路径> [--level 高中|初中|小学] [--home 项目目录]
  devour.py mindmap [--latest | --dir 输出目录] [--open] [--level 学习阶段]
  devour.py graph   [--latest | --dir 输出目录] [--open] [--level 学习阶段]
  devour.py card    [--latest | --dir 输出目录] [--open] [--level 学习阶段]
  devour.py styles  [--latest | --dir 输出目录] [--kind html,quantum,wechat,xiaohongshu]
  devour.py pdf     [--latest | --dir 输出目录] [--type report|detailed|outline|all] [--out 文件]
  devour.py md      [--latest | --dir 输出目录] [--type report|detailed|outline|all]
                   [--mode inline|zip] [--out 文件]
  devour.py mp      [--check] [--latest | --dir 输出目录] [--type report|detailed]
                   [--title 标题] [--digest 摘要]        # 公众号图文草稿
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
import re
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


def _run_extras(out_dir: Path, extras_spec: str, level=None) -> dict:
    """按需生成附加产物（mindmap/graph/card），与 WebUI 的 --extras 一致。"""
    extras_result = {}
    extras = [x.strip() for x in (extras_spec or "").split(",") if x.strip()]
    labels = {"mindmap": "思维导图", "graph": "知识图谱", "card": "学习卡片"}
    for kind in extras:
        if kind not in labels:
            continue
        print(f"生成{labels[kind]}（LLM 生成约 10-30 秒）...")
        try:
            from backend.algorithm import report_viz
            if kind == "card":
                path = report_viz.generate_learning_card(out_dir, level)
            else:
                fn = report_viz.generate_mindmap if kind == "mindmap" else report_viz.generate_knowledge_graph
                path = fn(out_dir, level)
            extras_result[kind] = str(path)
        except Exception as e:
            extras_result[kind] = f"生成失败: {e}"
    return extras_result


def _finish_outcome(home: Path, out_dir: Path, args) -> None:
    """收尾：可选 extras + 汇总产物 JSON（视频/会议两条管线共用）。"""
    outcome = {"output_dir": str(out_dir), **_collect_artifacts(out_dir)}
    extras_result = _run_extras(out_dir, getattr(args, "extras", "") or "", args.level)
    if extras_result:
        outcome["extras"] = extras_result
    if not outcome.get("report"):
        outcome["error"] = "处理未完成：final_report.md 未生成，请检查 processing.log"
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        sys.exit(2)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))


def _process_meeting(home: Path, args, ref: str):
    """腾讯会议任务：tmeet 拉转写 → 会议报告管线（无媒体下载，纯文字报告）。"""
    import uuid
    from backend.devour import tencent_meeting as tm
    from backend.algorithm.pipeline import run_meeting_pipeline

    print(f"[1/2] 获取腾讯会议转写: {ref}")
    meeting_data = tm.fetch_meeting_transcript(ref)
    speakers = meeting_data.get("speakers") or []
    print(f"转写已获取: {meeting_data.get('subject') or ref}"
          f"（{len(meeting_data.get('dialogue', []))} 段、{len(speakers)} 位发言人）")

    task_id = str(uuid.uuid4())
    print(f"[2/2] 启动会议报告管线 (学习阶段: {args.level}) ...")
    run_meeting_pipeline(task_id, meeting_data, education_level=args.level)

    candidates = sorted((home / "output").glob(f"frames_{task_id}_*"),
                        key=lambda p: p.stat().st_mtime)
    if not candidates:
        print(json.dumps({"error": "会议管线未产生输出目录，请检查日志"}, ensure_ascii=False))
        sys.exit(2)
    _finish_outcome(home, candidates[-1], args)


def cmd_process(args):
    home = project_home(args.home)
    setup_project(home)

    source = args.source
    # 支持直接粘贴含链接的分享文案（微信/B站 App 分享格式）
    from backend.devour.video_downloader import detect_platform, extract_share_url
    url = extract_share_url(source)

    # 腾讯会议：短链 / 9-12 位会议号 / 19 位 meeting_id 直接进会议管线（与 WebUI 一致）
    if detect_platform(url) == "tencent_meeting" or re.fullmatch(r"\d{9,19}", source.strip()):
        _process_meeting(home, args, source)
        return

    from backend.algorithm.pipeline import run_full_pipeline

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
    _finish_outcome(home, candidates[-1], args)


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


def cmd_meeting(args):
    """腾讯会议：检查 tmeet CLI 授权（--check），或查看单场转写概况（仅取数，不走 LLM）。"""
    home = project_home(args.home)
    setup_project(home)

    from backend.devour import tencent_meeting as tm

    if args.check:
        print(json.dumps(tm.check_auth(), ensure_ascii=False, indent=2))
        return
    if not args.ref:
        print("用法: devour.py meeting <会议短链|会议号|meeting_id>（或 meeting --check 检查授权）",
              file=sys.stderr)
        sys.exit(1)
    data = tm.fetch_meeting_transcript(args.ref)
    dialogue = data.get("dialogue") or []
    print(json.dumps({
        "subject": data.get("subject"),
        "meeting_code": data.get("meeting_code"),
        "speakers": data.get("speakers"),
        "duration_minutes": round((data.get("duration_seconds") or 0) / 60),
        "dialogue_segments": len(dialogue),
        "total_chars": sum(len(d.get("text") or "") for d in dialogue),
        "hint": "用 process 生成图文报告，或 notes 生成文字速记（都直接支持会议链接）",
    }, ensure_ascii=False, indent=2))


def cmd_mp(args):
    """微信公众号：--check 连通性；否则把任务报告发布为图文草稿（不自动群发）。"""
    home = project_home(args.home)
    setup_project(home)

    from backend.publisher import wechat_mp

    if args.check:
        from backend.algorithm import settings_store
        s = settings_store.load_settings()
        if not ((s.get("wechat_mp_appid") or "").strip()
                and (s.get("wechat_mp_secret") or "").strip()):
            print(json.dumps({
                "configured": False,
                "message": "未配置公众号凭据。在 WebUI 设置页「微信公众号发布」填写 AppID/AppSecret，"
                           "或写入 settings.json 的 wechat_mp_appid / wechat_mp_secret",
            }, ensure_ascii=False, indent=2))
            sys.exit(1)
        try:
            count = wechat_mp.draft_count()
            print(json.dumps({"configured": True, "ok": True, "draft_count": count,
                              "message": "公众号接口连通正常"}, ensure_ascii=False, indent=2))
        except wechat_mp.WechatMpError as e:
            # 常见 40164：出口 IP 不在公众号后台白名单，报错文案会带当前 IP
            print(json.dumps({"configured": True, "ok": False, "message": str(e)},
                             ensure_ascii=False, indent=2))
            sys.exit(1)
        return

    out_dir = _resolve_task_dir(home, args)
    is_detailed = args.type == "detailed"
    report_name = "detailed_report.md" if is_detailed else "final_report.md"
    report_path = out_dir / report_name
    if not report_path.exists() or report_path.stat().st_size == 0:
        print(f"该任务没有{'详细报告' if is_detailed else '精简报告'}（{report_name}）",
              file=sys.stderr)
        sys.exit(1)

    # 封面与 WebUI 一致：关键帧优先；纯文字报告（会议/音频）自动生成标题封面
    cover = None
    kf = out_dir / "keyframes"
    if kf.is_dir():
        imgs = sorted(kf.glob("*.jpg")) + sorted(kf.glob("*.png"))
        if imgs:
            cover = str(imgs[0])

    from backend.algorithm.document_library import _title_from_report
    title = (args.title or _title_from_report(out_dir, out_dir.name)).strip()[:64]
    print(f"正在创建公众号图文草稿: {title}（{'详细报告' if is_detailed else '精简报告'}）")
    try:
        result = wechat_mp.publish_report_to_draft(
            report_path, title=title, digest=args.digest or "",
            cover_path=cover, cover_title=title)
    except wechat_mp.WechatMpError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)
    print(json.dumps({**result, "report": report_name,
                      "cover": "关键帧" if cover else "自动生成标题封面",
                      "message": "草稿已创建，请在公众号后台「草稿箱」预览确认后手动发布（不会自动群发）"},
                     ensure_ascii=False, indent=2))


def cmd_notes(args):
    """字幕速记：用平台已有字幕/会议转写生成纯文本笔记（秒级，不下载视频）"""
    home = project_home(args.home)
    setup_project(home)

    from backend.devour.video_downloader import detect_platform, extract_share_url
    from backend.devour.subtitles import generate_subtitle_notes

    url = extract_share_url(args.url or "")
    platform = detect_platform(url)
    # 会议号/meeting_id 不是 URL 形态，按 API 同款规则识别后原样传递
    if platform == "tencent_meeting" or re.fullmatch(r"\d{9,19}", (args.url or "").strip() or "x"):
        platform, url = "tencent_meeting", args.url
    if platform not in ("bilibili", "youtube", "tencent_meeting"):
        print("错误: 字幕笔记支持 B站 / YouTube / 腾讯会议链接（可直接粘贴分享文案或会议号）",
              file=sys.stderr)
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
    """生成思维导图 / 知识图谱 / 学习卡片（复用 API 同款逻辑，结果缓存到任务目录）"""
    home = project_home(args.home)
    setup_project(home)
    out_dir = _resolve_task_dir(home, args)
    labels = {"mindmap": "思维导图", "graph": "知识图谱", "card": "学习卡片"}
    label = labels[kind]
    print(f"正在为 {out_dir.name} 生成{label}（LLM 生成约 10-30 秒）...")

    from backend.algorithm import report_viz
    fn = {"mindmap": report_viz.generate_mindmap,
          "graph": report_viz.generate_knowledge_graph,
          "card": report_viz.generate_learning_card}[kind]
    path = fn(out_dir, education_level=args.level or None)

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


def cmd_speedread(args):
    """HTML 速读页：基于任务报告生成一页式速读 HTML（版式规范 answer-me-with-html）。

    --png/--pdf 用无头 Chrome 导出全页长图 / A4 PDF，便于直接传播。
    """
    home = project_home(args.home)
    setup_project(home)
    out_dir = _resolve_task_dir(home, args)

    from backend.algorithm.style_articles import generate_style
    html_path = generate_style(out_dir, "html", args.level or None,
                               force=getattr(args, "force", False))
    result = {"html": str(html_path)}
    print(f"HTML 速读页: {html_path}")

    if args.png or args.pdf:
        from backend.devour import html_export
        if args.png:
            result["png"] = html_export.export_png(html_path, out_dir / "speedread.png")
            print(f"已导出 PNG: {result['png']}")
        if args.pdf:
            result["pdf"] = html_export.export_pdf(html_path, out_dir / "speedread.pdf")
            print(f"已导出 PDF: {result['pdf']}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.open:
        import webbrowser
        webbrowser.open(f"file://{html_path}")


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
            result["styles"][scope] = "不支持的文体（可选 html/quantum/wechat/xiaohongshu）"
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


def _safe_stem(text: str, fallback: str = "videodevour") -> str:
    stem = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9_-]+", "_", (text or "").strip())[:60].strip("_")
    return stem or fallback


def _compress_image_bytes(img_path: Path, target_bytes: int = 6 * 1024) -> tuple:
    """把图片压到目标体积内（与 WebUI 导出同档策略），返回 (mime, data)。

    base64 单行超长会被部分 Markdown 查看器截断导致图片不显示，内嵌时需要控制体积。
    """
    import io
    import mimetypes
    try:
        from PIL import Image
        img = Image.open(img_path)
        img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
        for max_side in (640, 480, 360, 280):
            work = img.copy()
            if max(work.size) > max_side:
                work.thumbnail((max_side, max_side), Image.LANCZOS)
            for quality in (70, 60, 50, 40):
                buf = io.BytesIO()
                work.save(buf, format="JPEG", quality=quality, optimize=True)
                data = buf.getvalue()
                if len(data) <= target_bytes:
                    return "image/jpeg", data
        return "image/jpeg", data
    except Exception:
        mime = mimetypes.guess_type(str(img_path))[0] or "image/jpeg"
        return mime, img_path.read_bytes()


def cmd_md(args):
    """把任务报告导出为 Markdown。

    --type：report 精简报告(默认) / detailed 详细报告 / outline 图文大纲 / all 合并
    --mode：inline 图片压缩后 base64 内嵌（单文件可移植） / zip md+原图打包（原图质量）
    """
    home = project_home(args.home)
    setup_project(home)
    out_dir = _resolve_task_dir(home, args)

    sources = {"report": ("final_report.md", "精简报告"),
               "detailed": ("detailed_report.md", "详细报告"),
               "outline": ("detailed_outline.md", "图文大纲")}
    sections = []
    if args.type == "all":
        headers = {"outline": "内容大纲", "report": "精简报告",
                   "detailed": "详细报告（原文对照）"}
        for key in ("outline", "report", "detailed"):
            f = out_dir / sources[key][0]
            if f.exists() and f.stat().st_size > 0:
                sections.append(f"# {headers[key]}\n\n{f.read_text(encoding='utf-8')}")
        if not sections:
            print("该任务暂无可导出的报告", file=sys.stderr)
            sys.exit(1)
        label = "合并导出"
    else:
        fname, label = sources[args.type]
        f = out_dir / fname
        if not f.exists() or f.stat().st_size == 0:
            print(f"该任务没有{label}（{fname}）", file=sys.stderr)
            sys.exit(1)
        sections.append(f.read_text(encoding="utf-8"))

    # 导出文件名 = 内容标题_类型（与 WebUI 报告页导出命名一致）
    from backend.algorithm.document_library import _title_from_report
    stem = _safe_stem(_title_from_report(out_dir, out_dir.name))

    if args.mode == "zip":
        import zipfile
        out_path = Path(args.out).expanduser() if args.out else out_dir / f"{stem}_{label}.zip"
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{stem}_{label}.md", "\n\n---\n\n".join(sections))
            kf_dir = out_dir / "keyframes"
            if kf_dir.exists():
                for img in sorted(kf_dir.iterdir()):
                    if img.is_file():
                        zf.write(img, f"keyframes/{img.name}")
        print(json.dumps({"zip": str(out_path), "md_in_zip": f"{stem}_{label}.md",
                          "type": args.type, "mode": "zip", "output_dir": str(out_dir)},
                         ensure_ascii=False, indent=2))
        return

    import base64

    def _embed(md_text):
        def _replace(m):
            rel = m.group(2).replace("\\", "/").lstrip("./")
            p = out_dir / rel
            if not p.exists():
                return m.group(0)
            mime, data = _compress_image_bytes(p)
            b64 = base64.b64encode(data).decode("ascii")
            return f"![{m.group(1)}](data:{mime};base64,{b64})"
        return re.sub(r"!\[([^\]]*)\]\((?!https?://|data:)([^)]+)\)", _replace, md_text)

    content = "\n\n---\n\n".join(_embed(s) for s in sections)
    out_path = Path(args.out).expanduser() if args.out else out_dir / f"{stem}_{label}.md"
    out_path.write_text(content, encoding="utf-8")
    print(json.dumps({"md": str(out_path), "type": args.type, "mode": "inline", "label": label,
                      "bytes": len(content.encode("utf-8")), "output_dir": str(out_dir)},
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
    _scope_choices = ["all", "outline", "report", "detailed", "html", "quantum", "wechat", "xiaohongshu"]

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

    p_notes = sub.add_parser(
        "notes", help="字幕速记：用平台字幕/会议转写生成纯文本笔记（B站/YouTube/腾讯会议，秒级）")
    p_notes.add_argument("url", help="B站/YouTube 链接、腾讯会议短链/会议号，或分享文案")
    p_notes.add_argument("--level", default="自由学习",
                         choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_notes.set_defaults(func=cmd_notes)

    p_meet = sub.add_parser(
        "meeting", help="腾讯会议：检查 tmeet 授权 / 查看会议转写概况（仅取数不走 LLM）")
    p_meet.add_argument("ref", nargs="?", default=None,
                        help="会议短链（meeting.tencent.com/crm|cw/...）/ 会议号 / meeting_id")
    p_meet.add_argument("--check", action="store_true", help="检查 tmeet CLI 是否安装并已授权")
    p_meet.set_defaults(func=cmd_meeting)

    p_mp = sub.add_parser(
        "mp", help="把任务报告发布为微信公众号图文草稿（不自动群发，后台确认后手动发）")
    p_mp.add_argument("--check", action="store_true", help="检查公众号凭据与接口连通性")
    p_mp.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_mp.add_argument("--dir", default=None, help="指定任务输出目录")
    p_mp.add_argument("--type", default="report", choices=["report", "detailed"],
                      help="report=精简报告(默认) / detailed=详细报告（注意公众号正文约 2 万字符上限）")
    p_mp.add_argument("--title", default=None, help="图文标题（默认取报告标题，≤64 字）")
    p_mp.add_argument("--digest", default="", help="摘要（默认正文前 54 字）")
    p_mp.set_defaults(func=cmd_mp)

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

    p_card = sub.add_parser("card", help="为任务报告生成学习卡片（Bento Grid HTML，手机尺寸）")
    p_card.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_card.add_argument("--dir", default=None, help="指定任务输出目录")
    p_card.add_argument("--level", default=None,
                        choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_card.add_argument("--open", action="store_true", help="生成后在浏览器打开")
    p_card.set_defaults(func=lambda a: cmd_viz(a, "card"))

    p_report = sub.add_parser("report", help="查看任务报告（默认精简报告，--type 可选详细报告/大纲）")
    p_report.add_argument("--latest", action="store_true")
    p_report.add_argument("--dir", default=None)
    p_report.add_argument("--type", default="report",
                          choices=["report", "detailed", "outline"],
                          help="report=精简报告(默认) / detailed=详细报告 / outline=图文大纲")
    p_report.set_defaults(func=cmd_report)

    p_styles = sub.add_parser(
        "styles", help="生成衍生文体：HTML 速读页 / 量子速读 / 公众号文章 / 小红书笔记")
    p_styles.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_styles.add_argument("--dir", default=None, help="指定任务输出目录")
    p_styles.add_argument("--kind", default="",
                          help="逗号分隔，可选：html,quantum,wechat,xiaohongshu（默认全部）")
    p_styles.add_argument("--force", action="store_true",
                          help="忽略已有缓存重新生成（修复处理中途生成导致的缺图产物）")
    p_styles.add_argument("--level", default=None,
                          choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_styles.set_defaults(func=cmd_styles)

    p_sr = sub.add_parser("speedread", help="HTML 速读页：生成一页速读 HTML 并可导出 PNG/PDF")
    p_sr.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_sr.add_argument("--dir", default=None, help="指定任务输出目录")
    p_sr.add_argument("--force", action="store_true", help="忽略缓存重新生成")
    p_sr.add_argument("--level", default=None,
                      choices=["自由学习", "小学", "初中", "高中", "大学", "硕士", "博士", "深入研究", "垂直领域研究"])
    p_sr.add_argument("--png", action="store_true", help="同时导出全页 PNG 长图（需本机 Chrome）")
    p_sr.add_argument("--pdf", action="store_true", help="同时导出 A4 PDF（需本机 Chrome）")
    p_sr.add_argument("--open", action="store_true", help="生成后在浏览器打开")
    p_sr.set_defaults(func=cmd_speedread)

    p_pdf = sub.add_parser("pdf", help="把报告导出为 PDF（内置中文字体）")
    p_pdf.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_pdf.add_argument("--dir", default=None, help="指定任务输出目录")
    p_pdf.add_argument("--type", default="report",
                       choices=["report", "detailed", "outline", "all"],
                       help="report=精简报告(默认) / detailed=详细报告 / outline=图文大纲 / all=合并")
    p_pdf.add_argument("--out", default=None, help="输出文件路径（默认写入任务目录）")
    p_pdf.set_defaults(func=cmd_pdf)

    p_md = sub.add_parser("md", help="把报告导出为 Markdown（inline 单文件内嵌图片 / zip 打包原图）")
    p_md.add_argument("--latest", action="store_true", help="使用最新完成的任务输出")
    p_md.add_argument("--dir", default=None, help="指定任务输出目录")
    p_md.add_argument("--type", default="report",
                      choices=["report", "detailed", "outline", "all"],
                      help="report=精简报告(默认) / detailed=详细报告 / outline=图文大纲 / all=合并")
    p_md.add_argument("--mode", default="inline", choices=["inline", "zip"],
                      help="inline=图片压缩内嵌为单文件(默认，可移植) / zip=md+原图打包(保原图质量)")
    p_md.add_argument("--out", default=None, help="输出文件路径（默认写入任务目录）")
    p_md.set_defaults(func=cmd_md)

    args = parser.parse_args()
    home = project_home(args.home)
    reexec_with_venv(home)
    args.func(args)


if __name__ == "__main__":
    main()
