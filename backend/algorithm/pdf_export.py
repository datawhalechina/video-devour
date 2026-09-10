# -*- coding: utf-8 -*-
"""把报告 Markdown 渲染为 PDF。

用 reportlab 直接排版（不依赖外部字体文件、浏览器或 pandoc）：
- 中文用内置 CID 字体 STSong-Light，跨平台可用，桌面轻量包也能内嵌；
- 自行解析我们生成的报告结构（标题/段落/列表/引用/代码/表格/图片），
  比通用 HTML 转换更可控，也不会引入额外重依赖；
- Mermaid 思维导图按缩进还原成嵌套要点，PDF 里比原始代码可读。
"""
import io
import logging
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle,
)

CJK_FONT = "STSong-Light"
MONO_FONT = "Courier"
_FONT_READY = False

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X, MARGIN_Y = 2 * cm, 2 * cm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X


def _ensure_fonts():
    global _FONT_READY
    if _FONT_READY:
        return
    pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
    # CID 字体没有独立粗体/斜体，映射到同一字体即可让 <b>/<i> 不报错
    pdfmetrics.registerFontFamily(CJK_FONT, normal=CJK_FONT, bold=CJK_FONT,
                                  italic=CJK_FONT, boldItalic=CJK_FONT)
    _FONT_READY = True


def _styles():
    # alignment 默认即左对齐，不放进 base，便于个别样式覆盖（如居中图注）
    base = dict(fontName=CJK_FONT, wordWrap="CJK")
    return {
        "h1": ParagraphStyle("h1", fontSize=20, leading=28, spaceBefore=6, spaceAfter=12,
                             textColor=colors.HexColor("#1f2a1a"), **base),
        "h2": ParagraphStyle("h2", fontSize=15, leading=22, spaceBefore=16, spaceAfter=8,
                             textColor=colors.HexColor("#2b3d24"), **base),
        "h3": ParagraphStyle("h3", fontSize=13, leading=19, spaceBefore=12, spaceAfter=6,
                             textColor=colors.HexColor("#3a4d32"), **base),
        "h4": ParagraphStyle("h4", fontSize=12, leading=18, spaceBefore=10, spaceAfter=5,
                             textColor=colors.HexColor("#46543f"), **base),
        "body": ParagraphStyle("body", fontSize=10.5, leading=17, spaceAfter=7,
                               textColor=colors.HexColor("#222222"), **base),
        "bullet": ParagraphStyle("bullet", fontSize=10.5, leading=17, spaceAfter=4,
                                 leftIndent=14, bulletIndent=4,
                                 textColor=colors.HexColor("#222222"), **base),
        "quote": ParagraphStyle("quote", fontSize=10, leading=16, spaceAfter=8,
                                leftIndent=12, rightIndent=6, textColor=colors.HexColor("#555f4f"),
                                borderPadding=(4, 0, 4, 6), **base),
        "code": ParagraphStyle("code", fontName=MONO_FONT, fontSize=8.5, leading=12,
                               textColor=colors.HexColor("#2f3b2a"), backColor=colors.HexColor("#f4f6f1"),
                               borderPadding=(6, 6, 6, 6), spaceBefore=4, spaceAfter=8),
        "cell": ParagraphStyle("cell", fontSize=9, leading=13, **base),
        "cellh": ParagraphStyle("cellh", fontSize=9, leading=13,
                                textColor=colors.HexColor("#2b3d24"), **base),
        "caption": ParagraphStyle("caption", fontSize=8.5, leading=12,
                                  textColor=colors.HexColor("#8a9384"), alignment=1, **base),
    }


# 按层级生成缩进样式：CID 字体下 &nbsp;/项目符号字形不可靠，
# 改用 Paragraph 的 leftIndent + bulletText（ASCII 短横/序号）表达缩进与项目符号。
_INDENT_STYLES = {}


def _indent_style(base_style, depth):
    key = (base_style.name, depth)
    if key not in _INDENT_STYLES:
        indent = base_style.leftIndent + depth * 16
        _INDENT_STYLES[key] = ParagraphStyle(
            f"{base_style.name}_{depth}", parent=base_style,
            leftIndent=indent, bulletIndent=max(2, indent - 10),
        )
    return _INDENT_STYLES[key]


# ---------------------------------------------------------------------------
# 行内格式：Markdown -> reportlab 迷你标记
# ---------------------------------------------------------------------------

def _escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _inline(text):
    """把行内 Markdown 转成 reportlab Paragraph 支持的标记。"""
    text = _escape(text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)          # 残留图片取 alt
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`",
                  r'<font face="%s" size="9" backColor="#eef1ea">\1</font>' % MONO_FONT, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#4d6b45">\1</link>', text)
    text = text.replace("~~", "")
    return text


# ---------------------------------------------------------------------------
# Mermaid mindmap -> 嵌套要点（PDF 里比原始代码更可读）
# ---------------------------------------------------------------------------

def _mermaid_to_bullets(body):
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if not lines or not lines[0].strip().lower().startswith("mindmap"):
        return None
    items = []
    for line in lines[1:]:
        depth = len(line) - len(line.lstrip())
        label = line.strip()
        label = re.sub(r"^root\((.*)\)$", r"\1", label)
        label = re.sub(r"^[（(](.*)[）)]$", r"\1", label)
        label = label.strip()
        if label:
            items.append((depth, label))
    return items or None


# ---------------------------------------------------------------------------
# 图片
# ---------------------------------------------------------------------------

def _find_image(src, base_dir, roots):
    src = src.strip().split(" ")[0].strip('"\'')
    if not src or src.startswith(("http://", "https://", "data:")):
        return None
    rel = src.replace("\\", "/").lstrip("./")
    candidates = []
    if base_dir:
        candidates.append(Path(base_dir) / rel)
    for root in roots:
        candidates.append(Path(root) / rel)
    for path in candidates:
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


def _image_flowable(path, styles):
    try:
        from PIL import Image as _PILImage
        with _PILImage.open(path) as im:
            w, h = im.size
    except Exception:
        return None
    if not w or not h:
        return None
    max_w = CONTENT_WIDTH
    max_h = PAGE_HEIGHT - 2 * MARGIN_Y - 4 * cm
    scale = min(max_w / w, max_h / h, 1.0)
    return Image(str(path), width=w * scale, height=h * scale)


# ---------------------------------------------------------------------------
# 块解析
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_HR_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_IMAGE_ONLY_RE = re.compile(r"^\s*!\[[^\]]*\]\(([^)]+)\)\s*$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,3}\.)\s+(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def _split_row(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def _parse_blocks(lines):
    """把 Markdown 切成块：('heading', level, text) / ('para', text) /
    ('list', items) / ('quote', text) / ('code', text, lang) / ('image', src, alt) /
    ('table', rows) / ('hr',)。"""
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fence = re.match(r"^\s*```(\w*)\s*$", line)
        if fence:
            lang = fence.group(1)
            buf = []
            i += 1
            while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", "\n".join(buf), lang))
            continue

        m = _HEADING_RE.match(line)
        if m:
            blocks.append(("heading", len(m.group(1)), m.group(2).strip()))
            i += 1
            continue

        if _HR_RE.match(line):
            blocks.append(("hr",))
            i += 1
            continue

        m = _IMAGE_ONLY_RE.match(line)
        if m:
            alt = re.match(r"^\s*!\[([^\]]*)\]", line).group(1)
            blocks.append(("image", m.group(1), alt))
            i += 1
            continue

        # 表格：当前行含 |，下一行是分隔行
        if "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
            rows = [_split_row(line)]
            i += 2
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append(("table", rows))
            continue

        if line.lstrip().startswith("> "):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip())
                i += 1
            blocks.append(("quote", " ".join(buf)))
            continue

        if _LIST_RE.match(line):
            items = []
            while i < n:
                m = _LIST_RE.match(lines[i])
                if not m:
                    # 列表项内的续行（缩进且非空）
                    if lines[i].strip() and lines[i].startswith(("  ", "\t")) and items:
                        items[-1]["text"] += " " + lines[i].strip()
                        i += 1
                        continue
                    break
                indent, marker, text = len(m.group(1)), m.group(2), m.group(3)
                ordered = marker.endswith(".")
                level = 1 if indent >= 2 else 0
                if items and items[-1]["ordered"] == ordered and items[-1]["level"] == level:
                    items.append({"text": text, "ordered": ordered, "level": level,
                                  "index": len([x for x in items if x["level"] == level]) + 1})
                else:
                    items.append({"text": text, "ordered": ordered, "level": level, "index": 1})
                i += 1
            blocks.append(("list", items))
            continue

        # 段落：累积到空行或下一个块起始
        buf = [line.strip()]
        i += 1
        while i < n and lines[i].strip():
            nxt = lines[i]
            if (_HEADING_RE.match(nxt) or _HR_RE.match(nxt) or nxt.lstrip().startswith("> ")
                    or _LIST_RE.match(nxt) or re.match(r"^\s*```", nxt)
                    or _IMAGE_ONLY_RE.match(nxt)):
                break
            buf.append(nxt.strip())
            i += 1
        blocks.append(("para", " ".join(buf)))
    return blocks


# ---------------------------------------------------------------------------
# 对外入口
# ---------------------------------------------------------------------------

def markdown_to_pdf(md_text, title="", base_dir=None, extra_roots=()):
    """把 Markdown 渲染为 PDF 字节流。title 为空时取正文首个一级标题。"""
    _ensure_fonts()
    styles = _styles()
    story = []

    lines = (md_text or "").replace("\r\n", "\n").split("\n")
    if not title:
        for line in lines:
            m = _HEADING_RE.match(line)
            if m and len(m.group(1)) == 1:
                title = m.group(2).strip()
                break
    title = title or "VideoDevour 报告"

    roots = [Path(r) for r in extra_roots]

    for block in _parse_blocks(lines):
        kind = block[0]
        if kind == "heading":
            _, level, text = block
            story.append(Paragraph(_inline(text), styles.get(f"h{min(level, 4)}", styles["h4"])))
        elif kind == "para":
            story.append(Paragraph(_inline(block[1]), styles["body"]))
        elif kind == "quote":
            story.append(Paragraph(_inline(block[1]), styles["quote"]))
        elif kind == "hr":
            story.append(Spacer(1, 4))
        elif kind == "list":
            for item in block[1]:
                style = _indent_style(styles["bullet"], item["level"])
                bullet = f"{item['index']}." if item["ordered"] else "-"
                story.append(Paragraph(_inline(item["text"]), style, bulletText=bullet))
            story.append(Spacer(1, 3))
        elif kind == "code":
            _, body, lang = block
            is_mermaid = lang == "mermaid" or body.lstrip().lower().startswith("mindmap")
            bullets = _mermaid_to_bullets(body) if is_mermaid else None
            if bullets:
                for depth, label in bullets:
                    style = _indent_style(styles["bullet"], max(0, depth // 2))
                    story.append(Paragraph(_inline(label), style, bulletText="-"))
                story.append(Spacer(1, 4))
            else:
                story.append(Preformatted(body, styles["code"]))
        elif kind == "table":
            rows = block[1]
            if not rows:
                continue
            ncol = max(len(r) for r in rows)
            data = []
            for r_i, row in enumerate(rows):
                style = styles["cellh"] if r_i == 0 else styles["cell"]
                cells = [Paragraph(_inline(c), style) for c in row]
                cells += [Paragraph("", style)] * (ncol - len(cells))
                data.append(cells)
            table = Table(data, colWidths=[CONTENT_WIDTH / ncol] * ncol, repeatRows=1)
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5ddcd")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ea")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(table)
            story.append(Spacer(1, 6))
        elif kind == "image":
            _, src, alt = block
            path = _find_image(src, base_dir, roots)
            flow = _image_flowable(path, styles) if path else None
            if flow is not None:
                story.append(flow)
                if alt:
                    story.append(Paragraph(_inline(alt), styles["caption"]))
                story.append(Spacer(1, 8))
            elif alt:
                story.append(Paragraph(f"[图片] {_inline(alt)}", styles["caption"]))

    if not story:
        story.append(Paragraph(_inline(title), styles["h1"]))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_Y, bottomMargin=MARGIN_Y,
        title=title, author="VideoDevour",
    )

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(CJK_FONT, 8)
        canvas.setFillColor(colors.HexColor("#9aa394"))
        canvas.drawRightString(PAGE_WIDTH - MARGIN_X, MARGIN_Y - 6 * mm, f"第 {doc_.page} 页")
        canvas.restoreState()

    try:
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    except Exception as e:
        logging.error(f"PDF 渲染失败: {e}", exc_info=True)
        raise
    return buf.getvalue()


def safe_pdf_name(title, label=""):
    stem = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9_-]+", "_", (title or "report"))[:60].strip("_") or "report"
    return f"{stem}_{label}.pdf" if label else f"{stem}.pdf"
