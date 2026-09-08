# backend/algorithm/outline_handler.py
import logging
import re
import os
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

        from llm_handler import LLMHandler, get_level_instruction
        llm = LLMHandler(education_level=education_level)

        prompt = (
            "你是一位专业的报告撰写员。请根据下面的 Markdown 大纲（含章节标题、文本摘要与关键帧图片），"
            "扩写成一份**结构清晰、可直接阅读**的图文报告。\\n\\n"
            "【必须保留】\\n"
            "1. 完整保留原有的一级（`#`）与二级（`##`）标题文字，不要新增、删除或改写标题。\\n"
            "2. 完整保留大纲中所有图片及其原始 Markdown 链接格式，且每张图片紧跟在所属二级标题下方。\\n"
            "3. 禁止编造图片：只能用大纲中真实存在的链接，绝不添加或替换成外部占位地址"
            "（如 example.com）；大纲无图时报告中也不出现图片。\\n\\n"
            "【结构与排版规范】\\n"
            "1. 每个二级章节的正文按「总—分」展开：先写 2-4 句连贯的引言段落概括本节要点，"
            "再按需用 `-` 列出 2-5 条关键要点（要点须具体，含数字、方法名或结论）。\\n"
            "2. 段落之间空一行；不要在一段里堆砌过多信息，单段不超过 5 行。\\n"
            "3. 不要使用三级及更深标题；不要出现「首先/然后/接下来/总之」等口语连接词。\\n"
            "4. 不要使用加粗（`**`）以外的复杂 Markdown 语法；不要输出代码块标记。\\n"
            "5. 全程简体中文（专有名词、技术术语保留原文）。\\n"
            "6. 只输出报告正文，不要输出「以下是报告」之类的说明文字。\\n\\n"
        )
        level_instruction = get_level_instruction(education_level)
        if level_instruction:
            prompt += f"【学习阶段】{level_instruction}。请根据学习阶段调整报告的语言深度与表达方式。\\n\\n"
        prompt += (
            "原始大纲内容如下：\\n"
            "-------------------\\n"
            f"{content}"
        )
        
        final_report_content = llm.get_response(prompt)

        # 后处理：删除LLM编造的外链图片（只保留本地相对路径图片），
        # 防止报告中出现 example.com 之类无法加载的占位图
        final_report_content = re.sub(
            r'!\[[^\]]*\]\(https?://[^)]*\)',
            '',
            final_report_content,
        )

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

        # 每章时间范围：优先 matched_data 的真实范围；否则按章节顺序均分
        if not dialogue:
            logging.warning("详细报告：缺少 ASR 对话数据，无法生成原文对照")
            return None
        total_start = min(c["start"] for c in dialogue)
        total_end = max(c["end"] for c in dialogue)
        ranges = {}
        for heading in level2:
            chunks = (matched_data or {}).get(heading) or []
            if chunks:
                ranges[heading] = (min(c["start"] for c in chunks), max(c["end"] for c in chunks))
        missing = [h for h in level2 if h not in ranges]
        if missing:
            # 均分兜底：未匹配章节按顺序瓜分剩余/全部时间轴
            span = total_end - total_start
            step = span / len(level2)
            for i, h in enumerate(level2):
                if h not in ranges:
                    ranges[h] = (total_start + step * i, total_start + step * (i + 1))

        def _mmss(sec):
            m, s = int(sec // 60), int(sec % 60)
            return f"{m:02d}:{s:02d}"

        def _raw_of(heading):
            lo, hi = ranges[heading]
            lines = []
            for c in dialogue:
                if c["end"] <= lo or c["start"] >= hi:
                    continue  # 与本章无交叠
                text = c["text"]
                if not text:
                    continue
                span = c["end"] - c["start"]
                if c["start"] >= lo - 0.01 and c["end"] <= hi + 0.01:
                    # 完全落在本章范围内：整句输出
                    lines.append(f"[{_mmss(c['start'])}] {text}")
                elif span > 0:
                    # 跨越章节边界的句子（如整段一长句的短视频）：
                    # 按字符占比切出本章片段，时间戳线性近似，避免每章重复全文
                    f0 = max(0.0, (lo - c["start"]) / span)
                    f1 = min(1.0, (hi - c["start"]) / span)
                    seg = text[int(len(text) * f0):int(len(text) * f1)].strip()
                    if seg:
                        lines.append(f"[{_mmss(c['start'] + span * f0)}] {seg}")
            if not lines:  # 仍为空时取最近邻，避免空章节
                nearest = min(dialogue, key=lambda c: min(abs(c["start"] - lo), abs(c["start"] - hi)))
                lines = [f"[{_mmss(nearest['start'])}] {nearest['text']}"]
            return "\n".join(lines)

        from llm_handler import LLMHandler, get_level_instruction
        llm = LLMHandler(education_level=education_level)
        level_instruction = get_level_instruction(education_level) or ""

        title_match = re.search(r'^#\s+(.+)', outline_content, re.MULTILINE)
        doc_title = title_match.group(1).strip() if title_match else "详细报告"

        parts = [f"# {doc_title}\n",
                 "> 每个章节先给【视频原文】（带时间戳的语音原话），再给【整理笔记】，对照精读；"
                 "时间戳可回看视频对应片段。\n"]

        for heading in level2:
            raw = _raw_of(heading)
            # 超长章节截断保护（LLM 上下文与可读性）
            if len(raw) > 6000:
                raw = raw[:6000] + "\n…（本章原文过长，已截取前段）"
            parts.append(f"\n## {heading}\n")
            img = section_images.get(heading)
            if img:
                parts.append(f"![关键帧: {heading}]({img})\n")
            lo, hi = ranges[heading]
            parts.append(f"*本章对应视频 {_mmss(lo)} - {_mmss(hi)}*\n")
            parts.append("### 视频原文\n")
            parts.append(raw + "\n")

            prompt = (
                "你是专业的学习笔记整理者。下面是视频某个章节的语音原话（带时间戳，口语化），"
                "请整理成要点式笔记。\n\n"
                "要求：\n"
                "1. 先用 1-3 句概括这部分讲了什么；\n"
                "2. 再用 `-` 列出 2-6 条关键要点（保留具体方法、数字、结论）；\n"
                "3. 只依据原话内容，不添加没有的信息；口语中的重复、语气词请忽略；\n"
                "4. 使用简体中文（专有名词保留原文）；\n"
                "5. 只输出笔记正文，不要标题、不要解释。\n"
                + (f"6. 学习阶段：{level_instruction}\n" if level_instruction else "")
                + f"\n章节标题：{heading}\n\n原话：\n---\n{raw}\n---\n"
            )
            try:
                notes = llm.get_response(
                    prompt,
                    system_message="你是专业的学习笔记整理者，只输出简体中文要点笔记。",
                ).strip()
            except Exception as e:
                logging.error(f"详细报告：章节 '{heading}' 笔记生成失败: {e}")
                notes = "（笔记生成失败）"
            parts.append("### 整理笔记\n")
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
