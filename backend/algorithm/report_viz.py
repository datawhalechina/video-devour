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


# ---------------------------------------------------------------------------
# 学习卡片（原 main.py 端点逻辑下沉，供 API / 任务尾部 / skill 共用）
# ---------------------------------------------------------------------------

CARD_SYSTEM_PROMPT = (
    "你是一位专业的教育科技产品设计师与前端开发专家，擅长设计适合学生学习和复习的交互式学习卡片页面。"
    "你深谙学习心理学和认知科学原理，能够将复杂的学习内容转化为清晰、易记、视觉友好的学习卡片。"
    "注意只输出一段完整的HTML代码，不要输出任何其他内容。"
)

CARD_PROMPT_TEMPLATE = """请根据以下Markdown笔记内容，生成一个适合{level}学生学习的学习卡片HTML页面。

## 设计要求（必须严格遵守）
1. 页面为手机尺寸设计，卡片宽度写死 393px，提供完整的HTML文件代码，确保可以直接运行
2. 使用 Bento Grid 风格布局，柔和深色背景（#1a1a2e 或 #16213e），高亮色区分内容类型（#4CAF50重点、#FF9800提醒、#2196F3概念）
3. 通过 CDN 引入 TailwindCSS 3.0+ 和图标库（Font Awesome 或 Material Icons）
4. 核心知识点使用超大字体粗体突出，形成清晰的视觉层次
5. 使用图标或符号标记重点内容，关键概念使用卡片式设计
6. 【重要】必须完整保留笔记中的所有标题、要点和关键信息，不要遗漏任何内容
7. 【重要】只输出HTML代码，不要输出多段，不要包含解释文字
8. 【重要】报告中若有 keyframes/ 开头的关键帧图片，必须在卡片对应章节保留 <img> 标签，
   且 src 必须**逐字复制**报告中的原始路径（禁止改写文件名、禁止使用外部图片链接）

## 笔记内容
---
{notes}
---
"""


def _embed_card_images(html: str, output_dir: Path) -> str:
    """
    卡片图片自包含处理：
    - <img> 引用的本地 keyframes 图片统一内嵌为 base64（卡片在任何上下文打开都有图）
    - LLM 改写过的错误路径按「序号前缀 → 文件名包含」自动匹配实际文件
    - 外链图片（LLM 编造的占位图）直接移除
    """
    import base64
    import mimetypes

    kf_dir = output_dir / "keyframes"
    real_files = (sorted(kf_dir.glob("*.jpg")) + sorted(kf_dir.glob("*.png"))) if kf_dir.exists() else []

    def find_real_file(ref_name: str):
        ref_name = Path(ref_name).name
        for f in real_files:                      # 精确匹配
            if f.name == ref_name:
                return f
        m_num = re.match(r"^(\d+)", ref_name)     # 序号前缀匹配（01_xxx）
        if m_num:
            for f in real_files:
                if f.name.startswith(m_num.group(1) + "_"):
                    return f
        core = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", ref_name.rsplit(".", 1)[0])
        if core:                                  # 文件名包含匹配
            for f in real_files:
                if core in re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", f.name):
                    return f
        return None

    def replace_img(match):
        tag, src = match.group(0), match.group(1)
        if src.startswith("data:"):
            return tag
        if src.startswith(("http://", "https://")):
            return ""                              # 移除编造的外链图
        if not src.startswith("keyframes/"):
            return tag
        real = find_real_file(src)
        if not real:
            return ""                              # 无法匹配的引用，移除避免破图
        mime = mimetypes.guess_type(str(real))[0] or "image/jpeg"
        data = base64.b64encode(real.read_bytes()).decode("ascii")
        return tag.replace(f'"{src}"', f'data:{mime};base64,{data}', 1)

    return re.sub(r'<img\b[^>]*src="([^"]*)"[^>]*>', replace_img, html)


def generate_learning_card(output_dir, education_level: str = None) -> Path:
    """
    生成（或读取缓存的）学习卡片 HTML（Bento Grid 手机尺寸，图片内嵌 base64）。

    Args:
        output_dir: 任务输出目录（含 final_report.md）
        education_level: 学习阶段，为空时使用设置中的默认值

    Returns:
        Path: learning_card.html 路径

    Raises:
        ValueError: 报告不存在或生成失败
    """
    output_dir = Path(output_dir)
    cache = output_dir / "learning_card.html"
    if cache.exists():
        return cache

    notes = _read_report_text(output_dir)
    if len(notes) > 24000:
        notes = notes[:24000] + "\n\n... (内容过长，已截取部分内容)"
    if education_level is None:
        try:
            from backend.algorithm.settings_store import load_settings
            education_level = load_settings().get("default_education_level")
        except Exception:
            education_level = None

    prompt = CARD_PROMPT_TEMPLATE.format(level=education_level, notes=notes)
    html = _run_llm(CARD_SYSTEM_PROMPT, prompt)
    html = _embed_card_images(html, output_dir)
    cache.write_text(html, encoding="utf-8")
    logging.info(f"学习卡片已生成: {cache}")
    return cache
