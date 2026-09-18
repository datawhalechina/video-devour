# -*- coding: utf-8 -*-
"""
VideoDevour 个人文档库 MCP 服务（stdio）

把本地积累的全部视频笔记/报告暴露为 MCP 工具，供 Claude Code、Cursor、
Claude Desktop 等任何支持 MCP 的 LLM 客户端检索使用。

工具集（配合使用）：
    1. search_library(query, scope, top_k)
       BM25 相关度检索，返回 top-k 摘要（含 doc_id / 类型 / 分数 / 命中片段）
    2. get_article(doc_id, scope)
       按 search 返回的 doc_id + scope 取全文 Markdown
    3. list_library(scope)
       无关键词浏览全部文档索引
    4. export_article(doc_id, scope, target_dir)
       把某篇导出为本地 .md 文件（返回绝对路径）

接入配置示例（Claude Code / Cursor 的 mcpServers）：
    {
      "mcpServers": {
        "videodevour-library": {
          "command": "<项目目录>/.venv/bin/python",
          "args": ["<项目目录>/mcp_server/videodevour_library_mcp.py"]
        }
      }
    }

运行：python mcp_server/videodevour_library_mcp.py   （stdio，无需端口）
"""
import sys
from pathlib import Path

# 保证可从项目根/任意目录运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from backend.algorithm.document_library import (
    ARTICLE_TYPES,
    export_article_zip as _export_article_zip,
    export_library_zip as _export_library_zip,
    get_article as _get_article,
    list_library as _list_library,
    search_library as _search_library,
)

# 视频存储目录与处理流水线（供 list_local_videos / process_local_video）
_VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v")


def _media_videos():
    """扫描视频存储目录（downloads + uploads）里的视频文件，返回 [(路径, 来源, 大小, mtime)]。"""
    from backend.runtime import paths as _rt
    out = []
    for src in ("downloads", "uploads"):
        d = _rt.media_subdir(src)
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in _VIDEO_EXTS:
                st = f.stat()
                out.append((str(f), src, st.st_size, st.st_mtime))
    return out

mcp = FastMCP(
    "videodevour-library",
    instructions=(
        "VideoDevour 个人文档库：检索与获取本地所有已生成视频笔记/报告。"
        "推荐流程：先用 search_library 按关键词检索（返回 top-k 摘要与 doc_id/scope/run_id），"
        "命中后用 get_article 取全文。scope 取值：outline=图文大纲, "
        "report=精简报告, detailed=详细报告（原文+笔记对照）, "
        "quantum=量子速读, wechat=公众号文章, xiaohongshu=小红书笔记。"
        "同一视频多次处理会形成多个版本：search_library 结果里的 run_id + version_label "
        "标识具体版本，取全文时把它一并传给 get_article 即可打开该版本。"
    ),
)


@mcp.tool()
def search_library(query: str, scope: str = "all", top_k: int = 5) -> str:
    """BM25 相关度检索全部视频笔记/报告，返回 top-k 命中摘要。

    Args:
        query: 检索关键词（支持中文/英文/混合）
        scope: 文章类型过滤：all（全部）| outline（图文大纲）| report（精简报告）
            | detailed（详细报告）| quantum（量子速读）| wechat（公众号）
            | xiaohongshu（小红书）
        top_k: 返回条数（默认 5，最大 20）
    """
    result = _search_library(query, scope, top_k=min(max(top_k, 1), 20))
    if not result["results"]:
        return f"未找到与 “{query}” 相关的内容。"
    lines = [f"共命中 {result['total']} 条，当前返回前 {len(result['results'])} 条：\n"]
    for i, r in enumerate(result["results"], 1):
        lines.append(
            f"{i}. 【{r['label']}】{r['title']}\n"
            f"   来源: {r['platform_label']} | 相关度: {r['score']} | 生成: {r['created_at'][:10]}\n"
            f"   doc_id: {r['doc_id']} | scope: {r['scope']} | {r.get('version_label', 'V1')}"
            f"{'（run_id=' + r['run_id'] + '）' if r.get('run_id') else ''}\n"
            f"   摘要: {r['snippet']}\n"
        )
    lines.append("\n（需要全文时，用对应 doc_id + scope 调用 get_article；多版本视频可加 run_id 指定版本）")
    return "\n".join(lines)


@mcp.tool()
def get_article(doc_id: str, scope: str, run_id: str = "") -> str:
    """获取单篇文章的完整 Markdown 全文。

    Args:
        doc_id: 任务 ID（来自 search_library 结果）
        scope: 文章类型：outline | report | detailed | quantum | wechat | xiaohongshu
        run_id: 可选，指定版本（来自 search_library 结果）；缺省取最近一次版本
    """
    result = _get_article(doc_id, scope, run_id)
    if not result:
        return f"文章不存在：doc_id={doc_id}, scope={scope}, run_id={run_id}。请先用 search_library 确认。"
    doc = result["doc"]
    header = (
        f"【{result['label']}】{doc['title']}\n"
        f"来源: {doc['platform_label']} | 生成: {(doc.get('created_at') or '')[:10]}"
        f" | {doc.get('version_label') or 'V1'}\n"
        f"{'=' * 40}\n\n"
    )
    return header + result["content"]


@mcp.tool()
def list_library(scope: str = "all") -> str:
    """列出文档库全部文章索引（无关键词浏览）。

    Args:
        scope: all | outline | report | detailed | quantum | wechat | xiaohongshu
    """
    result = _list_library(scope)
    if not result["results"]:
        return "文档库为空。"
    lines = [f"共 {result['total']} 篇：\n"]
    for r in result["results"]:
        lines.append(
            f"- 【{r['label']}】{r['title']}（{r['created_at'][:10]}）"
            f"doc_id={r['doc_id']} scope={r['scope']} {r.get('version_label', 'V1')}"
            f"{' run_id=' + r['run_id'] if r.get('run_id') else ''}"
        )
    return "\n".join(lines)


@mcp.tool()
def export_article(doc_id: str, scope: str, target_dir: str = "", run_id: str = "") -> str:
    """把某篇导出为本地 ZIP 文件（md + 引用图片），返回文件绝对路径。

    Args:
        doc_id: 任务 ID
        scope: outline | report | detailed | quantum | wechat | xiaohongshu
        target_dir: 导出目录（默认系统的下载/临时目录）
        run_id: 可选，指定版本（来自 search_library 结果）；缺省取最近一次版本
    """
    result = _export_article_zip(doc_id, scope, run_id)
    if not result:
        return f"文章不存在：doc_id={doc_id}, scope={scope}, run_id={run_id}。"
    content, suggested = result
    out_dir = Path(target_dir).expanduser() if target_dir else Path.home() / "Downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / suggested
    out_path.write_bytes(content)
    return f"已导出: {out_path}（{len(content) / 1024:.1f} KB）"


@mcp.tool()
def export_library(target_dir: str = "") -> str:
    """导出整个文档库为 ZIP（全部任务的 md + 关键帧 + manifest.json），返回文件路径。

    Args:
        target_dir: 导出目录（默认系统的下载/临时目录）
    """
    content, name = _export_library_zip()
    out_dir = Path(target_dir).expanduser() if target_dir else Path.home() / "Downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name
    out_path.write_bytes(content)
    return f"已导出整库: {out_path}（{len(content) / 1024 / 1024:.1f} MB）"


@mcp.tool()
def list_local_videos() -> str:
    """列出视频存储目录里待处理的本地视频（downloads + uploads）。

    这些视频可作为信息源：用 process_local_video 处理其中一个生成图文报告，
    再用 search_library / get_article 检索产物。返回每个视频的路径、来源、大小、修改时间。
    """
    from datetime import datetime
    videos = _media_videos()
    if not videos:
        return "视频存储目录（downloads / uploads）里暂无视频文件。"
    lines = [f"共 {len(videos)} 个本地视频：\n"]
    for path, src, size, mtime in videos:
        when = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"- [{src}] {Path(path).name}（{size / 1024 / 1024:.1f}MB，{when}）\n    路径: {path}")
    lines.append("\n用 process_local_video 处理其中一个（传路径），处理后可用 get_article 取报告。")
    return "\n".join(lines)


@mcp.tool()
def process_local_video(video_path: str, education_level: str = "自由学习") -> str:
    """处理一个本地视频：ASR → 大纲 → 关键帧 → 中文图文报告（同步执行，约数分钟）。

    Args:
        video_path: 视频文件绝对路径（可用 list_local_videos 查看）
        education_level: 自由学习/小学/初中/高中/大学/硕士/博士/深入研究/垂直领域研究
    """
    p = Path(video_path).expanduser()
    if not p.is_file():
        return f"视频文件不存在: {video_path}"
    try:
        from backend.algorithm import settings_store
        settings_store.apply_to_config()
        from backend.algorithm.pipeline import run_full_pipeline
        result = run_full_pipeline(str(p), education_level=education_level or "自由学习")
    except Exception as e:
        return f"处理失败: {type(e).__name__}: {str(e)[:200]}"
    out_dir = Path(result.get("output_dir", ""))
    parts = [f"处理完成，输出目录: {out_dir}"]
    for name, label in (("final_report.md", "精简报告"), ("detailed_report.md", "详细报告"),
                        ("detailed_outline.md", "图文大纲")):
        f = out_dir / name
        if f.exists() and f.stat().st_size > 0:
            parts.append(f"  {label}: {f}")
    return "\n".join(parts)


if __name__ == "__main__":
    mcp.run()   # stdio
