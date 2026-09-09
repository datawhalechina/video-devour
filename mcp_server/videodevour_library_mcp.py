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

mcp = FastMCP(
    "videodevour-library",
    instructions=(
        "VideoDevour 个人文档库：检索与获取本地所有已生成视频笔记/报告。"
        "推荐流程：先用 search_library 按关键词检索（返回 top-k 摘要与 doc_id/scope），"
        "命中后用 get_article 取全文。scope 取值：outline=图文大纲, "
        "report=精简报告, detailed=详细报告（原文+笔记对照）。"
    ),
)


@mcp.tool()
def search_library(query: str, scope: str = "all", top_k: int = 5) -> str:
    """BM25 相关度检索全部视频笔记/报告，返回 top-k 命中摘要。

    Args:
        query: 检索关键词（支持中文/英文/混合）
        scope: 文章类型过滤：all | outline（图文大纲）| report（精简报告）| detailed（详细报告）
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
            f"   doc_id: {r['doc_id']} | scope: {r['scope']}\n"
            f"   摘要: {r['snippet']}\n"
        )
    lines.append("\n（需要全文时，用对应 doc_id + scope 调用 get_article）")
    return "\n".join(lines)


@mcp.tool()
def get_article(doc_id: str, scope: str) -> str:
    """获取单篇文章的完整 Markdown 全文。

    Args:
        doc_id: 任务 ID（来自 search_library 结果）
        scope: 文章类型：outline | report | detailed
    """
    result = _get_article(doc_id, scope)
    if not result:
        return f"文章不存在：doc_id={doc_id}, scope={scope}。请先用 search_library 确认。"
    header = (
        f"【{result['label']}】{result['doc']['title']}\n"
        f"来源: {result['doc']['platform_label']} | 生成: {result['doc']['created_at'][:10]}\n"
        f"{'=' * 40}\n\n"
    )
    return header + result["content"]


@mcp.tool()
def list_library(scope: str = "all") -> str:
    """列出文档库全部文章索引（无关键词浏览）。

    Args:
        scope: all | outline | report | detailed
    """
    result = _list_library(scope)
    if not result["results"]:
        return "文档库为空。"
    lines = [f"共 {result['total']} 篇：\n"]
    for r in result["results"]:
        lines.append(f"- 【{r['label']}】{r['title']}（{r['created_at'][:10]}）doc_id={r['doc_id']} scope={r['scope']}")
    return "\n".join(lines)


@mcp.tool()
def export_article(doc_id: str, scope: str, target_dir: str = "") -> str:
    """把某篇导出为本地 ZIP 文件（md + 引用图片），返回文件绝对路径。

    Args:
        doc_id: 任务 ID
        scope: outline | report | detailed
        target_dir: 导出目录（默认系统的下载/临时目录）
    """
    result = _export_article_zip(doc_id, scope)
    if not result:
        return f"文章不存在：doc_id={doc_id}, scope={scope}。"
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


if __name__ == "__main__":
    mcp.run()   # stdio
