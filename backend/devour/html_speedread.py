# -*- coding: utf-8 -*-
"""HTML 速读页：把视频报告渲染成可单文件传播的一页 HTML（speedread.html）。

版式规范遵循 answer-me-with-html（github.com/QingYunA/answer-me-with-html，MIT）：
- 内容稿 = 扩展 Markdown：YAML frontmatter（title/subtitle/cols…）+ `## ` 面板
  + ```组件 围栏块；模型只写内容稿，本模块负责排版、配色与暗色模式。
- sheet 一页速读：现代编辑风主题（圆角卡片 / 柔和阴影 / 语义色）、面板网格、
  面板字母 ID；组件按信息形状选用。
- 实现的组件子集（视频速读够用，复杂图形组件引导用表格/时间线替代）：
  callout / kv / timeline / limits / flow（线性链+扇出）/ tree（缩进列表）/
  Markdown 表格（ok / no / warn 状态徽章）与关键帧图片（base64 内嵌）。

导出：html_export.export_png / export_pdf 用无头 Chrome 截全页长图与 A4 PDF，
供传播（微信/群里直接发图或 PDF）。
"""
import base64
import html as _html
import io
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

# 关键帧内嵌参数：报告原图多为 720p JPEG，直接 base64 会让 HTML 膨胀到数 MB；
# 压到 ≤880px 宽再嵌，单页 6-8 图通常落在 0.6-1.5MB，传播友好且屏显够清晰。
_EMBED_MAX_WIDTH = 880
_EMBED_JPEG_QUALITY = 74

_STATUS_WORDS = {"ok": "✓", "no": "✗", "warn": "!"}


# ---------------------------------------------------------------------------
# LLM 内容稿提示词（版式规范 = answer-me-with-html 的稿件格式子集）
# ---------------------------------------------------------------------------
SPEEDREAD_PROMPT = """你是「一页速读页」的内容编辑。根据下面的视频报告，写一份 HTML 速读页的**内容稿**。
读者打开就是一屏清晰的面板网格，30-60 秒抓住全片。

【稿件格式】（渲染器负责排版配色，你只写内容，绝不写 HTML/CSS）
稿件必须以一行 --- 开始写 frontmatter，再用一行 --- 结束，之后才是导语与面板：
---
title: 页面标题（即视频核心命题，不超过 22 字；纯文本，不要用 ** 加粗）
subtitle: 一句话副标题，不超过 30 字；纯文本，不要用 ** 加粗
cols: 3
source: UP主或讲者 · 平台（报告里有就写，没有就省略此行）
---
导语：一句核心结论（可选，不超过 40 字）。

## A 面板标题
面板正文。每个 `## ` 是一个面板，字母 ID 可省略；标题后可加 {span=2}（跨两列宽）
或 {bare}（无标题栏）。共 4-7 个面板，第一个面板必须给核心结论。

【可用组件】（```围栏块，按信息形状选，不要全用一种）
结论/警示 → ```callout info|ok|warn|err 标题（下一行起写正文）
元信息 → ```kv（每行 `键: 值`，`* 键: 值` 占整行；可 `kv cols=2`）
章节脉络/阶段 → ```timeline v（每行 `时间 | 标题 | 说明`，行首 `*` 高亮该条）
数值与上限 → ```limits（`标签 | 实际值 / 上限 | 单位`，或 `标签 | max 上限`；没有真实数字就不要用）
步骤链路 → ```flow（`A -> B: 标签`，虚线 `A --> B`，判断 `{条件?}`，端点 `(词)`，存储 `[(词)]`，重点 `*词`；只写单条线性链，分支用 `A -> B & C` 扇出，不要画复杂网状）
层级/分类 → ```tree（缩进表达层级，每行 `标签 | 说明`，行首可加 `` `编号` `` 标签）
多维对比 → 普通 Markdown 表格，状态列写 ok / no / warn（可带文字，如 `ok 已验证`）
关键帧配图 → 报告中有 `![...](keyframes/...)` 时，把 Markdown 图片原样放进相关面板（独立成行）

【写作规则（STE 受控写作）】
1. 一句话只说一件事；用主动语态；同一概念全文同名。
2. 句长：列表条目 ≤35 字，说明 ≤45 字；每段不超过 6 句。
3. 不编造：所有事实、数字、名称只能来自报告；报告没有真实数字就不要用 limits。
4. 禁止空泛套话（「值得关注」「赋能」「闭环」等）；保留报告里的具体数字与名称。
5. 面板正文可用 Markdown 段落、列表、加粗；不要用一级/二级标题（## 被面板占用）。
"""


# ---------------------------------------------------------------------------
# 草稿解析：frontmatter + 面板 + 组件围栏
# ---------------------------------------------------------------------------
_FM_VALUE_MD_RE = re.compile(r"(\*\*|__|`)+")


def _fm_value(raw: str) -> str:
    """frontmatter 值清洗：去引号与残留的 Markdown 强调符（标题里不该有 **）。"""
    v = raw.strip().strip('"').strip("'").strip()
    return _FM_VALUE_MD_RE.sub("", v).strip()


def parse_draft(draft: str) -> Dict:
    """
    解析内容稿 → {title, subtitle, cols, meta{...}, intro[md行], panels[...]}。

    面板语法：`## [ID ]标题 {span=N rows=N meta="右上角小字"}` / `{bare}`。
    正文里的 ```name args 围栏块识别为组件；未知组件按代码块渲染（不丢内容）。
    """
    lines = (draft or "").replace("\r\n", "\n").split("\n")

    # frontmatter。LLM 偶发漏写开头的 ---（实测会让整段 title:/cols: 漏进导语），
    # 所以无 --- 时只要首行形如 `键: 值` 也按 frontmatter 解析；
    # 但收到的键里没有 title/subtitle/cols 之一则视为普通正文，不吞内容。
    meta_fm: Dict[str, str] = {}
    idx = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() in ("---", "..."):
                idx = i + 1
                break
            m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", lines[i].strip())
            if m:
                meta_fm[m.group(1).lower()] = _fm_value(m.group(2))
    elif lines and re.match(r"^[A-Za-z_][\w-]*\s*:\s*\S", lines[0].strip()):
        i = 0
        while i < len(lines):
            m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", lines[i].strip())
            if not m:
                break
            meta_fm[m.group(1).lower()] = _fm_value(m.group(2))
            i += 1
        if not any(k in meta_fm for k in ("title", "subtitle", "cols")):
            meta_fm.clear()
        else:
            idx = i

    panels: List[Dict] = []
    intro: List[str] = []
    current: Optional[Dict] = None
    fence: Optional[Dict] = None

    for line in lines[idx:]:
        fence_open = re.match(r"^```([\w-]+)\s*(.*)$", line.strip())
        if fence and line.strip() == "```":
            current["blocks"].append(fence)
            fence = None
            continue
        if fence_open and current is not None:
            fence = {"kind": "component", "name": fence_open.group(1).lower(),
                     "args": fence_open.group(2).strip(), "lines": []}
            continue
        if fence is not None:
            fence["lines"].append(line)
            continue

        panel_m = re.match(r"^##\s+(.*)$", line)
        if panel_m:
            current = _parse_panel_head(panel_m.group(1), len(panels))
            panels.append(current)
            continue
        if current is None:
            intro.append(line)
        else:
            current["md_lines"].append(line)

    # 收尾：未闭合的组件围栏按已有内容收进来
    if fence is not None and current is not None:
        current["blocks"].append(fence)
    for p in panels:
        p["blocks"].insert(0, {"kind": "md", "lines": p.pop("md_lines")})

    intro_text = "\n".join(intro).strip()
    # 草稿约定「导语：一句话」，页面上不应露出这个标签本身
    intro_text = re.sub(r"^导语[:：]\s*", "", intro_text)
    return {
        "title": meta_fm.get("title") or "视频速读",
        "subtitle": meta_fm.get("subtitle", ""),
        "cols": _to_int(meta_fm.get("cols"), default=3, lo=1, hi=6),
        # frontmatter 其余键（source 等）进页头元信息行
        "meta": {k: v for k, v in meta_fm.items()
                 if k not in ("title", "subtitle", "cols", "template", "theme", "lang")},
        "intro": intro_text,
        "panels": panels,
    }


def _parse_panel_head(text: str, seq: int) -> Dict:
    """`A 标题 {span=2 meta=".."}` → 面板结构；ID 可省略（自动分配 A/B/C…）。"""
    attrs = {}
    attr_m = re.search(r"\{(.*)\}\s*$", text)
    if attr_m:
        text = text[:attr_m.start()].strip()
        for kv in re.finditer(r'(\w+)(?:=\s*"([^"]*)"|=\s*([-\w]+)|\b)', attr_m.group(1)):
            key = kv.group(1).lower()
            val = kv.group(2) if kv.group(2) is not None else kv.group(3)
            attrs[key] = val if val not in (None, "") else True

    panel_id = ""
    # 仅「单个大写字母 + 空格 + 标题」视为显式面板 ID（## A 核心结论）；
    # 否则像「CPU 的发展」这类英文开头的标题会被误吃首字母
    id_m = re.match(r"^([A-Z])\s+(\S.*)$", text)
    if id_m:
        panel_id, text = id_m.group(1), id_m.group(2).strip()
    else:
        panel_id = chr(ord("A") + seq % 26)

    return {
        "id": panel_id,
        "title": text.strip(),
        "span": _to_int(attrs.get("span"), default=1, lo=1, hi=6),
        "rows": _to_int(attrs.get("rows"), default=0, lo=0, hi=12),
        "meta": attrs.get("meta") if isinstance(attrs.get("meta"), str) else "",
        "bare": bool(attrs.get("bare")),
        "md_lines": [],
        "blocks": [],
    }


def _to_int(value, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(str(value))))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# 迷你 Markdown（速读页正文子集：段落/列表/表格/引用/图片/行内标记）
# ---------------------------------------------------------------------------
_INLINE_RE = re.compile(
    r"(!\[[^\]]*\]\([^)]+\))"                 # 图片
    r"|(\[[^\]]+\]\([^)]+\))"                 # 链接
    r"|(`[^`]+`)"                             # 行内代码
    r"|(\*\*[^*]+\*\*)"                       # 粗体
    r"|(~~[^~]+~~)"                           # 删除线
    r"|(\*[^*\n]+\*)"                         # 斜体
)


def _inline(text: str, output_dir: Optional[Path] = None) -> str:
    """行内 Markdown → HTML（图片相对路径就地内嵌 base64）。"""
    out, pos = [], 0
    for m in _INLINE_RE.finditer(text):
        out.append(_plain(text[pos:m.start()]))
        token = m.group(0)
        if m.group(1):                                   # 图片
            img_m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", token)
            out.append(_img_tag(img_m.group(2), img_m.group(1), output_dir))
        elif m.group(2):                                 # 链接
            a_m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            href = _plain(a_m.group(2))
            out.append(f'<a href="{href}" target="_blank" rel="noreferrer">{_plain(a_m.group(1))}</a>')
        elif m.group(3):
            out.append(f"<code>{_plain(m.group(3)[1:-1])}</code>")
        elif m.group(4):
            out.append(f"<strong>{_plain(m.group(4)[2:-2])}</strong>")
        elif m.group(5):
            out.append(f"<del>{_plain(m.group(5)[2:-2])}</del>")
        elif m.group(6):
            out.append(f"<em>{_plain(m.group(6)[1:-1])}</em>")
        pos = m.end()
    out.append(_plain(text[pos:]))
    return "".join(out)


def _plain(text: str) -> str:
    return _html.escape(text, quote=False)


def _img_tag(src: str, alt: str, output_dir: Optional[Path]) -> str:
    """图片 → figure；本地 keyframes 路径读自 output_dir，压缩后 base64 内嵌。"""
    data_uri = _embed_image(src, output_dir)
    alt_esc = _html.escape(alt or "", quote=True)
    cls = "am-img"
    if data_uri:
        return (f'<figure class="{cls}"><img src="{data_uri}" alt="{alt_esc}" loading="lazy">'
                + (f"<figcaption>{_plain(alt)}</figcaption>" if alt else "")
                + "</figure>")
    # 原样保留 http(s) 图链；本地缺失的图不渲染（防裂图）
    if src.startswith(("http://", "https://", "data:")):
        return f'<figure class="{cls}"><img src="{_html.escape(src, quote=True)}" alt="{alt_esc}" loading="lazy"></figure>'
    return ""


def _embed_image(src: str, output_dir: Optional[Path]) -> str:
    """本地图片压缩为 JPEG data URI；只认 output_dir 内的相对路径。"""
    if src.startswith(("http://", "https://", "data:")) or output_dir is None:
        return ""
    path = (output_dir / src.replace("\\", "/").lstrip("./")).resolve()
    if not path.exists() or not str(path).startswith(str(output_dir.resolve())):
        return ""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            if im.width > _EMBED_MAX_WIDTH:
                im = im.resize((_EMBED_MAX_WIDTH, round(im.height * _EMBED_MAX_WIDTH / im.width)),
                               Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=_EMBED_JPEG_QUALITY, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as e:
        logging.warning(f"速读页图片内嵌失败（{src}）: {e}")
        return ""


def _md_blocks(lines: List[str], output_dir: Optional[Path] = None) -> str:
    """块级 Markdown → HTML（段落 / 列表 / 表格 / 引用 / 分隔线）。"""
    html_out: List[str] = []
    buf: List[str] = []
    table_rows: List[List[str]] = []
    list_items: List[tuple] = []       # (有序?, 条目html)
    quote_buf: List[str] = []

    def flush_para():
        text = " ".join(s.strip() for s in buf if s.strip())
        if text:
            html_out.append(f"<p>{_inline(text, output_dir)}</p>")
        buf.clear()

    def flush_list():
        if not list_items:
            return
        ordered = list_items[0][0]
        tag = "ol" if ordered else "ul"
        items = "".join(f"<li>{t}</li>" for _, t in list_items)
        html_out.append(f"<{tag}>{items}</{tag}>")
        list_items.clear()

    def flush_table():
        if not table_rows:
            return
        head, body = table_rows[0], table_rows[1:]
        thead = "".join(f"<th>{_inline(c, output_dir)}</th>" for c in head)
        rows = ""
        for r in body:
            if all(re.fullmatch(r"\s*:?-{2,}:?\s*", c) for c in r):   # 分隔行
                continue
            rows += "<tr>" + "".join(f"<td>{_table_cell(c, output_dir)}</td>" for c in r) + "</tr>"
        html_out.append(
            f'<div class="am-table-wrap"><table><thead><tr>{thead}</tr></thead>'
            f"<tbody>{rows}</tbody></table></div>")
        table_rows.clear()

    def flush_quote():
        if quote_buf:
            text = " ".join(s.lstrip("> ").strip() for s in quote_buf if s.strip())
            html_out.append(f"<blockquote>{_inline(text, output_dir)}</blockquote>")
            quote_buf.clear()

    def flush_all():
        flush_para(); flush_list(); flush_table(); flush_quote()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_all()
            continue
        if re.match(r"^\s*>\s?", line):
            flush_para(); flush_list(); flush_table()
            quote_buf.append(line)
            continue
        if quote_buf:
            flush_quote()
        if re.match(r"^\s*(---|\*\*\*|___)\s*$", line):
            flush_all(); html_out.append("<hr>"); continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            flush_para(); flush_list()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            continue
        if table_rows:
            flush_table()
        list_m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if list_m:
            flush_para()
            ordered = list_m.group(2)[0].isdigit()
            list_items.append((ordered, _inline(list_m.group(3), output_dir)))
            continue
        if list_items:
            flush_list()
        heading_m = re.match(r"^#{3,4}\s+(.*)$", line)
        if heading_m:
            flush_para()
            html_out.append(f"<h3>{_inline(heading_m.group(1), output_dir)}</h3>")
            continue
        # 独立成行的图片是块级元素（figure 不能嵌在 <p> 里，浏览器会拆开导致间距错乱）
        if re.match(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$", line):
            flush_para()
            html_out.append(_inline(line.strip(), output_dir))
            continue
        buf.append(line)
    flush_all()
    return "\n".join(html_out)


def _table_cell(cell: str, output_dir: Optional[Path]) -> str:
    """表格单元格：ok/no/warn 状态词 → 徽章（answer-me-with-html 表格约定）。"""
    m = re.fullmatch(r"\s*(ok|no|warn)\s*(.*)", cell, re.IGNORECASE)
    if m and (not m.group(2) or m.group(2).startswith((" ", "·", "—", "-"))):
        kind = m.group(1).lower()
        icon = _STATUS_WORDS[kind]
        rest = m.group(2).strip(" ·—-").strip()
        text = f" {rest}" if rest else ""
        return (f'<span class="am-status am-status--{kind}">'
                f'<span class="am-status-icon">{icon}</span>{_plain(text)}</span>')
    return _inline(cell, output_dir)


# ---------------------------------------------------------------------------
# 组件渲染
# ---------------------------------------------------------------------------
def _render_component(name: str, args: str, lines: List[str], output_dir: Optional[Path]) -> str:
    body = [l for l in lines]
    if name == "callout":
        return _render_callout(args, body, output_dir)
    if name == "kv":
        return _render_kv(args, body)
    if name == "timeline":
        return _render_timeline(args, body)
    if name == "limits":
        return _render_limits(body)
    if name == "flow":
        return _render_flow(body)
    if name == "tree":
        return _render_tree(body)
    # 未知组件：按代码块渲染，内容不丢
    code = _html.escape("\n".join(body).strip())
    return f'<pre class="am-code">{code}</pre>'


def _render_callout(args: str, lines: List[str], output_dir: Optional[Path]) -> str:
    m = re.match(r"^(info|ok|warn|err)\s+(.*)$", args.strip(), re.IGNORECASE)
    kind = m.group(1).lower() if m else "info"
    title = m.group(2).strip() if m else args.strip()
    body = _md_blocks(lines, output_dir)
    title_html = f'<div class="am-callout-title">{_inline(title)}</div>' if title else ""
    return f'<div class="am-callout am-callout--{kind}">{title_html}<div class="am-md">{body}</div></div>'


def _render_kv(args: str, lines: List[str]) -> str:
    cols = 2
    m = re.match(r"^cols\s*=\s*(\d)", args, re.IGNORECASE)
    if m:
        cols = _to_int(m.group(1), default=2, lo=1, hi=4)
    cells = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        wide = line.startswith("*")
        if wide:
            line = line[1:].strip()
        km = re.match(r"^(.+?)\s*[:：]\s*(.+)$", line)
        if not km:
            continue
        cells.append((wide, km.group(1).strip(), km.group(2).strip()))
    if not cells:
        return ""
    cell_html = "".join(
        f'<div class="am-kv-cell{" am-kv-cell--wide" if w else ""}">'
        f"<dt>{_plain(k)}</dt><dd>{_inline(v)}</dd></div>"
        for w, k, v in cells)
    return f'<dl class="am-kv" style="--kv-cols:{cols}">{cell_html}</dl>'


def _render_timeline(args: str, lines: List[str]) -> str:
    vertical = "v" in (args or "").lower().split()
    items = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        hi = line.startswith("*")
        if hi:
            line = line[1:].strip()
        parts = [p.strip() for p in line.split("|")]
        when = parts[0] if parts and parts[0] else ""
        title = parts[1] if len(parts) > 1 else ""
        text = parts[2] if len(parts) > 2 else ""
        items.append((when, title, text, hi))
    if not items:
        return ""
    li = "".join(
        f'<li class="am-tl-item{" am-tl-item--hi" if hi else ""}">'
        f'<span class="am-tl-when">{_plain(w)}</span>'
        f'<span class="am-tl-dot"></span>'
        f'<span class="am-tl-title">{_inline(t)}</span>'
        + (f'<span class="am-tl-text">{_inline(x)}</span>' if x else "")
        + "</li>"
        for w, t, x, hi in items)
    orient = "am-timeline--v" if vertical else "am-timeline--h"
    style = "" if vertical else f' style="--n:{len(items)}"'
    return f'<ul class="am-timeline {orient}"{style}>{li}</ul>'


def _render_limits(lines: List[str]) -> str:
    bars = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        label = parts[0]
        m = re.fullmatch(r"max\s*([\d.]+)\s*(\S*)", parts[1], re.IGNORECASE)
        if m:                                        # 只标上限（当前值未知）
            bars.append((label, None, float(m.group(1)), m.group(2), None))
            continue
        vm = re.fullmatch(r"([\d.]+)\s*/\s*([\d.]+)\s*(\S*)", " ".join(parts[1:]))
        if vm:
            bars.append((label, float(vm.group(1)), float(vm.group(2)),
                         vm.group(3), None))
            continue
        bars.append((label, None, None, None, " ".join(parts[1:]) or None))  # 无数值：仅文字
    if not bars:
        return ""
    out = []
    for label, val, cap, unit, note in bars:
        val_txt = cap_txt = ""
        pct = over = 0
        if val is not None and cap:
            val_txt, cap_txt = _fmt_num(val), _fmt_num(cap)
            pct = min(100.0, val / cap * 100.0) if cap > 0 else 100.0
            over = val > cap
        elif cap is not None:
            cap_txt = _fmt_num(cap)                  # max-only：画满格刻度线
            pct = 0
        right = (f'{val_txt} / {cap_txt} {unit or ""}'.strip()
                 if cap else (note or ""))
        cls = "am-lim is-over" if over else "am-lim"
        bar = (f'<div class="am-lim-track"><div class="am-lim-fill" style="width:{pct:.1f}%"></div>'
               + (f'<div class="am-lim-mark" style="left:100%"></div>' if val is None and cap else "")
               + "</div>") if (cap is not None or note) else ""
        ticks = (f'<div class="am-lim-ticks"><span>0</span><span>{cap_txt}</span></div>'
                 if cap_txt else "")
        out.append(
            f'<div class="{cls}"><div class="am-lim-head">'
            f'<span>{_inline(label)}</span>'
            f'<span class="am-lim-val">{_plain(right)}</span></div>'
            f"{bar}{ticks}</div>")
    return "".join(out)


def _fmt_num(v: float) -> str:
    return f"{v:g}"


def _render_flow(lines: List[str]) -> str:
    """
    线性流程链（CSS 盒+箭头，非 SVG 自动布局）。

    支持：A -> B: 标签 / A --> B 虚线 / A -> B & C 扇出 / {判断?} / (端点) /
    [(存储)] / *重点。复杂拓扑请改用表格或 timeline（提示词已引导）。
    """
    edges: List[Dict] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        dashed = "-->" in line
        m = re.match(r"^(.+?)\s*-+>\s*(.+)$", line)
        if not m:
            edges.append({"from": _flow_node(line), "targets": [], "dashed": False})
            continue
        left, right = m.group(1).strip(), m.group(2).strip()
        label = ""
        lm = re.match(r"^(.*?)\s*:\s*(.+)$", right)
        if lm:
            right, label = lm.group(1).strip(), lm.group(2).strip()
        targets = [_flow_node(t.strip()) for t in right.split("&")]
        edges.append({"from": _flow_node(left), "targets": targets,
                      "label": label, "dashed": dashed})

    # 展开为线性序列：链式 A->B、B->C 不重复中间节点
    seq: List[Dict] = []
    last_label = None

    def push(node, label="", dashed=False):
        nonlocal last_label
        if node["text"] != last_label:
            seq.append({"node": node, "label": label, "dashed": dashed})
            last_label = node["text"]

    for e in edges:
        push(e["from"])
        for i, t in enumerate(e["targets"]):
            push(t, e["label"] if i == 0 else "", e["dashed"])
    if not seq:
        return ""

    parts = []
    for i, item in enumerate(seq):
        if i > 0:
            arrow_cls = "am-fa--dashed" if item["dashed"] else ""
            lbl = (f'<span class="am-fa-label">{_plain(item["label"])}</span>'
                   if item["label"] else "")
            parts.append(f'<span class="am-flow-arrow {arrow_cls}"><span class="am-fa-line"></span>{lbl}</span>')
        n = item["node"]
        parts.append(f'<span class="am-fnode am-fnode--{n["shape"]}{" am-fnode--hi" if n["hi"] else ""}">{_plain(n["text"])}</span>')
    return f'<div class="am-flow">{"".join(parts)}</div>'


def _flow_node(token: str) -> Dict:
    hi = token.startswith("*")
    if hi:
        token = token[1:].strip()
    shape, text = "box", token
    if token.startswith("{") and token.endswith("}"):
        shape, text = "diamond", token[1:-1].rstrip("?？")
    elif token.startswith("((") and token.endswith("))"):
        shape, text = "pill", token[2:-2]
    elif token.startswith("(") and token.endswith(")"):
        shape, text = "pill", token[1:-1]
    elif token.startswith("[(" ) and token.endswith(")]"):
        shape, text = "store", token[2:-2]
    elif token.startswith("[") and token.endswith("]"):
        shape, text = "box", token[1:-1]
    return {"shape": shape, "text": text.strip(), "hi": hi}


def _render_tree(lines: List[str]) -> str:
    """缩进层级树（list 变体）：`标签 | 说明`，行首 `编号` 为标签码。"""
    root = {"tag": "", "label": "", "sub": "", "children": []}
    stack = [(-1, root)]
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else root
        tag, sub = "", ""
        body = content
        tm = re.match(r"^`([^`]+)`\s*(.*)$", body)
        if tm:
            tag, body = tm.group(1), tm.group(2)
        if "|" in body:
            body, sub = body.split("|", 1)
            body, sub = body.strip(), sub.strip()
        node = {"tag": tag, "label": body, "sub": sub, "children": []}
        parent["children"].append(node)
        stack.append((indent, node))

    def render(node) -> str:
        if not node["children"]:
            return ""
        items = []
        for c in node["children"]:
            label = (f'<span class="am-tree-tag">{_plain(c["tag"])}</span>' if c["tag"] else "") \
                    + f'<span class="am-tree-label">{_inline(c["label"])}</span>'
            if c["sub"]:
                label += f'<span class="am-tree-sub">{_inline(c["sub"])}</span>'
            items.append(f"<li>{label}{render(c)}</li>")
        return f'<ul class="am-tree-list">{"".join(items)}</ul>'

    inner = render(root)
    return f'<div class="am-tree">{inner}</div>' if inner else ""


# ---------------------------------------------------------------------------
# 页面组装
# ---------------------------------------------------------------------------
def _shorten_url(url: str) -> str:
    """页头展示用短链：去掉 query/fragment，超长截中间保留首尾可读部分。"""
    m = re.match(r"^(https?://[^/?#]+)([^?#]*)", url.strip())
    if not m:
        return url
    text = (m.group(1) + m.group(2)).rstrip("/")
    if len(text) > 46:
        text = text[:26] + "…" + text[-18:]
    return text


def _meta_chip(k: str, v: str) -> str:
    """页头元信息 → chip；URL 只展示短链（完整地址保留在链接里，避免刷屏）。"""
    if v.startswith(("http://", "https://")):
        href = _html.escape(v, quote=True)
        return (f'<span class="am-chip"><b>{_plain(k)}</b>'
                f'<a href="{href}" target="_blank" rel="noreferrer">'
                f"{_plain(_shorten_url(v))}</a></span>")
    return f'<span class="am-chip"><b>{_plain(k)}</b>{_plain(v)}</span>'


def render_sheet(draft_text: str, output_dir=None, meta: Optional[Dict] = None) -> str:
    """
    内容稿 → 单文件 HTML（图片 base64 内嵌、亮暗双主题、打印分页样式）。

    meta 为任务元信息（platform_label / source_url / generated_at / level），
    与 frontmatter 里的 source 等键合并显示在页头元信息行。
    """
    doc = parse_draft(draft_text)
    out_dir = Path(output_dir) if output_dir else None
    meta = meta or {}

    head_meta: List[tuple] = []
    for k, v in meta.items():
        if v:
            head_meta.append((str(k), str(v)))
    for k, v in doc["meta"].items():
        if v:
            head_meta.append((str(k), str(v)))

    panels_html = []
    panel_seq = 0
    for p in doc["panels"]:
        blocks = []
        for b in p["blocks"]:
            if b["kind"] == "md":
                blocks.append(_md_blocks(b["lines"], out_dir))
            else:
                blocks.append(_render_component(b["name"], b["args"], b["lines"], out_dir))
        body = "\n".join(x for x in blocks if x)
        if not body:
            continue
        # 阅读动线：第一个面板（核心结论）固定全宽，作为导览区；
        # 其余面板按草稿 span 进入细节网格
        if panel_seq == 0:
            cls, style = "am-panel am-panel--lead", "grid-column: 1 / -1;"
        else:
            cls, style = "am-panel", f"grid-column: span {min(p['span'], doc['cols'])};"
        if p["rows"]:
            style += f" grid-row: span {p['rows']};"
        if p["bare"]:
            head_html = ""
        else:
            meta_html = (f'<span class="am-panel-meta">{_plain(p["meta"])}</span>'
                         if p["meta"] else "")
            head_html = (f'<div class="am-panel-head"><span class="am-panel-id">{_plain(p["id"])}</span>'
                         f"<h2>{_inline(p['title'])}</h2>{meta_html}</div>")
        panels_html.append(
            f'<section class="{cls}" style="{style}">{head_html}'
            f'<div class="am-panel-body am-md">{body}</div></section>')
        panel_seq += 1

    intro_html = (f'<p class="am-intro">{_inline(doc["intro"])}</p>'
                  if doc["intro"] else "")
    subtitle_html = (f'<p class="am-sub">{_inline(doc["subtitle"])}</p>'
                     if doc["subtitle"] else "")
    meta_html = "".join(_meta_chip(k, v) for k, v in head_meta)
    ruler = "".join("<span></span>" for _ in range(doc["cols"]))

    return _PAGE_TEMPLATE.format(
        title=_html.escape(doc["title"], quote=True),
        title_text=_plain(doc["title"]),
        subtitle=subtitle_html,
        intro=intro_html,
        meta=meta_html,
        cols=doc["cols"],
        panels="\n".join(panels_html),
        ruler_top=ruler,
        ruler_bottom=ruler,
        css=_SHEET_CSS,
    )


_SHEET_CSS = """
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace;
  --radius: 14px; --radius-sm: 10px;
  --shadow: 0 1px 2px rgba(15,23,42,.05), 0 10px 28px -16px rgba(15,23,42,.16);
  --shadow-hover: 0 2px 4px rgba(15,23,42,.06), 0 18px 40px -18px rgba(15,23,42,.22);
}
html[data-mode="light"], html:not([data-mode]) {
  --bg: #eef4ee; --paper: #ffffff; --ink: #16261b; --ink-2: #47604f; --ink-3: #66796b;
  --line: #dce8de; --line-2: #e9f1ea; --fill: #f2f6f3; --zebra: #f0f7f1;
  --accent: #1d7a46; --accent-bg: #e9f4ec; --accent-soft: #bfe3cb;
  --ok: #1d7a46; --ok-bg: #e9f4ec;
  --err: #c64848; --err-bg: #faecec;
  --warn: #a9680a; --warn-bg: #fbf3e4;
  --head-bg: #e9f4ec; --head-fg: #1d7a46;
}
html[data-mode="dark"] {
  --bg: #0c1410; --paper: #131f18; --ink: #e6efe8; --ink-2: #a3b8aa; --ink-3: #6f8377;
  --line: #24352b; --line-2: #1d2c23; --fill: #182720; --zebra: #17251d;
  --accent: #6fcf97; --accent-bg: #173324; --accent-soft: #2c4d38;
  --ok: #6fcf97; --ok-bg: #173324;
  --err: #ff8f8f; --err-bg: #3d2020;
  --warn: #f2b95c; --warn-bg: #3a2c10;
  --head-bg: #173324; --head-fg: #6fcf97;
}
@media (prefers-color-scheme: dark) {
  html[data-mode="auto"] { --bg:#0c1410; --paper:#131f18; --ink:#e6efe8; --ink-2:#a3b8aa;
    --ink-3:#6f8377; --line:#24352b; --line-2:#1d2c23; --fill:#182720; --zebra:#17251d;
    --accent:#6fcf97; --accent-bg:#173324; --accent-soft:#2c4d38;
    --ok:#6fcf97; --ok-bg:#173324; --err:#ff8f8f; --err-bg:#3d2020;
    --warn:#f2b95c; --warn-bg:#3a2c10; --head-bg:#173324; --head-fg:#6fcf97; }
}
body { background: var(--bg); color: var(--ink); font-family: var(--font-sans);
  font-size: 14px; line-height: 1.6; -webkit-font-smoothing: antialiased; }
::selection { background: var(--accent-soft); }
code, pre, kbd { font-family: var(--font-mono); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ---- 悬浮工具栏（亮暗切换） ---- */
.am-toolbar { position: fixed; top: 14px; right: 14px; z-index: 10; }
.am-btn { display: inline-flex; align-items: center; gap: 6px;
  font: 500 12px/1 var(--font-sans); color: var(--ink-2); background: var(--paper);
  border: 1px solid var(--line); border-radius: 999px; padding: 8px 14px; cursor: pointer;
  box-shadow: var(--shadow); transition: color .2s ease, border-color .2s ease; }
.am-btn:hover { color: var(--accent); border-color: var(--accent-soft); }
.am-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.am-btn .am-ico { display: inline-block; vertical-align: middle; }
.am-btn .am-ico--sun, .am-btn .am-t-dark { display: none; }
.am-btn.is-dark .am-ico--sun { display: inline-block; }
.am-btn.is-dark .am-ico--moon { display: none; }
.am-btn.is-dark .am-t-dark { display: inline; }
.am-btn.is-dark .am-t-light { display: none; }

/* ---- 页面骨架 ---- */
.am-sheet { max-width: 1560px; margin: 0 auto; padding: 42px 32px 48px; }
.am-frame { position: relative; }
.am-ruler { display: none; }

/* ---- 页头 ---- */
.am-head { margin: 0 0 26px; padding: 0 4px; }
.am-overline { margin: 0 0 10px; font: 600 11px/1 var(--font-mono);
  letter-spacing: .16em; text-transform: uppercase; color: var(--accent); }
.am-head h1 { margin: 0; font-size: 27px; line-height: 1.28; font-weight: 700;
  letter-spacing: -.015em; }
.am-sub { margin: 8px 0 0; color: var(--ink-2); font-size: 15px; line-height: 1.55; }
.am-head-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.am-chip { display: inline-flex; align-items: center; gap: 7px; padding: 4px 11px;
  background: var(--paper); border: 1px solid var(--line); border-radius: 999px;
  font-size: 12px; color: var(--ink-2); box-shadow: 0 1px 2px rgba(15,23,42,.04); }
.am-chip b { font-weight: 500; font-size: 11px; color: var(--ink-3); }
.am-chip a { color: var(--ink-2); }
.am-chip a:hover { color: var(--accent); }
.am-intro { margin: 16px 0 0; max-width: 80ch; padding: 10px 14px; font-size: 14.5px;
  line-height: 1.65; color: var(--ink); background: var(--accent-bg);
  border-left: 3px solid var(--accent); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }

/* ---- 面板网格 ---- */
.am-grid { display: grid; grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr));
  gap: 18px; align-items: start; }
@media (max-width: 900px) {
  .am-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 620px) {
  .am-sheet { padding: 24px 14px 32px; }
  .am-grid { grid-template-columns: 1fr; }
  .am-grid > section { grid-column: 1 / -1 !important; }
}

.am-panel { background: var(--paper); border: 1px solid var(--line);
  border-radius: var(--radius); box-shadow: var(--shadow); min-width: 0; overflow: hidden;
  transition: box-shadow .18s ease; }
.am-panel:hover { box-shadow: var(--shadow-hover); }
/* 阅读动线：首面板（核心结论）= 全宽导览区，绿色渐变底 + 实心徽章 */
.am-panel--lead { background: linear-gradient(135deg, var(--accent-bg) 0%, var(--paper) 62%);
  border-color: var(--accent-soft); border-top: 3px solid var(--accent);
  margin-bottom: 8px; }
.am-panel--lead .am-panel-head { padding: 14px 18px 12px;
  border-bottom-color: var(--accent-soft); }
.am-panel--lead .am-panel-id { background: var(--accent); color: #fff; }
.am-panel--lead .am-panel-head h2 { font-size: 16.5px; }
.am-panel--lead .am-panel-body { padding: 16px 20px 18px; }
.am-panel-head { display: flex; align-items: center; gap: 10px;
  padding: 12px 16px 11px; border-bottom: 1px solid var(--line-2); }
.am-panel-id { display: inline-flex; align-items: center; justify-content: center;
  flex: none; min-width: 24px; height: 24px; padding: 0 7px; border-radius: 7px;
  background: var(--head-bg); color: var(--head-fg); font: 600 12px/1 var(--font-mono); }
.am-panel-head h2 { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: -.01em;
  flex: 1; display: flex; align-items: center; min-width: 0; }
.am-panel-meta { flex: none; font: 11px/1.4 var(--font-mono); color: var(--ink-3);
  text-align: right; white-space: nowrap; }
.am-panel-body { padding: 15px 17px 17px; }
.am-panel-body > * + * { margin-top: 12px; }

/* ---- 正文排版 ---- */
.am-md > :first-child { margin-top: 0; } .am-md > :last-child { margin-bottom: 0; }
.am-md p { margin: 0 0 9px; }
.am-md ul, .am-md ol { margin: 0 0 9px; padding-left: 20px; }
.am-md li + li { margin-top: 3px; }
.am-md li::marker { color: var(--accent); }
.am-md h3 { margin: 14px 0 6px; font-size: 13px; font-weight: 600; }
.am-md h3::before { content: ""; display: inline-block; width: 4px; height: 12px;
  margin-right: 7px; border-radius: 2px; background: var(--accent-soft);
  vertical-align: -1px; }
.am-panel--lead .am-md > p:first-child { font-size: 15px; }
.am-md blockquote { margin: 0 0 9px; padding: 8px 12px; color: var(--ink-2);
  border-left: 3px solid var(--accent-soft); background: var(--fill);
  border-radius: 0 8px 8px 0; }
.am-md :not(pre) > code { font-size: .9em; background: var(--fill);
  border: 1px solid var(--line-2); padding: 1px 5px; border-radius: 5px; }
.am-md hr { border: 0; border-top: 1px solid var(--line); margin: 14px 0; }
.am-table-wrap { overflow-x: auto; border: 1px solid var(--line);
  border-radius: var(--radius-sm); }
.am-md table { width: 100%; border-collapse: collapse; font-size: 13px; }
.am-md th { text-align: left; font-size: 11px; font-weight: 600; letter-spacing: .04em;
  color: var(--ink-2); padding: 8px 12px; background: var(--fill);
  border-bottom: 1px solid var(--line); }
.am-md td { padding: 8px 12px; border-bottom: 1px solid var(--line-2); vertical-align: top; }
.am-md tbody tr:last-child td { border-bottom: none; }
.am-md tbody tr:nth-child(even) td { background: var(--zebra); }
.am-code { margin: 0; padding: 12px 14px; background: var(--fill);
  border: 1px solid var(--line-2); border-radius: var(--radius-sm);
  overflow-x: auto; font-size: 12.5px; line-height: 1.55; white-space: pre-wrap; }

/* ---- 图片 ---- */
.am-img { margin: 6px 0; }
.am-img img { max-width: 100%; height: auto; display: block; border-radius: var(--radius-sm);
  border: 1px solid var(--line); box-shadow: 0 8px 20px -12px rgba(15,23,42,.28); }
.am-img figcaption { font-size: 12px; color: var(--ink-3); margin-top: 7px; }

/* ---- 状态徽章（表格 ok/no/warn） ---- */
.am-status { display: inline-flex; align-items: center; gap: 4px; padding: 2px 9px;
  border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.am-status--ok { color: var(--ok); background: var(--ok-bg); }
.am-status--no { color: var(--err); background: var(--err-bg); }
.am-status--warn { color: var(--warn); background: var(--warn-bg); }
.am-status-icon { font-weight: 700; }

/* ---- callout ---- */
.am-callout { position: relative; border: 1px solid var(--line); background: var(--accent-bg);
  padding: 11px 14px 12px 17px; border-radius: var(--radius-sm); }
.am-callout::before { content: ""; position: absolute; left: 0; top: 10px; bottom: 10px;
  width: 3px; border-radius: 3px; background: var(--accent); }
.am-callout--ok { background: var(--ok-bg); } .am-callout--ok::before { background: var(--ok); }
.am-callout--warn { background: var(--warn-bg); } .am-callout--warn::before { background: var(--warn); }
.am-callout--err { background: var(--err-bg); } .am-callout--err::before { background: var(--err); }
.am-callout-title { font-weight: 600; font-size: 13.5px; margin-bottom: 4px; }
.am-callout .am-md > :last-child { margin-bottom: 0; }

/* ---- kv 键值卡 ---- */
.am-kv { display: grid; grid-template-columns: repeat(var(--kv-cols, 2), minmax(0, 1fr));
  gap: 8px; margin: 0; }
.am-kv-cell { background: var(--fill); border: 1px solid var(--line-2);
  border-radius: var(--radius-sm); padding: 9px 12px 10px; min-width: 0; }
.am-kv-cell--wide { grid-column: 1 / -1; }
.am-kv dt { font-size: 10.5px; font-weight: 500; letter-spacing: .06em; color: var(--ink-3); }
.am-kv dd { margin: 3px 0 0; font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.am-kv-cell--wide dd { font-size: 16.5px; }

/* ---- timeline ---- */
.am-timeline { list-style: none; margin: 0; padding: 0; }
.am-timeline--h { display: grid; grid-template-columns: repeat(var(--n, 1), minmax(0, 1fr));
  padding-top: 4px; }
.am-timeline--h li { position: relative; text-align: center; padding: 0 6px; }
.am-timeline--h li::before { content: ""; position: absolute; top: 31px; left: 0; right: 0;
  border-top: 2px solid var(--line); }
.am-timeline--h li:first-child::before { left: 50%; }
.am-timeline--h li:last-child::before { right: 50%; }
.am-tl-when { display: block; font-size: 14px; font-weight: 600; height: 24px; }
.am-timeline--v .am-tl-when { display: inline-block; height: auto; font: 500 11px/1.6
  var(--font-mono); color: var(--accent); background: var(--accent-bg);
  padding: 1px 7px; border-radius: 6px; margin-right: 8px; }
.am-tl-dot { position: relative; display: block; width: 11px; height: 11px;
  margin: 2px auto 8px; border: 2px solid var(--accent); border-radius: 50%;
  background: var(--paper); }
.am-tl-item--hi .am-tl-dot { background: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-bg); }
.am-tl-title { display: block; font-size: 12.5px; font-weight: 600; }
.am-timeline--v .am-tl-title { display: inline; font-size: 14px; }
.am-tl-item--hi .am-tl-title { color: var(--accent); }
.am-tl-text { display: block; font-size: 12px; color: var(--ink-2); line-height: 1.5; }
.am-timeline--v li { position: relative; padding: 0 0 14px 24px; }
.am-timeline--v li::before { content: ""; position: absolute; left: 5px; top: 8px;
  bottom: -6px; border-left: 2px solid var(--line); }
.am-timeline--v li:last-child::before { display: none; }
.am-timeline--v .am-tl-dot { position: absolute; left: 1px; top: 4px; margin: 0; }
.am-timeline--v .am-tl-text { margin-top: 3px; }

/* ---- limits 量程条 ---- */
.am-lim + .am-lim { margin-top: 14px; }
.am-lim-head { display: flex; justify-content: space-between; gap: 12px;
  font-size: 13px; margin-bottom: 5px; }
.am-lim-val { font: 600 12px var(--font-mono); color: var(--accent); white-space: nowrap; }
.am-lim-track { position: relative; height: 10px; border: 1px solid var(--line-2);
  background: var(--fill); border-radius: 999px; }
.am-lim-fill { position: absolute; left: 0; top: 0; bottom: 0;
  background: linear-gradient(90deg, var(--accent-soft), var(--accent));
  border-radius: 999px; }
.am-lim-mark { position: absolute; top: -4px; bottom: -4px; border-left: 2px solid var(--accent); }
.am-lim.is-over .am-lim-fill { background: var(--err); }
.am-lim.is-over .am-lim-val { color: var(--err); }
.am-lim-ticks { position: relative; height: 16px; font: 10px/16px var(--font-mono);
  color: var(--ink-3); display: flex; justify-content: space-between; }

/* ---- flow 流程链 ---- */
.am-flow { display: flex; align-items: center; flex-wrap: wrap; gap: 10px 0; }
.am-fnode { position: relative; border: 1px solid var(--line); background: var(--paper);
  padding: 6px 13px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500;
  text-align: center; }
.am-fnode--pill { border-radius: 999px; }
.am-fnode--diamond { background: var(--fill); border-style: dashed; }
.am-fnode--diamond::before { content: "? "; color: var(--accent); font-weight: 700; }
.am-fnode--store::after { content: ""; position: absolute; inset: 3px;
  border: 1px solid var(--line); border-radius: 7px; pointer-events: none; }
.am-fnode--hi { background: var(--accent); border-color: var(--accent); color: var(--paper);
  font-weight: 600; }
.am-fnode--hi::after { display: none; }
.am-flow-arrow { display: inline-flex; flex-direction: column; align-items: center;
  padding: 0 7px; min-width: 36px; color: var(--ink-3); }
.am-fa-line { position: relative; width: 100%; min-width: 26px; height: 2px;
  background: var(--ink-3); }
.am-fa-line::after { content: ""; position: absolute; right: -1px; top: -4px;
  border: 5px solid transparent; border-left: 7px solid var(--ink-3); }
.am-flow-arrow.am-fa--dashed .am-fa-line {
  background: repeating-linear-gradient(90deg, var(--ink-3) 0 5px, transparent 5px 9px); }
.am-fa-label { font-size: 11px; color: var(--ink-3); margin-top: 3px; white-space: nowrap; }

/* ---- tree 层级 ---- */
.am-tree { font-size: 13px; }
.am-tree-list, .am-tree-list ul { list-style: none; margin: 0; padding: 0; }
.am-tree-list ul { margin-left: 16px; }
.am-tree-list li { position: relative; padding: 3px 0 3px 18px; }
.am-tree-list li::before { content: ""; position: absolute; left: 0; top: .95em;
  width: 12px; border-top: 1px solid var(--ink-3); }
.am-tree-list li::after { content: ""; position: absolute; left: 0; top: 0; bottom: 0;
  border-left: 1px solid var(--ink-3); }
.am-tree-list li:last-child::after { bottom: auto; height: .95em; }
.am-tree-tag { font: 500 10.5px/1.7 var(--font-mono); color: var(--ink-3);
  background: var(--fill); border: 1px solid var(--line-2); border-radius: 5px;
  padding: 1px 6px; margin-right: 6px; }
.am-tree-sub { display: block; font-size: 11.5px; color: var(--ink-2); }

/* ---- 页脚 ---- */
.am-foot { margin-top: 28px; padding-top: 14px; border-top: 1px solid var(--line);
  display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  font: 11px/1.5 var(--font-mono); color: var(--ink-3); }

body.am-export .am-toolbar { display: none; }
@media (prefers-reduced-motion: reduce) {
  .am-panel, .am-btn { transition: none; }
}
@page { size: A4; margin: 10mm; }
@media print {
  .am-toolbar { display: none; }
  .am-sheet { padding: 0; max-width: none; }
  .am-frame { border: none; padding: 0; }
  .am-frame::before, .am-ruler { display: none; }
  .am-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .am-panel { break-inside: avoid; page-break-inside: avoid; box-shadow: none; }
  .am-panel--lead { background: #fff; border-color: #bbb; }
  body { background: #fff; }
}
"""

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" data-mode="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="am-toolbar">
  <button class="am-btn" id="am-theme-btn" aria-label="切换深浅色主题"
    onclick="var h=document.documentElement;h.dataset.mode=h.dataset.mode==='dark'?'light':'dark';document.getElementById('am-theme-btn').classList.toggle('is-dark',h.dataset.mode==='dark')">
    <svg class="am-ico am-ico--moon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
    <svg class="am-ico am-ico--sun" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4"/></svg>
    <span class="am-t-light">深色</span><span class="am-t-dark">浅色</span>
  </button>
</div>
<div class="am-sheet">
  <header class="am-head">
    <p class="am-overline">VideoDevour \u00b7 \u4e00\u9875\u901f\u8bfb</p>
    <h1>{title_text}</h1>
    {subtitle}{intro}{meta}
  </header>
  <div class="am-frame">
    <div class="am-ruler am-ruler--top">{ruler_top}</div>
    <div class="am-ruler am-ruler--bottom">{ruler_bottom}</div>
    <div class="am-grid" style="--cols:{cols}">
{panels}
    </div>
  </div>
  <footer class="am-foot">
    <span>VideoDevour \u00b7 HTML \u901f\u8bfb\u9875</span>
    <span>\u7248\u5f0f\u89c4\u8303 answer-me-with-html (MIT)</span>
  </footer>
</div>
</body>
</html>"""
