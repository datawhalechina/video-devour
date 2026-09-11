# backend/algorithm/outline_handler.py
import logging
import re
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import config

def save_outline(outline, output_dir=None):
    """
    保存初始 Markdown 大纲到文件
    
    文件名：outline.md（保存在指定的输出目录下）
    
    Args:
        outline (str): 大纲的 Markdown 内容
        output_dir (str, optional): 输出目录路径。如果未提供，使用默认输出目录
        
    Returns:
        str: 保存的文件路径
    """
    # 确定输出目录
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    # 构建文件路径
    outline_filename = "outline.md"
    outline_path = os.path.join(output_dir, outline_filename)
    
    logging.info(f"--- 步骤 3: 正在将大纲保存到 {outline_path} ---")
    try:
        with open(outline_path, 'w', encoding='utf-8') as f:
            f.write(outline)
        logging.info("--- 大纲保存成功 ---")
        print(f"处理成功完成！大纲已保存至: {outline_path}")
        return outline_path
    except IOError as e:
        logging.error(f"无法将大纲写入文件 {outline_path}: {e}")
        raise

def parse_headings_from_outline(outline_content):
    """
    从大纲内容中解析所有Markdown标题，并返回其级别和内容。
    
    Args:
        outline_content (str): Markdown 大纲内容。
        
    Returns:
        list[tuple[int, str]]: 一个元组列表，每个元组包含 (级别, 标题文本)。
    """
    logging.info("正在从大纲中解析所有级别的标题...")
    headings_found = re.findall(r"^(#+)\s*(.*)", outline_content, re.MULTILINE)
    headings = [(len(level), title.strip()) for level, title in headings_found]

    if not headings:
        logging.warning("在大纲中未找到任何标题 (#, ##, ...)。")
    else:
        logging.info(f"成功从大綱中提取 {len(headings)} 个标题。")
    return headings

def parse_headings_with_content(outline_content):
    """
    解析大纲，提取每个二级标题及其下面的内容
    
    Args:
        outline_content (str): Markdown 大纲内容
        
    Returns:
        dict: 字典，键为二级标题，值为该标题下的文本内容
    """
    logging.info("正在从大纲中解析二级标题及其内容...")
    
    headings_with_content = {}
    lines = outline_content.split('\n')
    
    current_heading = None
    current_content = []
    
    for line in lines:
        # 检查是否是二级标题
        heading_match = re.match(r'##\s+(.+)', line.strip())
        if heading_match:
            # 保存上一个标题的内容
            if current_heading:
                headings_with_content[current_heading] = '\n'.join(current_content).strip()
            
            # 开始新标题
            current_heading = heading_match.group(1).strip()
            current_content = []
        elif current_heading and line.strip() and not line.strip().startswith('#'):
            # 收集当前标题下的内容（非标题行）
            current_content.append(line.strip())
    
    # 保存最后一个标题的内容
    if current_heading:
        headings_with_content[current_heading] = '\n'.join(current_content).strip()
    
    logging.info(f"成功解析 {len(headings_with_content)} 个二级标题及其内容")
    return headings_with_content

def generate_detailed_outline(outline_content, headings, matched_data, output_dir=None):
    """
    生成并保存包含匹配文本块的详细大纲
    
    文件名：detailed_outline.md（保存在指定的输出目录下）
    
    Args:
        outline_content (str): 原始 Markdown 大纲内容
        headings (list): 标题列表
        matched_data (dict): 标题到匹配文本块的映射字典
        output_dir (str, optional): 输出目录路径。如果未提供，使用默认输出目录
        
    Returns:
        str: 保存的文件路径
    """
    # 确定输出目录
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    # 构建文件路径
    detailed_outline_filename = "detailed_outline.md"
    detailed_outline_path = os.path.join(output_dir, detailed_outline_filename)
    
    logging.info(f"--- 步骤 5: 正在生成详细大纲文件到 {detailed_outline_path} ---")
    try:
        with open(detailed_outline_path, 'w', encoding='utf-8') as f:
            # 遍历原始大纲以保留结构
            for line in outline_content.splitlines():
                f.write(line + '\n')
                match = re.match(r"##\s*(.*)", line)
                if match:
                    heading = match.group(1).strip()
                    if heading in matched_data and matched_data[heading]:
                        f.write('\n> **匹配的文本片段:**\n>\n')
                        for chunk in matched_data[heading]:
                            start_str = f"{int(chunk['start'] // 60):02d}:{int(chunk['start'] % 60):02d}"
                            end_str = f"{int(chunk['end'] // 60):02d}:{int(chunk['end'] % 60):02d}"
                            # 格式化为引用块
                            f.write(f"> - **[{start_str} - {end_str}] {chunk['speaker']}:** {chunk['text']}\n")
                        f.write('\n')
            
        logging.info("--- 详细大纲生成成功 ---")
        print(f"处理成功完成！详细大纲已保存至: {detailed_outline_path}")
        return detailed_outline_path
    except IOError as e:
        logging.error(f"无法将详细大纲写入文件 {detailed_outline_path}: {e}")
        raise

def update_detailed_outline_with_keyframes(detailed_outline_path, keyframes):
    """
    更新详细大纲文件，为每个二级标题添加选定的关键帧图片。

    Args:
        detailed_outline_path (str): 详细大纲文件的路径。
        keyframes (dict): 将二级标题映射到其关键帧相对路径的字典。
    """
    logging.info(f"--- 步骤 10: 正在向详细大纲中添加关键帧链接 ---")
    try:
        with open(detailed_outline_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            new_lines.append(line)
            match = re.match(r"##\s*(.*)", line.strip())
            if match:
                heading = match.group(1).strip()
                if heading in keyframes:
                    # 插入图片链接，确保路径格式正确 (使用 /)
                    image_path = keyframes[heading].replace("\\", "/")
                    image_md = f"\n![关键帧: {heading}]({image_path})\n\n"
                    new_lines.append(image_md)
        
        with open(detailed_outline_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        logging.info(f"成功将 {len(keyframes)} 个关键帧链接添加到详细大纲中。存在：{detailed_outline_path}")

    except FileNotFoundError:
        logging.error(f"详细大纲文件未找到: {detailed_outline_path}")
    except Exception as e:
        logging.error(f"更新详细大纲时出错: {e}", exc_info=True)

_FINAL_REPORT_SYSTEM = (
    "你是一位专业的知识编辑，擅长把视频内容压缩成高信息密度的速读报告。"
    "只输出简体中文报告正文（专有名词保留原文），不要任何解释。"
)

# 精简报告：目标是「3 分钟读完就掌握干货」。事实必须取自大纲中的视频原话
# （「匹配的文本片段」），章节摘要只是结构参考——否则会写成「概括的概括」，
# 通篇正确但没有信息量。
_FINAL_REPORT_PROMPT = """下面是一份视频大纲。每个章节包含：二级标题、关键帧图片链接、
「匹配的文本片段」（视频原话，是唯一的事实来源）、以及一段章节摘要（仅为结构参考，不要照抄）。

请据此写一份**高信息密度的精简报告**，让读者 3 分钟读完就能掌握这个视频的全部干货。

【最重要的要求】
1. 事实只来自「匹配的文本片段」里的原话：所有数字、产品名、方法名、技术机制、结论都必须从原话提取。
   章节摘要段只是告诉你"这节在讲什么"，绝不要基于它写内容——那会写成空泛的复述。
2. 严禁空泛套话。以下这类没有信息量的表达一律不要出现：
   「具有重要意义」「值得关注」「核心原因」「明显差异」「不断优化」「越来越受重视」「是…的关键」「为后续做铺垫」。
   每条要点必须至少含一个具体信息：数字、名称、步骤、机制、对比或明确结论。
3. 不要写"元描述"：禁止用「本节介绍/本节点明/本节展示/本节讲解/本节梳理了/本章讲述了」这类句式开头，
   直接给出该节的结论、机制或事实。读者不需要你告诉他"这一段在讲什么"。
4. 同一信息只说一次，不要在多处重复同义句。

【输出结构（严格遵守）】
# 原有一级标题（原样保留）

> 一句话总结：用不超过 50 字说清这个视频最核心的结论（要有判断，不要"介绍了…"这种罗列）

## 核心结论
- 3-5 条。每条一句话，直接把最重要的结论或数据讲清楚。
- 只读这一段也能抓住要点；不要与后文章节逐字重复。

## 原有二级标题（逐章保留，顺序不变，不得改写或增删）
![原图片链接](原样保留，紧跟标题下方)

用 2-3 句话直接讲清本节的核心结论与机制，带上原话里的数字、名称或机制；
不要用「本节介绍/本节梳理了/本节点明/本节展示/本节讲解」开头，也不要写"为后续做铺垫"。
- 2-4 条要点，每条都是可验证的具体事实（数字、名称、机制、对比、结论）。

## 关键数据与术语
- 整份报告**最多出现一次**，放在全部章节之后，作为速查表。
- 仅当视频出现具体数字、产品名或专业术语时输出，每条格式：`- 名称/数字：一句话说明`
  例：- `150ms`：50 并发压测下创建沙箱的 P99 时延
- 视频没有任何具体数据时，整节不要输出。

【格式】
- 只保留一个一级标题；二级标题只用原有章节标题 + 「核心结论」「关键数据与术语」这两个新增小节，不要其他新标题。
- 不要三级及更深标题；不要代码块；不要加粗（`**`）以外的复杂 Markdown 语法。
- 段落之间空一行；不要出现「首先/然后/接下来/总之」等口语连接词。
- 只输出报告正文，不要输出「以下是报告」之类的说明。
__LEVEL__
大纲内容：
-------------------
__CONTENT__
"""


_DATA_SECTION = "关键数据与术语"


def _inline_outline_images(content, markdown):
    """图片以大纲为准还原：LLM 常改写 alt 文字或漏图，导致关键帧失效。

    按章标题定位大纲中该节的图片，替换报告中该节内的图片行；缺图则补上。
    """
    images = {}          # 章节标题 -> [图片 Markdown]
    current = None
    for line in content.splitlines():
        h2 = re.match(r"^##\s+(.+)$", line)
        img = re.match(r"^\s*(!\[[^\]]*\]\([^)]+\))\s*$", line)
        if h2:
            current = h2.group(1).strip()
        elif img and current:
            images.setdefault(current, []).append(img.group(1))

    out, current, inserted = [], None, set()
    for line in (markdown or "").splitlines():
        h2 = re.match(r"^##\s+(.+)$", line)
        if h2:
            current = h2.group(1).strip()
            out.append(line)
            # 标题后立即补回该节的图片（报告正文里原有的图片行稍后会被丢弃）
            if current in images and current not in inserted:
                out.extend(images[current])
                inserted.add(current)
            continue
        if re.match(r"^\s*!\[", line):
            continue          # 丢弃 LLM 生成/改写的图片行，统一以大纲为准
        out.append(line)

    # 大纲里未被插入的章节（标题被 LLM 改写等），在结尾兜底补图
    for heading, imgs in images.items():
        if heading not in inserted:
            out.extend(imgs)
    return "\n".join(out)


def _consolidate_data_section(markdown):
    """把重复的「关键数据与术语」合并成结尾唯一一节（LLM 有时会输出两次）。"""
    blocks = []          # [(level, header, [body_lines])]；level=0 表示标题前的引言
    cur = [0, "", []]
    for line in (markdown or "").splitlines():
        m = re.match(r"^(#{1,2})\s+(.*)$", line)
        if m:
            blocks.append(cur)
            cur = [len(m.group(1)), m.group(2).strip(), []]
        else:
            cur[2].append(line)
    blocks.append(cur)

    data_items, seen, kept = [], set(), []
    for level, header, body in blocks:
        if level == 2 and _DATA_SECTION in header:
            for line in body:
                item = line.strip()
                if item.startswith(("-", "*")) and item not in seen:
                    seen.add(item)
                    data_items.append(item)
        else:
            kept.append((level, header, body))

    if not data_items:
        return markdown

    while kept and not any(x.strip() for x in kept[-1][2]):
        kept.pop()          # 去掉正文尾部空行，数据小节统一收尾

    out = []
    for level, header, body in kept:
        if level:
            out.append("#" * level + " " + header)
        out.extend(body)
    out.extend(["", f"## {_DATA_SECTION}", ""])
    out.extend(data_items)
    return "\n".join(out).strip() + "\n"


def generate_final_report(detailed_outline_path, output_dir, education_level: str = None):
    """
    使用LLM基于包含关键帧的详细大纲生成最终的图文报告。

    Args:
        detailed_outline_path (str): 带有关键帧链接的详细大纲文件路径。
        output_dir (str): 保存最终报告的目录。
        education_level (str): 学习阶段（小学/初中/高中），为空时不注入。

    Returns:
        str: 最终报告的文件路径，如果失败则返回 None。
    """
    logging.info(f"--- 步骤 11: 开始生成最终的图文报告 ---")
    try:
        with open(detailed_outline_path, 'r', encoding='utf-8') as f:
            content = f.read()

        from backend.algorithm.llm_handler import LLMHandler, get_level_instruction
        llm = LLMHandler(education_level=education_level)

        level_instruction = get_level_instruction(education_level)
        level_block = (f"【学习阶段】{level_instruction}。请据此调整语言深度与表达方式。\n\n"
                       if level_instruction else "")
        prompt = (_FINAL_REPORT_PROMPT
                  .replace("__LEVEL__", level_block)
                  .replace("__CONTENT__", content))
        final_report_content = llm.get_response(
            prompt, system_message=_FINAL_REPORT_SYSTEM)

        # 后处理：删除LLM编造的外链图片（只保留本地相对路径图片），
        # 防止报告中出现 example.com 之类无法加载的占位图
        final_report_content = re.sub(
            r'!\[[^\]]*\]\(https?://[^)]*\)',
            '',
            final_report_content,
        )
        # 关键数据小节去重并统一放到结尾
        final_report_content = _consolidate_data_section(final_report_content)
        # 图片以大纲为准还原（LLM 可能改写 alt 或漏图，导致关键帧失效）
        final_report_content = _inline_outline_images(content, final_report_content)

        final_report_path = os.path.join(output_dir, "final_report.md")
        with open(final_report_path, 'w', encoding='utf-8') as f:
            f.write(final_report_content)
            
        logging.info(f"最终报告已成功生成并保存到: {final_report_path}")
        print(f"最终报告已生成！已保存至: {final_report_path}")
        return final_report_path

    except FileNotFoundError:
        logging.error(f"用于生成最终报告的详细大纲文件未找到: {detailed_outline_path}")
        return None
    except Exception as e:
        logging.error(f"生成最终报告时发生未知错误: {e}", exc_info=True)
        return None

# ---------------------------------------------------------------------------
# 详细报告：章节笔记生成
#
# 单次生成的原文上限（按行/句子边界切分，超长章节分段生成后再合并，
# 而不是把原文截断——原文必须完整呈现）。
NOTES_CHUNK_CHARS = 3500
# 分段笔记生成的并发度；长视频（10 万字级）串行要近 20 分钟，适度并发才能实用。
NOTES_PARALLEL = 3
# 分段数不超过该值时合并成一份连贯笔记；更多段时直接顺序拼接，
# 避免单次合并要吞下数万字、反而成为最慢的一步。
NOTES_MERGE_MAX_SEGMENTS = 3

_DETAIL_NOTES_SYSTEM = (
    "你是专业的学习笔记整理者，擅长把口语化的视频原话整理成结构清晰、信息完整的书面笔记。"
    "只输出简体中文（专有名词保留原文），不要任何解释。"
)

# 仅当原话不是中文时才安排「内容翻译」，中文视频直接跳过这一节。
_TRANSLATION_SECTION = """**内容翻译**
把原话逐句翻译为通顺、准确的书面中文。要求：逐句对应，不省略、不概括、不合并句子，
完整保留原话中的信息、数字与举例。

"""

_DETAIL_NOTES_PROMPT = """你是专业的学习笔记整理者。下面是视频某章节的语音原话（带时间戳，口语化），
请整理成结构化的书面笔记。

严格按以下结构输出，保留小标题文字：

**本段主旨**
用 1-3 句话概括这部分讲了什么。

__TRANSLATION__**结构化解读**
按内容实际组织，用「-」分点解读，尽量覆盖以下维度：
- 核心概念（是什么）
- 原理与机制（为什么、如何运作）
- 关键数据与细节（数字、名称、步骤）
- 结论与价值（带来什么影响）
要点要具体，含方法名、数字或结论；只依据原话，不添加原话没有的信息。

**关键要点**
用「-」列出 4-8 条最重要的要点，供快速复习。

其他要求：
1. 只依据原话内容，不编造；口语中的重复、语气词请忽略。
2. 专有名词、技术术语保留英文原文。
3. 只输出笔记正文，不要输出标题以外的解释文字。
__LEVEL__章节标题：__HEADING__

原话：
---
__RAW__
---
"""

_DETAIL_MERGE_PROMPT = """下面是一段视频原话分段整理出的多份笔记，请合并成一份完整笔记。

要求：
1. 保持原有结构：__STRUCTURE__。
2. __TRANSLATION_MERGE__
3. 「结构化解读」与「关键要点」去重合并，避免重复条目。
4. 只依据给定笔记合并，不添加新内容。
5. 全程简体中文（专有名词保留原文）。
6. 只输出合并后的笔记正文，不要任何解释。

章节标题：__HEADING__

分段笔记：
---
__NOTES__
---
"""

_MINDMAP_SYSTEM = (
    "你是知识可视化专家，只输出一个 Mermaid 代码块，不要任何解释文字。"
)

_MINDMAP_PROMPT = """请根据下面的视频大纲，用 Mermaid 画一张思维导图（mindmap），概括整体内容结构。

要求：
1. 只输出一个 ```mermaid 代码块，代码块第一行必须是 mindmap。
2. 根节点写成 root((主题))；下面用 3-6 个一级分支（对应大纲的二级标题），每个分支下 2-4 个要点。
3. 用缩进表示层级，每层 2 个空格；节点文字精炼，不超过 15 字。
4. 节点文字中禁止出现圆括号、方括号、花括号、引号、冒号、逗号、斜杠等标点，以免破坏 Mermaid 语法。
5. 只使用大纲中真实存在的内容，不要新增观点。
6. 全程简体中文（专有名词保留原文）。

大纲：
---
__OUTLINE__
---
"""


def _split_notes_source(raw, limit=NOTES_CHUNK_CHARS):
    """按行（句子）边界切分原文，避免在句子中间断开。"""
    lines = raw.splitlines()
    pieces, buf, size = [], [], 0
    for line in lines:
        if buf and size + len(line) > limit:
            pieces.append("\n".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        pieces.append("\n".join(buf))
    return pieces or [raw]


def _clean_mermaid(text):
    """提取并校验 Mermaid mindmap 代码块；不合法时返回 None。"""
    match = re.search(r"```mermaid\s*(.*?)```", text, re.S)
    body = (match.group(1) if match else text).strip()
    body = re.sub(r"^```(?:mermaid)?\s*|```$", "", body).strip()
    lines = [line for line in body.splitlines() if line.strip()]
    if not lines or lines[0].strip().lower() != "mindmap":
        return None
    if not any(line.startswith(("  ", "\t")) for line in lines[1:]):
        return None
    return "```mermaid\n" + body + "\n```"


def _is_chinese_dominant(text, sample=6000):
    """判断语音原话是否以中文为主：中文视频跳过「内容翻译」这一节。"""
    chunk = (text or "")[:sample]
    t = re.sub(r"\[\d{2}:\d{2}\]", "", chunk)          # 去时间戳，避免误判
    cjk = sum(1 for ch in t if "\u4e00" <= ch <= "\u9fff")
    latin = sum(1 for ch in t if ch.isascii() and ch.isalpha())
    if cjk + latin == 0:
        return True                                     # 无字母类内容按中文处理（不翻译）
    return cjk / (cjk + latin) >= 0.4


def _generate_chapter_notes(llm, raw, heading, level_instruction, translate=True):
    translation = _TRANSLATION_SECTION if translate else ""
    level = f"4. 学习阶段：{level_instruction}\n" if level_instruction else (
        "4. 直接输出，不要额外说明。\n" if not translate else "")
    prompt = (_DETAIL_NOTES_PROMPT
              .replace("__TRANSLATION__", translation)
              .replace("__LEVEL__", level)
              .replace("__HEADING__", heading)
              .replace("__RAW__", raw))
    return llm.get_response(prompt, system_message=_DETAIL_NOTES_SYSTEM).strip()


def _merge_chapter_notes(llm, partials, heading, translate=True):
    """长章节分段生成的笔记合并为一份，避免原文被截断导致信息丢失。

    段数较多时直接顺序拼接（仍是完整内容），只对少量分段做一次 LLM 合并，
    否则合并调用本身要吞下数万字，会成为整份报告最慢的一步。
    """
    if len(partials) == 1:
        return partials[0]
    if len(partials) > NOTES_MERGE_MAX_SEGMENTS:
        return "\n\n".join(partials)
    joined = "\n\n".join(f"【第 {i + 1} 段笔记】\n{p}" for i, p in enumerate(partials))
    structure = ("**本段主旨** / **内容翻译** / **结构化解读** / **关键要点**" if translate
                 else "**本段主旨** / **结构化解读** / **关键要点**")
    translation_rule = ("「内容翻译」按时间顺序完整拼接，逐句保留，不得省略或压缩任何一段。"
                        if translate else "保留各段「本段主旨」「结构化解读」「关键要点」的内容。")
    prompt = (_DETAIL_MERGE_PROMPT
              .replace("__STRUCTURE__", structure)
              .replace("__TRANSLATION_MERGE__", translation_rule)
              .replace("__HEADING__", heading)
              .replace("__NOTES__", joined))
    return llm.get_response(prompt, system_message=_DETAIL_NOTES_SYSTEM).strip()


def _notes_for_chapter(llm, raw, heading, level_instruction, translate=True):
    """章节笔记：超长章节分段并发生成后合并；长视频据此避免串行等待过久。"""
    pieces = _split_notes_source(raw)
    if len(pieces) == 1:
        return _generate_chapter_notes(llm, pieces[0], heading, level_instruction, translate)
    workers = max(1, min(NOTES_PARALLEL, len(pieces)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        partials = list(pool.map(
            lambda piece: _generate_chapter_notes(llm, piece, heading, level_instruction),
            pieces))
    return _merge_chapter_notes(llm, partials, heading)


def _build_mindmap(llm, outline):
    try:
        out = llm.get_response(_MINDMAP_PROMPT.replace("__OUTLINE__", outline),
                               system_message=_MINDMAP_SYSTEM)
    except Exception as e:
        logging.warning(f"详细报告：思维导图生成失败，跳过: {e}")
        return None
    cleaned = _clean_mermaid(out)
    if not cleaned:
        logging.warning("详细报告：思维导图格式不合法，跳过")
    return cleaned


def generate_detailed_report(detailed_outline_path, output_dir, education_level: str = None,
                             headings_with_level=None, matched_data=None, dialogue=None):
    """
    生成「详细报告」：每个章节给出【视频原文】（真·ASR 字幕，带时间戳）与【整理笔记】对照。

    与其他产物的分工：
    - 图文大纲：目录 + 关键帧（结构速览）
    - 精简报告：LLM 提炼扩写（快速阅读）
    - 详细报告：真原文 + 笔记（对照精读，可按时间戳回看视频）

    原文必须来自 ASR transcript（口语原话），而不是大纲的 LLM 复述——
    大纲是概括文本，用它会得到"概括的概括"，失去对照价值。

    Args:
        detailed_outline_path: 含关键帧链接的详细大纲（用于取每章配图）
        headings_with_level: [(level, heading)]，用于确定二级章节顺序
        matched_data: {heading: [{start, end, text}]}，章节的真实时间范围
        dialogue: ASR 处理后的对话块 [{speaker, text, start, end}]
    """
    logging.info("--- 步骤 12: 开始生成详细报告（视频原文+笔记对照）---")
    try:
        with open(detailed_outline_path, 'r', encoding='utf-8') as f:
            outline_content = f.read()

        # 每章关键帧（从详细大纲解析）
        section_images = {}
        current_h2 = None
        for line in outline_content.splitlines():
            h2 = re.match(r'^##\s+(.+)', line)
            img = re.match(r'^!\[.*?\]\((.*?)\)', line.strip())
            if h2:
                current_h2 = h2.group(1).strip()
            elif img and current_h2 and current_h2 not in section_images:
                section_images[current_h2] = img.group(1)

        # 二级章节顺序（缺参时从大纲解析）
        if headings_with_level:
            level2 = [h for lvl, h in headings_with_level if lvl == 2]
        else:
            level2 = [m.group(1).strip() for m in re.finditer(r'^##\s+(.+)', outline_content, re.MULTILINE)]
        if not level2:
            logging.warning("详细报告：未找到二级章节，跳过")
            return None

        if not dialogue:
            logging.warning("详细报告：缺少 ASR 对话数据，无法生成原文对照")
            return None

        # 每章字幕块：整块归属（align_outline_chunks 已保证每块只属于一章）。
        # 不做按字符比例的边界切割，避免原文被切成半句或丢失内容。
        chapter_chunks = {}
        if matched_data:
            for heading in level2:
                chunks = [c for c in (matched_data.get(heading) or []) if c.get("text")]
                chapter_chunks[heading] = sorted(chunks, key=lambda c: c["start"])
        if not any(chapter_chunks.values()):
            # 对齐结果整体缺失时兜底：整块均分，仍保证每块只出现一次、句子完整
            count, chapters = len(dialogue), len(level2)
            for i, heading in enumerate(level2):
                chapter_chunks[heading] = dialogue[i * count // chapters:(i + 1) * count // chapters]

        def _mmss(sec):
            m, s = int(sec // 60), int(sec % 60)
            return f"{m:02d}:{s:02d}"

        def _raw_of(heading):
            """本章原文：完整输出整块字幕，不截断、不切割。"""
            return "\n".join(f"[{_mmss(c['start'])}] {c['text']}"
                             for c in chapter_chunks.get(heading, []))

        from backend.algorithm.llm_handler import LLMHandler, get_level_instruction
        llm = LLMHandler(education_level=education_level)
        level_instruction = get_level_instruction(education_level) or ""

        # 中文原话无需翻译：跳过「内容翻译」，笔记只保留主旨/解读/要点
        all_text = "\n".join(c.get("text", "") for c in dialogue)
        translate = not _is_chinese_dominant(all_text)
        logging.info(f"详细报告：原话{'非中文，保留「内容翻译」' if translate else '为中文，跳过翻译'}")

        title_match = re.search(r'^#\s+(.+)', outline_content, re.MULTILINE)
        doc_title = title_match.group(1).strip() if title_match else "详细报告"

        parts = [f"# {doc_title}\n",
                 "> 每个章节先给【视频原文】（带时间戳的语音原话，完整不截断），再给【整理笔记】，"
                 "对照精读；时间戳可回看视频对应片段。\n"]

        # 整体思维导图（Mermaid，随报告一起呈现）
        mindmap = _build_mindmap(llm, outline_content)
        if mindmap:
            parts.append("\n## 内容思维导图\n")
            parts.append(mindmap + "\n")

        for heading in level2:
            raw = _raw_of(heading)
            chunks = chapter_chunks.get(heading) or []
            parts.append(f"\n## {heading}\n")
            img = section_images.get(heading)
            if img:
                parts.append(f"![关键帧: {heading}]({img})\n")
            if chunks:
                parts.append(f"*本章对应视频 {_mmss(chunks[0]['start'])} - "
                             f"{_mmss(chunks[-1]['end'])}*\n")
            parts.append("### 视频原文\n")
            parts.append((raw if raw else "（本章无对应语音内容）") + "\n")

            parts.append("### 整理笔记\n")
            if raw:
                try:
                    notes = _notes_for_chapter(llm, raw, heading, level_instruction, translate)
                except Exception as e:
                    logging.error(f"详细报告：章节 '{heading}' 笔记生成失败: {e}")
                    notes = "（笔记生成失败）"
            else:
                notes = "（本章无对应语音内容）"
            parts.append(notes + "\n")

        report_content = "\n".join(parts)
        # 清理 LLM 编造的外链图片
        report_content = re.sub(r'!\[[^\]]*\]\(https?://[^)]*\)', '', report_content)

        out_path = os.path.join(output_dir, "detailed_report.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logging.info(f"详细报告已生成: {out_path}")
        print(f"详细报告已生成！已保存至: {out_path}")
        return out_path
    except Exception as e:
        logging.error(f"生成详细报告失败: {e}", exc_info=True)
        return None
