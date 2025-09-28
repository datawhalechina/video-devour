# -*- coding: utf-8 -*-
"""
Main entry point for the ASR data processing and outline generation pipeline.

This script orchestrates the entire workflow by coordinating the data processor
and the LLM handler to transform a raw ASR JSON file into a final Markdown
outline.
"""
import logging
import config
from data_processor import ASRProcessor
from llm_handler import LLMHandler

def main():
    """
    Executes the full pipeline from data loading to outline generation.
    """
    # Configure logging for detailed output
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        # Step 1: Process the raw ASR data to get structured, chunked dialogue
        logging.info("--- 步骤 1: 开始处理ASR数据 ---")
        processor = ASRProcessor(config.ASR_RESULT_PATH)
        chunked_dialogue = processor.process()
        logging.info("--- ASR数据处理完成 ---")

        # Step 2: Use the LLM to generate a Markdown outline from the processed data
        logging.info("--- 步骤 2: 开始生成LLM大纲 ---")
        llm_handler = LLMHandler()
        outline = llm_handler.get_outline(chunked_dialogue)
        logging.info("--- LLM大纲生成完成 ---")

        # Step 3: Save the final outline to a Markdown file
        logging.info(f"--- 步骤 3: 正在将大纲保存到 {config.OUTLINE_MD_PATH} ---")
        with open(config.OUTLINE_MD_PATH, 'w', encoding='utf-8') as f:
            f.write(outline)
        logging.info("--- 大纲保存成功 ---")
        print(f"处理成功完成！大纲已保存至: {config.OUTLINE_MD_PATH}")

    except FileNotFoundError:
        logging.error(f"关键错误：输入文件 {config.ASR_RESULT_PATH} 未找到。请检查文件路径配置。")
        print(f"处理失败。错误：输入文件 {config.ASR_RESULT_PATH} 未找到。")
    except Exception as e:
        logging.error(f"处理流程中发生未知错误: {e}", exc_info=True)
        print(f"处理失败，发生未知错误: {e}")

if __name__ == '__main__':
    main()
