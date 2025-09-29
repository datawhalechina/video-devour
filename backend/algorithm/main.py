# -*- coding: utf-8 -*-
"""
Main entry point for the video processing pipeline.
"""
import logging
import config
from data_processor import ASRProcessor
from llm_handler import LLMHandler
import outline_handler
import video_handler
import image_processor

def main():
    """
    Executes the full pipeline from data loading to keyframe extraction.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        # Step 1: Process the raw ASR data
        logging.info("--- 步骤 1: 开始处理ASR数据 ---")
        processor = ASRProcessor(config.ASR_RESULT_PATH)
        processed_dialogue = processor.process()
        logging.info("--- ASR数据处理完成 ---")

        # Step 2: Generate Markdown outline using LLM
        logging.info("--- 步骤 2: 开始生成LLM大纲 ---")
        llm = LLMHandler()
        outline = llm.get_outline(processed_dialogue)
        logging.info("--- LLM大纲生成完成 ---")

        # Step 3: Save the initial outline
        outline_handler.save_outline(outline)

        # Step 4: Match dialogue chunks to outline headings
        logging.info("--- 步骤 4: 正在将文本块与大纲标题进行匹配 ---")
        headings = outline_handler.parse_headings_from_outline(outline)
        if not headings:
            logging.warning("在大纲中未找到标题，流程提前结束。")
            return

        matched_data = {heading: [] for heading in headings}
        unmatched_chunks = []
        last_matched_heading_index = -1

        total_chunks = len(processed_dialogue)
        for i, chunk in enumerate(processed_dialogue):
            logging.info(f"正在处理块 {i+1}/{total_chunks}...")
            candidate_headings = headings[last_matched_heading_index + 1:]
            
            if not candidate_headings:
                logging.warning(f"块 {i+1} 及之后的所有块没有候选标题可匹配，将它们标记为未匹配。")
                unmatched_chunks.extend(processed_dialogue[i:])
                break

            matched_heading = llm.match_chunk_to_headings(chunk, candidate_headings)
            
            try:
                newly_matched_index = headings.index(matched_heading)
                last_matched_heading_index = newly_matched_index
                matched_data[matched_heading].append(chunk)
                logging.info(f"块 {i+1} 成功匹配到标题: '{matched_heading}'")
            except ValueError:
                logging.error(f"LLM返回的标题 '{matched_heading}' 不在原始标题列表中。将此块添加到未匹配列表。")
                unmatched_chunks.append(chunk)

        if unmatched_chunks and last_matched_heading_index != -1:
            last_matched_heading = headings[last_matched_heading_index]
            logging.info(f"将 {len(unmatched_chunks)} 个未匹配的块附加到最后一个匹配的标题下: '{last_matched_heading}'")
            matched_data[last_matched_heading].extend(unmatched_chunks)
            unmatched_chunks.clear()

        # Step 5: Generate the detailed outline file
        outline_handler.generate_detailed_outline(outline, headings, matched_data)

        # Step 6: Cut video based on headings
        video_handler.cut_videos_by_headings(headings, matched_data)

        # Step 7: Extract frames from video clips
        video_handler.extract_frames_from_videos()

        # Step 8: Process and filter frames to get keyframes
        image_processor.process_all_frames()

    except FileNotFoundError:
        logging.error(f"关键错误：输入文件 {config.ASR_RESULT_PATH} 未找到。请检查文件路径配置。")
        print(f"处理失败。错误：输入文件 {config.ASR_RESULT_PATH} 未找到。")
    except Exception as e:
        logging.error(f"处理流程中发生未知错误: {e}", exc_info=True)
        print(f"处理失败，发生未知错误: {e}")

if __name__ == '__main__':
    main()
