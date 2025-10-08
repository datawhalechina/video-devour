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

def generate_final_report(detailed_outline_path, output_dir):
    """
    使用LLM基于包含关键帧的详细大纲生成最终的图文报告。

    Args:
        detailed_outline_path (str): 带有关键帧链接的详细大纲文件路径。
        output_dir (str): 保存最终报告的目录。
    
    Returns:
        str: 最终报告的文件路径，如果失败则返回 None。
    """
    logging.info(f"--- 步骤 11: 开始生成最终的图文报告 ---")
    try:
        with open(detailed_outline_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        from llm_handler import LLMHandler
        llm = LLMHandler()
        
        prompt = (
            "你是一位专业的报告撰写员。你的任务是根据下面提供的Markdown大纲（其中包含了章节标题、文本摘要和关键帧图片），将其优化和扩写成一份内容更丰富、图文并茂的综合性报告。\\n\\n"
            "**重要指令：**\\n"
            "1. **保留原始结构：** 必须完整保留所有原始的一级和二级标题（`#` 和 `##`）。\\n"
            "2. **保留所有图片：** 必须保留大纲中提供的所有图片，并且维持它们原来的Markdown链接格式 (`![...](...)`)。\\n"
            "3. **维持图片位置：** 确保每张图片都紧跟在它所属的二级标题下方，作为该章节的配图。\\n"
            "4. **润色和扩写：** 在保留上述结构和图片的基础上，对每个章节下的文本内容进行语言润色、逻辑梳理和内容补充，使其更加流畅、专业和易于理解。\\n"
            "5. **输出格式：** 最终输出仍为完整的Markdown格式文档。\\n\\n"
            "原始大纲内容如下：\\n"
            "-------------------\\n"
            f"{content}"
        )
        
        final_report_content = llm.get_response(prompt)
        
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
