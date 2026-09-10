# -*- coding: utf-8 -*-
"""按需生成的衍生文体：量子速读 / 公众号文章 / 小红书笔记。

这些不是分析报告，而是「以视频内容为素材的成稿」——共同点是把已有报告
转成特定风格的成品文案，因此统一基于信息密度最高的精简报告（final_report.md）
改写，并复用报告里的关键帧图片。生成结果落盘缓存，随文档库一起展示与下载。
"""
import logging
import re
from pathlib import Path

from backend.algorithm.llm_handler import LLMHandler

# scope -> (文件名, 中文名, 是否图文)
STYLE_TYPES = {
    "quantum": ("quantum_read.md", "量子速读", False),
    "wechat": ("wechat_article.md", "公众号文章", True),
    "xiaohongshu": ("xiaohongshu_article.md", "小红书笔记", True),
}

_BASE_FILES = ("final_report.md", "detailed_outline.md")

_STYLE_SYSTEM = (
    "你是资深中文内容编辑，擅长把知识内容改写成特定平台的成品文案。"
    "只输出简体中文成品正文（专有名词保留原文），不要任何解释。"
)

# 共用的取材约束：事实必须来自给定报告，禁止编造与空泛套话
_FACT_RULES = """【取材约束】
1. 所有事实、数字、名称、结论只能来自下面的报告，不要编造、不要补充报告以外的信息。
2. 禁止空泛套话：「具有重要意义」「值得关注」「显而易见」「不言而喻」「值得深思」等一律不要。
3. 报告里有具体数字、产品名、机制时，尽量保留其具体性。
4. 只输出成品正文，不要输出「以下是」之类的说明。

报告如下：
-------------------
__REPORT__
"""

QUANTUM_PROMPT = """你是擅长把长内容压成"一眼看懂"卡片的内容编辑。
请根据下面的视频报告，写一份「量子速读」：读者 30 秒读完就能抓住全片大意，
并且其中有一句可以直接复制发朋友圈。

严格按以下结构输出：

# __TITLE__

> 一句话大意：不超过 40 字，讲清这个视频最核心的判断（要有观点，不要"介绍了…"）

## 三个核心洞察
- 3 条，每条不超过 40 字，必须含具体信息（数字、名称、机制或结论）。

## 发朋友圈的一句话
一句不超过 50 字、可直接复制发布的话：有观点、有信息量、能引发共鸣。
不要鸡汤、不要标题党、不要问句结尾。

""" + _FACT_RULES

WECHAT_PROMPT = """你是资深公众号主笔，擅长把知识类视频写成读者愿意读完的图文文章。
请根据下面的报告，写一篇公众号风格文章。

写作要求：
1. 标题有吸引力但不标题党，不超过 25 字。
2. 开头第一段用一个具体场景、问题或反常识结论钩住读者，素材必须来自报告。
3. 正文分 3-5 个小节，每节用 `## 小标题`，围绕一个要点讲透，2-4 段，口语化但不啰嗦。
4. 每节尽量配一张关键帧图片：若报告中有 `![...](keyframes/...)` 形式的图片，
   把该图片的 Markdown 链接原样保留并放到对应小节下；报告没有图片就不要编造图片。
5. 结尾加一段总结，并用一句有分量的话收束。
6. 不要写"关注我""点赞"之类的引导语。

""" + _FACT_RULES

XIAOHONGSHU_PROMPT = """你是小红书爆款笔记作者。请根据下面的报告，写一篇小红书图文笔记。

写作要求：
1. 第一行是标题：`# ` 开头，不超过 20 字，带 1-2 个贴合内容的 emoji，要有钩子但不夸张。
2. 正文用第一人称、口语化、短句，多换行；每段不要超过 2 行。
3. 用 emoji 分点（如 ✨ / 🔧 / 💡），每点 1-3 行，讲清一个具体信息；共 4-6 点。
4. 关键帧图片：若报告中有 `![...](keyframes/...)`，把图片 Markdown 链接原样保留、
   穿插在相关小节之间；报告没有图片就不要编造。
5. 结尾一句总结，然后另起一行放 4-6 个话题标签，格式如 `#AI工具 #云沙箱`。
   标签内绝对不能有空格：英文专有名词也要连写（写 #AIAgent、#KubeSandbox，
   不要写 #AI Agent）。标签要贴内容，不要堆无关热词。

""" + _FACT_RULES


_PROMPTS = {"quantum": QUANTUM_PROMPT, "wechat": WECHAT_PROMPT,
            "xiaohongshu": XIAOHONGSHU_PROMPT}


def _read_base_report(output_dir) -> str:
    """取信息密度最高的报告作为改写素材。"""
    for name in _BASE_FILES:
        path = Path(output_dir) / name
        if path.exists() and path.stat().st_size > 0:
            return path.read_text(encoding="utf-8")
    raise ValueError("任务还没有可改写的报告")


def _doc_title(report: str, fallback: str = "视频速读") -> str:
    m = re.search(r"^#\s+(.+)$", report, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def _keep_only_report_images(report: str, result: str) -> str:
    """成品里的图片必须是报告真实存在的，防止编造关键帧链接。"""
    allowed = set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", report))
    if not allowed:
        return re.sub(r"!\[[^\]]*\]\([^)]*\)\n?", "", result)

    def _replace(match):
        return match.group(0) if match.group(2) in allowed else ""

    return re.sub(r"(!\[[^\]]*\]\(([^)]+)\))\n?", _replace, result)


def generate_style(output_dir, scope: str, education_level: str = None) -> Path:
    """生成指定文体的成品文案并落盘；已存在则直接复用（缓存）。"""
    if scope not in STYLE_TYPES:
        raise ValueError(f"不支持的文体: {scope}")
    filename, label, _ = STYLE_TYPES[scope]
    out_path = Path(output_dir) / filename
    if out_path.exists() and out_path.stat().st_size > 0:
        return out_path

    report = _read_base_report(output_dir)
    title = _doc_title(report)
    prompt = (_PROMPTS[scope]
              .replace("__TITLE__", title)
              .replace("__REPORT__", report))

    llm = LLMHandler(education_level=education_level)
    content = llm.get_response(prompt, system_message=_STYLE_SYSTEM).strip()
    content = re.sub(r"^```(?:markdown|md)?\s*|```$", "", content, flags=re.MULTILINE).strip()
    content = _keep_only_report_images(report, content)
    if not content:
        raise ValueError(f"{label}生成结果为空")

    out_path.write_text(content, encoding="utf-8")
    logging.info(f"{label}已生成: {out_path}")
    return out_path
