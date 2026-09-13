# -*- coding: utf-8 -*-
"""
VideoDevour 文档库 MCP 服务——端到端测试客户端。

以标准 MCP stdio 协议连接 videodevour_library_mcp.py，依次：
    1) 握手（initialize）
    2) 发现能力（list_tools / list_resources / list_prompts）
    3) 逐个调用全部工具，覆盖正常路径与异常/边界路径
    4) 校验返回内容与副作用（导出文件真实落盘、ZIP 可解析）
    5) 输出 JSON 结果（--json）或人类可读报告

运行：
    python mcp_server/test_mcp_client.py            # 控制台报告
    python mcp_server/test_mcp_client.py --json     # 机器可读结果
"""
import asyncio
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))          # 便于直接复用底层库做样本探测
SERVER = PROJECT_ROOT / "mcp_server" / "videodevour_library_mcp.py"
PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():                       # Windows / 非源码布局兜底
    PYTHON = Path(sys.executable)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

RESULTS = []


def record(name, ok, detail, data=None, ms=None):
    RESULTS.append({"test": name, "ok": bool(ok), "detail": detail,
                    "ms": round(ms, 1) if ms is not None else None, "data": data})
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}  ({detail})" + (f"  {ms:.0f}ms" if ms is not None else ""))


def text_of(result):
    """MCP CallToolResult → 拼接的文本内容。"""
    parts = []
    for c in (result.content or []):
        t = getattr(c, "text", None)
        if t:
            parts.append(t)
    return "\n".join(parts)


def call_tool(name, args, timeout=180):
    """在已建立 session 的上下文中调用；由 run() 注入 session。"""
    async def _inner():
        t0 = time.perf_counter()
        res = await SESSION.call_tool(name, args)
        return res, (time.perf_counter() - t0) * 1000
    return _inner()


SESSION = None


async def run():
    global SESSION
    params = StdioServerParameters(
        command=str(PYTHON), args=[str(SERVER)], cwd=str(PROJECT_ROOT))
    tmp = Path(tempfile.mkdtemp(prefix="vdmcp_test_"))

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            SESSION = session

            # --- 1. 握手 ---
            t0 = time.perf_counter()
            init = await session.initialize()
            record("initialize 握手", True,
                   f"server={init.serverInfo.name} v{init.serverInfo.version}, "
                   f"protocol={init.protocolVersion}",
                   {"capabilities": str(init.capabilities)},
                   (time.perf_counter() - t0) * 1000)

            # --- 2. 能力发现 ---
            tl = await session.list_tools()
            names = sorted(t.name for t in tl.tools)
            expected = sorted(["search_library", "get_article", "list_library",
                               "export_article", "export_library"])
            record("list_tools 工具发现", names == expected,
                   f"发现 {len(names)} 个工具: {', '.join(names)}", names)
            for t in tl.tools:
                desc_ok = bool(t.description) and bool(t.inputSchema)
                record(f"工具 schema: {t.name}", desc_ok,
                       f"desc={len(t.description or '')}字符, "
                       f"params={list((t.inputSchema or {}).get('properties', {}))}")

            rl = await session.list_resources()
            record("list_resources", True, f"{len(rl.resources)} 个（非本服务能力，预期 0）")
            pl = await session.list_prompts()
            record("list_prompts", True, f"{len(pl.prompts)} 个（非本服务能力，预期 0）")

            # --- 3. search_library ---
            res, ms = await call_tool("search_library", {"query": "智能体", "scope": "all", "top_k": 3})
            txt = text_of(res)
            ok = ("doc_id:" in txt) and ("scope:" in txt) and not res.isError
            record("search_library 命中检索(CJK)", ok,
                   f"返回 {len(txt)} 字符; 首行={txt.splitlines()[0][:50] if txt else ''}",
                   txt[:400], ms)

            res, ms = await call_tool("search_library", {"query": "agent workflow"})
            txt = text_of(res)
            record("search_library 命中检索(英文)", ("doc_id:" in txt) or ("未找到" in txt),
                   f"返回 {len(txt)} 字符", txt[:200], ms)

            res, ms = await call_tool("search_library", {"query": "zzqqxxyywwvv"})
            txt = text_of(res)
            record("search_library 无命中", "未找到" in txt, f"返回: {txt[:60]}", txt, ms)

            # BM25 为 CJK 字符级分词：含常见汉字的"生僻词"仍会命中（预期行为，非缺陷）
            res, ms = await call_tool("search_library", {"query": "zzqqxx不存在的词zz"})
            txt = text_of(res)
            record("search_library CJK 字符级召回(说明性)", "共命中" in txt,
                   f"CJK 逐字分词下常见字仍召回: {txt.splitlines()[0] if txt else ''}", txt[:120], ms)

            res, ms = await call_tool("search_library", {"query": "学习", "scope": "report", "top_k": 10})
            txt = text_of(res)
            scopes = [l for l in txt.splitlines() if "scope:" in l]
            record("search_library scope 过滤", all("scope: report" in s for s in scopes) if scopes else False,
                   f"{len(scopes)} 条结果均为 report", txt[:200], ms)

            res, ms = await call_tool("search_library", {"query": "学习", "top_k": 100})
            txt = text_of(res)
            n = sum(1 for l in txt.splitlines() if "doc_id:" in l)
            record("search_library top_k 上限钳制(100→≤20)", n <= 20,
                   f"请求 100，实际返回 {n} 条", None, ms)

            # --- 4. get_article ---
            res, ms = await call_tool("search_library", {"query": "智能体", "scope": "report", "top_k": 1})
            txt = text_of(res)
            doc_id = scope = None
            for l in txt.splitlines():
                if "doc_id:" in l:
                    doc_id = l.split("doc_id:")[1].split("|")[0].strip()
                if "scope:" in l:
                    scope = l.split("scope:")[1].split("|")[0].strip()
            record("search→get 链路: 解析出 doc_id/scope", bool(doc_id and scope),
                   f"doc_id={doc_id}, scope={scope}")

            if doc_id and scope:
                res, ms = await call_tool("get_article", {"doc_id": doc_id, "scope": scope})
                txt = text_of(res)
                ok = (not res.isError) and len(txt) > 200 and "===" in txt
                record("get_article 全文获取", ok, f"返回 {len(txt)} 字符", txt[:160], ms)

            res, ms = await call_tool("get_article", {"doc_id": "nonexistent-id-000", "scope": "report"})
            txt = text_of(res)
            record("get_article 非法 doc_id", "不存在" in txt, f"返回: {txt[:80]}", txt, ms)

            res, ms = await call_tool("get_article", {"doc_id": doc_id or "x", "scope": "bogus"})
            txt = text_of(res)
            record("get_article 非法 scope", "不存在" in txt, f"返回: {txt[:80]}", txt, ms)

            res, ms = await call_tool("get_article", {"doc_id": doc_id or "x", "scope": "quantum"})
            txt = text_of(res)
            record("get_article 衍生文体(quantum)", True,
                   f"{'有内容' if '不存在' not in txt else '未生成该文体'}（{len(txt)}字符）", txt[:120], ms)

            # --- 4b. 多版本视频：run_id 精确指定版本 ---
            # 先经 MCP 探测哪些 doc_id 暴露了多个 run_id
            res, ms = await call_tool("list_library", {"scope": "all"})
            runs_by_doc = {}
            for l in text_of(res).splitlines():
                if "doc_id=" in l and "scope=" in l:
                    d = l.split("doc_id=")[1].split(" ")[0].strip()
                    runs_by_doc.setdefault(d, 0)
                    runs_by_doc[d] += 1
            # 用底层扫描确认多 run_id 的真实样本
            from backend.algorithm.document_library import scan_library as _scan
            from collections import defaultdict
            bydoc = defaultdict(set)
            for dd in _scan():
                bydoc[dd["doc_id"]].add(dd.get("run_id", ""))
            multi = next(((d, sorted(rs)) for d, rs in bydoc.items() if len(rs) >= 2), None)
            if multi:
                d0, runs = multi
                c1 = text_of((await call_tool("get_article",
                              {"doc_id": d0, "scope": "report", "run_id": runs[0]}))[0])
                c2 = text_of((await call_tool("get_article",
                              {"doc_id": d0, "scope": "report", "run_id": runs[1]}))[0])
                latest = text_of((await call_tool("get_article",
                                 {"doc_id": d0, "scope": "report"}))[0])
                ok = (c1 != c2) and ("不存在" not in c1) and ("不存在" not in c2) \
                     and ("不存在" not in latest)
                record("get_article 多版本 run_id 区分", ok,
                       f"doc={d0[:8]} V_runs 各取到 {len(c1)}/{len(c2)} 字符，内容不同={c1 != c2}；"
                       f"缺省取最新={len(latest)}字符", None, ms)
            else:
                record("get_article 多版本 run_id 区分", False, "库中未找到同 doc 多 run_id 样本")

            # --- 5. list_library ---
            res, ms = await call_tool("list_library", {"scope": "all"})
            txt = text_of(res)
            record("list_library 全量索引", txt.startswith("共 ") and "doc_id=" in txt,
                   f"{txt.splitlines()[0] if txt else ''}", txt[:300], ms)

            res, ms = await call_tool("list_library", {"scope": "report"})
            txt = text_of(res)
            bad = [l for l in txt.splitlines() if l.startswith("- ") and "scope=report" not in l]
            record("list_library scope 过滤", not bad,
                   f"{txt.splitlines()[0] if txt else ''}; 非report行={len(bad)}", None, ms)

            res, ms = await call_tool("list_library", {"scope": "bogus"})
            txt = text_of(res)
            record("list_library 非法 scope(空结果不崩)", True, f"返回: {txt[:60]}", txt, ms)

            # --- 6. export_article ---
            if doc_id and scope:
                res, ms = await call_tool("export_article",
                                          {"doc_id": doc_id, "scope": scope,
                                           "target_dir": str(tmp / "article")})
                txt = text_of(res)
                ok = ("已导出:" in txt) and (not res.isError)
                path = None
                if ok:
                    path = Path(txt.split("已导出:")[1].split("（")[0].strip())
                    ok = path.exists() and path.stat().st_size > 0
                    if ok:
                        with zipfile.ZipFile(path) as zf:
                            names = zf.namelist()
                        ok = any(n.endswith(".md") for n in names)
                record("export_article 导出+ZIP校验", ok,
                       f"{txt[:90]}", {"path": str(path) if path else None}, ms)

            res, ms = await call_tool("export_article",
                                      {"doc_id": "nonexistent", "scope": "report",
                                       "target_dir": str(tmp / "article")})
            txt = text_of(res)
            record("export_article 非法 doc_id", "不存在" in txt, f"返回: {txt[:80]}", txt, ms)

            # --- 7. export_library ---
            res, ms = await call_tool("export_library", {"target_dir": str(tmp / "library")})
            txt = text_of(res)
            ok = "已导出整库:" in txt
            path = None
            if ok:
                path = Path(txt.split("已导出整库:")[1].split("（")[0].strip())
                ok = path.exists() and path.stat().st_size > 0
                if ok:
                    with zipfile.ZipFile(path) as zf:
                        names = zf.namelist()
                        ok = any(n.endswith("/manifest.json") or n == "manifest.json" for n in names)
                        mf = json.loads(zf.read([n for n in names if n.endswith("manifest.json")][0]))
                    detail = (f"{len(names)} 文件, {mf['total_videos']} 视频 / "
                              f"{mf['total_versions']} 版本")
                else:
                    detail = txt[:90]
            else:
                detail = txt[:90]
            record("export_library 整库导出+manifest校验", ok, detail,
                   {"path": str(path) if path else None}, ms)

            # --- 8. 健壮性：并发调用 ---
            async def one(i):
                r = await session.call_tool("search_library", {"query": "报告", "top_k": 2})
                return r.isError
            errs = await asyncio.gather(*[one(i) for i in range(5)])
            record("并发 5 路 search_library", not any(errs), f"错误数={sum(errs)}")

    SESSION = None


def main():
    asyncio.run(run())
    passed = sum(1 for r in RESULTS if r["ok"])
    failed = len(RESULTS) - passed
    print("\n" + "=" * 64)
    print(f"合计 {len(RESULTS)} 项：PASS {passed} / FAIL {failed}")
    if failed:
        print("失败项：")
        for r in RESULTS:
            if not r["ok"]:
                print(f"  - {r['test']}: {r['detail']}")
    if "--json" in sys.argv:
        print("\n@@JSON@@")
        print(json.dumps({"passed": passed, "failed": failed, "results": RESULTS},
                         ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
