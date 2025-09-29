# backend/algorithm/outline_handler.py
import logging
import re
import config

def save_outline(outline):
    """
    Saves the initial Markdown outline to a file.
    
    Args:
        outline (str): The Markdown content of the outline.
    """
    logging.info(f"--- 步骤 3: 正在将大纲保存到 {config.OUTLINE_MD_PATH} ---")
    try:
        with open(config.OUTLINE_MD_PATH, 'w', encoding='utf-8') as f:
            f.write(outline)
        logging.info("--- 大纲保存成功 ---")
        print(f"处理成功完成！大纲已保存至: {config.OUTLINE_MD_PATH}")
    except IOError as e:
        logging.error(f"无法将大纲写入文件 {config.OUTLINE_MD_PATH}: {e}")
        raise

def parse_headings_from_outline(outline_content):
    """
    Parses all second-level Markdown headings from the outline content.
    
    Args:
        outline_content (str): The Markdown content of the outline.
        
    Returns:
        list: A list of heading titles.
    """
    logging.info("正在从大纲中解析二级标题...")
    headings = re.findall(r"##\s*(.*)", outline_content)
    if not headings:
        logging.warning("在大纲中未找到二级标题（##）。")
    else:
        logging.info(f"成功从大綱中提取 {len(headings)} 个二级标题。")
    return headings

def generate_detailed_outline(outline_content, headings, matched_data):
    """
    Generates and saves the detailed outline with matched text chunks.
    
    Args:
        outline_content (str): The original Markdown outline content.
        headings (list): The list of heading titles.
        matched_data (dict): A dictionary mapping headings to their matched text chunks.
    """
    logging.info(f"--- 步骤 5: 正在生成详细大纲文件到 {config.DETAILED_OUTLINE_MD_PATH} ---")
    try:
        with open(config.DETAILED_OUTLINE_MD_PATH, 'w', encoding='utf-8') as f:
            # We iterate through the original outline to preserve the structure
            for line in outline_content.splitlines():
                f.write(line + '\\n')
                match = re.match(r"##\s*(.*)", line)
                if match:
                    heading = match.group(1).strip()
                    if heading in matched_data and matched_data[heading]:
                        f.write('\\n> **匹配的文本片段:**\\n>\\n')
                        for chunk in matched_data[heading]:
                            start_str = f"{int(chunk['start'] // 60):02d}:{int(chunk['start'] % 60):02d}"
                            end_str = f"{int(chunk['end'] // 60):02d}:{int(chunk['end'] % 60):02d}"
                            # Format as a blockquote
                            f.write(f"> - **[{start_str} - {end_str}] {chunk['speaker']}:** {chunk['text']}\\n")
                        f.write('\\n')
            
        logging.info("--- 详细大纲生成成功 ---")
        print(f"处理成功完成！详细大纲已保存至: {config.DETAILED_OUTLINE_MD_PATH}")
    except IOError as e:
        logging.error(f"无法将详细大纲写入文件 {config.DETAILED_OUTLINE_MD_PATH}: {e}")
        raise
