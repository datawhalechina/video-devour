# -*- coding: utf-8 -*-
"""
报告知识可视化生成器

从已完成的任务报告生成：
- 思维导图（markmap 交互式层级导图）
- 知识图谱（ECharts 力导向概念关系网络）

供 FastAPI 端点与 Agent Skill（.agents/skills/videodevour）共用。
生成结果缓存到任务输出目录（mindmap.html / knowledge_graph.html）。
"""
import json
import logging
import re
from pathlib import Path

from backend.algorithm.llm_handler import LLMHandler

# ---------------------------------------------------------------------------
# Prompt 与模板
# ---------------------------------------------------------------------------

MINDMAP_SYSTEM_PROMPT = (
    "你是一位专业的知识架构师，擅长把课程内容整理成层级清晰的思维导图。"
    "只输出大纲本身，不要任何解释文字。"
)

MINDMAP_PROMPT_TEMPLATE = """请把以下课程报告整理为思维导图的层级大纲，用于 markmap 渲染。

要求：
1. 第一行为一级标题：# 课程中心主题（≤15字）
2. 用无序列表表达 3 层左右的分支结构（章节 → 核心要点 → 关键细节）
3. 每个节点不超过 20 字，保留关键术语与英文专有名词
4. 忠于原报告内容，不要新增报告之外的观点
5. 只输出 Markdown（标题+列表），不要 markdown 代码块标记

课程报告：
---
{report}
---
"""

KNOWLEDGE_GRAPH_SYSTEM_PROMPT = (
    "你是知识图谱构建专家，擅长从教学内容中抽取概念与关系。"
    "只输出严格的 JSON，不要 markdown 代码块标记，不要任何解释。"
)

KNOWLEDGE_GRAPH_PROMPT_TEMPLATE = """分析以下课程报告，构建知识图谱。

输出严格 JSON，结构如下：
{{
  "categories": ["类别1", "类别2", ...],
  "nodes": [{{"name": "概念名", "category": 0, "desc": "一句话说明"}}],
  "links": [{{"source": "概念A", "target": "概念B", "relation": "关系（≤8字）"}}]
}}

要求：
1. categories 为节点类别（如 核心概念 / 技术方法 / 应用场景 / 实践要点 等），3-5 个
2. nodes 8-16 个，覆盖报告的主要概念；category 为类别下标（从 0 开始）
3. links 10-20 条，关系准确、简明；source/target 必须是 nodes 中已有的 name
4. 使用简体中文

课程报告：
---
{report}
---
"""

# 注意：本模板为普通字符串（使用 .replace 注入数据），花括号不做 f-string 转义
KNOWLEDGE_GRAPH_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>课程知识图谱</title>
<style>
  html, body { margin: 0; padding: 0; height: 100%; background: #f8fafc; }
  /* 固定最小尺寸：后台/隐藏标签初始化时容器可能为 0，导致空白 */
  #graph { position: absolute; inset: 0; min-width: 1024px; min-height: 600px; }
  .toolbar { position: fixed; top: 12px; left: 16px; z-index: 10;
    font: 14px/1.6 -apple-system, "PingFang SC", sans-serif; color: #334155; }
  .toolbar small { color: #94a3b8; }
</style>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body>
<div class="toolbar"><b>课程知识图谱</b> <small>拖动平移 · 滚轮缩放 · 拖拽节点调整布局 · 悬停查看说明</small></div>
<div id="graph"></div>
<script>
const graphData = __GRAPH_DATA__;
const chart = echarts.init(document.getElementById('graph'));
const option = {
  backgroundColor: '#f8fafc',
  tooltip: {
    formatter: (p) => p.dataType === 'edge'
      ? (p.data.source + ' —[' + p.data.relation + ']→ ' + p.data.target)
      : (p.data.desc ? '<b>' + p.name + '</b><br/>' + p.data.desc : '<b>' + p.name + '</b>')
  },
  legend: {
    data: graphData.categories.map(c => c.name),
    top: 10, textStyle: { color: '#334155' }
  },
  series: [{
    type: 'graph', layout: 'force', roam: true,
    label: { show: true, fontSize: 12, color: '#0f172a' },
    edgeLabel: { show: true, fontSize: 10, color: '#64748b',
      formatter: (p) => p.data.relation || '' },
    edgeSymbol: ['none', 'arrow'], edgeSymbolSize: 8,
    lineStyle: { color: '#94a3b8', width: 1.5, curveness: 0.1 },
    force: { repulsion: 420, edgeLength: 130, gravity: 0.08 },
    emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
    categories: graphData.categories,
    data: graphData.nodes,
    links: graphData.links,
  }]
};
chart.setOption(option);
window.addEventListener('resize', () => chart.resize());
// 标签页从后台切换到前台时重新量取容器尺寸，避免空白
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) setTimeout(() => chart.resize(), 100);
});
</script>
</body>
</html>"""


def _read_report_text(output_dir: Path) -> str:
    for name in ("final_report.md", "detailed_outline.md"):
        p = output_dir / name
        if p.exists():
            text = p.read_text(encoding="utf-8")
            if len(text) > 20000:
                text = text[:20000] + "\n\n... (内容过长，已截取)"
            return text
    raise ValueError("任务尚未生成报告")


def _run_llm(system_prompt: str, prompt: str) -> str:
    llm = LLMHandler()
    out = llm.get_response(prompt, system_message=system_prompt)
    return re.sub(r"^```(?:html|markdown|json)?\s*|```$", "", out.strip(),
                  flags=re.MULTILINE).strip()


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def generate_mindmap(output_dir, education_level: str = None) -> Path:
    """
    生成（或读取缓存的）思维导图 HTML。

    Args:
        output_dir: 任务输出目录（含 final_report.md）
        education_level: 学习阶段，为空时使用设置中的默认值

    Returns:
        Path: mindmap.html 路径

    Raises:
        ValueError: 报告不存在或生成失败
    """
    output_dir = Path(output_dir)
    cache = output_dir / "mindmap.html"
    if cache.exists():
        return cache

    report_text = _read_report_text(output_dir)
    if education_level is None:
        try:
            from backend.algorithm.settings_store import load_settings
            education_level = load_settings().get("default_education_level")
        except Exception:
            education_level = None
    prompt = MINDMAP_PROMPT_TEMPLATE.format(report=report_text)
    md = _run_llm(MINDMAP_SYSTEM_PROMPT, prompt)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>课程思维导图</title>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: #f8fafc; }}
  .markmap {{ position: absolute; inset: 0; }}
  .markmap > svg {{ width: 100%; height: 100%; }}
  .toolbar {{ position: fixed; top: 12px; left: 16px; z-index: 10;
    font: 14px/1.6 -apple-system, "PingFang SC", sans-serif; color: #334155; }}
  .toolbar small {{ color: #94a3b8; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script>
</head>
<body>
<div class="toolbar"><b>课程思维导图</b> <small>滚轮缩放 · 拖动平移 · 点击节点折叠</small></div>
<div class="markmap"><script type="text/template">
{md}
</script></div>
</body>
</html>"""

    cache.write_text(html, encoding="utf-8")
    logging.info(f"思维导图已生成: {cache}")
    return cache


def generate_knowledge_graph(output_dir, education_level: str = None) -> Path:
    """
    生成（或读取缓存的）知识图谱 HTML。

    Returns:
        Path: knowledge_graph.html 路径

    Raises:
        ValueError: 报告不存在 / JSON 解析失败 / 图谱过于稀疏
    """
    output_dir = Path(output_dir)
    cache = output_dir / "knowledge_graph.html"
    if cache.exists():
        return cache

    report_text = _read_report_text(output_dir)
    if education_level is None:
        try:
            from backend.algorithm.settings_store import load_settings
            education_level = load_settings().get("default_education_level")
        except Exception:
            education_level = None
    prompt = KNOWLEDGE_GRAPH_PROMPT_TEMPLATE.format(report=report_text)
    raw = _run_llm(KNOWLEDGE_GRAPH_SYSTEM_PROMPT, prompt)

    try:
        graph = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("知识图谱 JSON 解析失败，请重试")
        graph = json.loads(raw[start:end + 1])

    categories = [{"name": c} for c in graph.get("categories", [])] or [{"name": "概念"}]
    nodes = [
        {
            "name": n.get("name", f"节点{i}"),
            "category": min(int(n.get("category", 0)), len(categories) - 1),
            "desc": n.get("desc", ""),
            "symbolSize": 30 + min(len(graph.get("links", [])), 40) // 10,
        }
        for i, n in enumerate(graph.get("nodes", []))
    ]
    names = {n["name"] for n in nodes}
    links = [
        {"source": l["source"], "target": l["target"], "relation": l.get("relation", "关联")}
        for l in graph.get("links", [])
        if l.get("source") in names and l.get("target") in names and l["source"] != l["target"]
    ]
    if len(nodes) < 2 or not links:
        raise ValueError("知识图谱抽取结果过于稀疏，请重试")

    graph_data = {"categories": categories, "nodes": nodes, "links": links}
    html = KNOWLEDGE_GRAPH_TEMPLATE.replace(
        "__GRAPH_DATA__", json.dumps(graph_data, ensure_ascii=False)
    )
    cache.write_text(html, encoding="utf-8")
    logging.info(f"知识图谱已生成: {cache}")
    return cache
