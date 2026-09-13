# -*- coding: utf-8 -*-
"""
生成《MCP 测试案例一览》：挑选若干真实文章，走标准 MCP 协议逐个调用工具，
把「调用入参 + 实际返回」原样抓下来，写成 Markdown 案例集。

运行：
    .venv/bin/python mcp_server/gen_case_overview.py
输出：
    mcp_server/MCP测试案例一览.md
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
SERVER = PROJECT_ROOT / "mcp_server" / "videodevour_library_mcp.py"
PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
OUT = PROJECT_ROOT / "mcp_server" / "MCP测试案例一览.md"

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SESSION = None
CASES = []          # 抓取到的案例（供文档生成）


def text_of(res):
    return "\n".join(getattr(c, "text", "") for c in (res.content or []) if getattr(c, "text", None))


async def call(name, args):
    res = await SESSION.call_tool(name, args)
    return res, text_of(res)


def clip(text, n=700):
    text = (text or "").strip()
    return text if len(text) <= n else text[:n].rstrip() + f"\n…（共 {len(text)} 字符，此处截断）"


def add(case_id, title, tool, args, result_text, is_error=False, note=""):
    CASES.append({
        "id": case_id, "title": title, "tool": tool, "args": args,
        "result": result_text, "is_error": is_error, "note": note,
    })


def parse_header(txt):
    """从 get_article 返回中解析真实 (类型, 标题, 来源平台, 版本)。"""
    label = title = platform = version = ""
    lines = (txt or "").splitlines()
    if lines and lines[0].startswith("【"):
        seg = lines[0]
        if "】" in seg:
            label, title = seg[1:].split("】", 1)
    for l in lines[:3]:
        if l.startswith("来源:"):
            parts = [p.strip() for p in l[3:].split("|")]
            platform = parts[0] if parts else ""
            version = parts[-1] if len(parts) >= 3 else ""
    return label, title, platform, version


async def pick_doc(query, scope):
    """经 MCP 检索并解析首个命中的 (doc_id, run_id, title)。"""
    _, txt = await call("search_library", {"query": query, "scope": scope, "top_k": 1})
    doc_id = run_id = title = None
    for l in txt.splitlines():
        if "doc_id:" in l:
            doc_id = l.split("doc_id:")[1].split("|")[0].strip()
            if "run_id=" in l:
                run_id = l.split("run_id=")[1].rstrip("）").strip()
        if l and l[0].isdigit() and ". 【" in l:
            title = l.split("】", 1)[1][:50]
    return doc_id, run_id, title


async def article_case(case_id, query, scope, label_txt):
    """检索 → 取全文；标题直接用**实际返回的平台/类型/标题**，避免标签与实际不符。"""
    d, r, _ = await pick_doc(query, scope)
    if not d:
        return False
    args = {"doc_id": d, "scope": scope}
    _, txt = await call("get_article", args)
    plabel, title, platform, version = parse_header(txt)
    title = (title or d)[:46]
    add(case_id,
        f"{platform or label_txt} · {plabel or scope}｜{title}（{version or 'V1'}）",
        "get_article", args, txt)
    return True


async def run():
    global SESSION
    params = StdioServerParameters(command=str(PYTHON), args=[str(SERVER)], cwd=str(PROJECT_ROOT))
    tmp = Path(tempfile.mkdtemp(prefix="vdcase_"))

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            SESSION = session
            await session.initialize()

            # ---- C1：关键词检索（B站 · 图文大纲）----
            args = {"query": "吴恩达 Agent 智能体工作流", "scope": "outline", "top_k": 3}
            _, txt = await call("search_library", args)
            add("C1", "B站 · 图文大纲｜关键词检索", "search_library", args, txt)

            # ---- C2：B站 精简报告 ----
            await article_case("C2", "沙箱 Docker 虚拟机区别", "report", "B站 · 精简报告")
            # ---- C3：B站 详细报告（原文+笔记对照）----
            await article_case("C3", "3Blue1Brown Grant Sanderson", "detailed", "B站 · 详细报告")
            # ---- C4：量子速读（衍生文体）----
            await article_case("C4", "傅里叶变换", "quantum", "B站 · 量子速读")
            # ---- C5：公众号文章（衍生文体）----
            await article_case("C5", "Agent 智能体 落地应用", "wechat", "公众号文章")
            # ---- C6：小红书笔记（衍生文体）----
            await article_case("C6", "AI 工具 教师 教学", "xiaohongshu", "小红书笔记")

            # ---- C7：跨平台 - 微信视频号 ----
            await article_case("C7", "教师的AI工具书 实操案例", "report", "微信视频号 · 精简报告")
            # ---- C8：跨平台 - YouTube ----
            await article_case("C8", "AI最前沿的人 不聊模型", "report", "YouTube · 精简报告")
            # ---- C9：跨平台 - 本地上传 ----
            await article_case("C9", "产品功能介绍", "outline", "本地上传 · 图文大纲")

            # ---- C10：无关键词浏览 ----
            args = {"scope": "report"}
            _, txt = await call("list_library", args)
            add("C10", "无关键词浏览：list_library（scope=report）", "list_library", args, txt)

            # ---- C11：多版本 run_id 精确取文 ----
            from backend.algorithm.document_library import scan_library as _scan
            from collections import defaultdict
            bydoc = defaultdict(set)
            for dd in _scan():
                bydoc[dd["doc_id"]].add(dd.get("run_id", ""))
            multi = next(((k, sorted(v)) for k, v in bydoc.items() if len(v) >= 2), None)
            if multi:
                k, runs = multi
                for i, rid in enumerate(runs, 1):
                    args = {"doc_id": k, "scope": "report", "run_id": rid}
                    _, txt = await call("get_article", args)
                    add(f"C11.{i}", f"多版本取文：run_id={rid[-15:]}（同 doc 第 {i} 版）",
                        "get_article", args, txt)

            # ---- C12：导出单篇 ZIP ----
            d = (await pick_doc("沙箱 Docker 虚拟机区别", "report"))[0]
            if d:
                args = {"doc_id": d, "scope": "report", "target_dir": str(tmp / "case12")}
                _, txt = await call("export_article", args)
                path = txt.split("已导出:")[1].split("（")[0].strip() if "已导出:" in txt else ""
                listing = ""
                if path and Path(path).exists():
                    import zipfile
                    with zipfile.ZipFile(path) as zf:
                        listing = "\n".join("  - " + n for n in zf.namelist()[:8])
                add("C12", "导出单篇为 ZIP（md + 引用图片）", "export_article", args,
                    txt + ("\nZIP 内容：\n" + listing if listing else ""))

            # ---- C13：整库导出 ----
            args = {"target_dir": str(tmp / "case13")}
            _, txt = await call("export_library", args)
            add("C13", "导出整库 ZIP（含 manifest.json）", "export_library", args, txt)

            # ---- C14：边界 — 无命中 ----
            args = {"query": "zzqqxxyywwvv"}
            _, txt = await call("search_library", args)
            add("C14", "边界 · 无命中", "search_library", args, txt)

            # ---- C15：边界 — 非法 doc_id / scope ----
            args = {"doc_id": "not-a-real-id", "scope": "report"}
            _, txt = await call("get_article", args)
            add("C15", "边界 · 非法 doc_id", "get_article", args, txt)
            args = {"doc_id": "not-a-real-id", "scope": "bogus"}
            _, txt = await call("get_article", args)
            add("C16", "边界 · 非法 scope", "get_article", args, txt)


def render():
    lines = []
    lines.append("# VideoDevour 文档库 MCP — 测试案例一览\n")
    lines.append("> 本文由 `mcp_server/gen_case_overview.py` 自动生成：")
    lines.append("> 通过标准 MCP 协议（stdio）真实调用服务，入参与返回均为**原样抓取**（长文做截断）。")
    lines.append("> 配套回归测试见 `test_mcp_client.py`，缺陷分析见 `MCP测试报告.md`。\n")
    lines.append(f"- 生成命令：`.venv/bin/python mcp_server/gen_case_overview.py`")
    lines.append(f"- 案例总数：**{len(CASES)}**")
    tools = sorted({c['tool'] for c in CASES})
    lines.append(f"- 覆盖工具：{'、'.join(tools)}\n")
    lines.append("## 案例索引\n")
    lines.append("| 编号 | 案例 | 工具 |")
    lines.append("| --- | --- | --- |")
    for c in CASES:
        lines.append(f"| {c['id']} | {c['title']} | `{c['tool']}` |")
    lines.append("")
    for c in CASES:
        lines.append(f"## {c['id']} · {c['title']}\n")
        lines.append(f"- **工具**：`{c['tool']}`")
        lines.append(f"- **入参**：\n\n```json\n{json.dumps(c['args'], ensure_ascii=False, indent=2)}\n```\n")
        if c["note"]:
            lines.append(f"- **说明**：{c['note']}\n")
        lines.append("- **返回**：\n")
        lines.append("```text")
        lines.append(clip(c["result"]))
        lines.append("```\n")
        lines.append("---\n")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"已写入 {OUT}（{len(CASES)} 个案例）")


if __name__ == "__main__":
    asyncio.run(run())
    render()
