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

def generate_detailed_report(detailed_outline_path, output_dir, education_level: str = None):
    """
    生成「详细报告」：每个章节同时呈现【原始内容】与【整理笔记】，便于对照学习。

    与另外两个产物的区别：
    - 图文大纲（detailed_outline.md）：标题 + 关键帧 + 原始片段（溯源用）
    - 精简报告（final_report.md）：标题 + 关键帧 + LLM 提炼要点（快速阅读）
    - 详细报告（detailed_report.md）：原始片段 + 提炼笔记 对照（精读用）

    Args:
        detailed_outline_path (str): 含关键帧与原始片段的详细大纲路径
        output_dir (str): 输出目录
        education_level (str): 学习阶段

    Returns:
        str: 详细报告文件路径；失败返回 None
    """
    logging.info("--- 步骤 12: 开始生成详细报告（原文+笔记对照）---")
    try:
        with open(detailed_outline_path, 'r', encoding='utf-8') as f:
            outline_content = f.read()

        # 解析出每个二级章节的：标题、关键帧、原始片段
        sections = []
        current = None
        for line in outline_content.splitlines():
            h1 = re.match(r'^#\s+(.+)', line)
            h2 = re.match(r'^##\s+(.+)', line)
            img = re.match(r'^!\[.*?\]\((.*?)\)', line.strip())
            if h2:
                if current:
                    sections.append(current)
                current = {"heading": h2.group(1).strip(), "image": None, "raw": []}
            elif img and current:
                current["image"] = img.group(1)
            elif current is not None:
                # 收集原始片段（引用块 / 正文）
                stripped = line.strip()
                if stripped and not h1:
                    current["raw"].append(stripped)
        if current:
            sections.append(current)

        if not sections:
            logging.warning("详细报告：未解析到任何章节，跳过")
            return None

        # 逐章节调用 LLM 生成「笔记」（基于该章节的原始内容，避免全文重复调用）
        from llm_handler import LLMHandler, get_level_instruction
        llm = LLMHandler(education_level=education_level)
        level_instruction = get_level_instruction(education_level) or ""

        parts = []
        title_match = re.search(r'^#\s+(.+)', outline_content, re.MULTILINE)
        doc_title = title_match.group(1).strip() if title_match else "详细报告"
        parts.append(f"# {doc_title}\n")
        parts.append("> 本报告每个章节同时给出【原始内容】与【整理笔记】，便于对照精读。\n")

        for idx, sec in enumerate(sections, 1):
            parts.append(f"\n## {sec['heading']}\n")
            if sec.get("image"):
                parts.append(f"![关键帧: {sec['heading']}]({sec['image']})\n")
            # 原始内容
            raw_text = "\n".join(sec["raw"]).strip()
            if raw_text:
                parts.append("### 原始内容\n")
                parts.append(raw_text + "\n")
            # 整理笔记
            prompt = (
                "你是专业的学习笔记整理者。请把下面这段视频字幕内容整理成要点式笔记。\n\n"
                "要求：\n"
                "1. 先用 1-3 句概括这段话讲了什么；\n"
                "2. 再用 `-` 列出 2-6 条关键要点（含具体方法、数字或结论）；\n"
                "3. 只依据给定内容，不添加原文没有的信息；\n"
                "4. 使用简体中文（专有名词保留原文）；\n"
                "5. 只输出笔记正文，不要输出标题、不要解释。\n"
                + (f"6. 学习阶段：{level_instruction}\n" if level_instruction else "")
                + f"\n章节标题：{sec['heading']}\n\n内容：\n---\n{raw_text or sec['heading']}\n---\n"
            )
            try:
                notes = llm.get_response(
                    prompt,
                    system_message="你是专业的学习笔记整理者，只输出简体中文要点笔记。",
                ).strip()
            except Exception as e:
                logging.error(f"详细报告：章节 '{sec['heading']}' 笔记生成失败: {e}")
                notes = "（笔记生成失败）"
            parts.append("### 整理笔记\n")
            parts.append(notes + "\n")

        report_content = "\n".join(parts)

        # 清理 LLM 编造的外链图片（与最终报告一致）
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
