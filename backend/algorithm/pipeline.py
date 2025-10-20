# -*- coding: utf-8 -*-
"""
This module contains the core pipeline logic for processing videos.
"""
import logging
import os
import json
from datetime import datetime

# Local imports from the project
from backend.devour.asr_engine_paraformer_v2 import VideoDevourASRParaformerV2
from backend.algorithm.data_processor import ASRProcessor
from backend.algorithm.llm_handler import LLMHandler
from backend.algorithm.text_similarity_matcher import TextSimilarityMatcher
import backend.algorithm.outline_handler as outline_handler
import backend.algorithm.video_handler as video_handler
import backend.algorithm.image_processor as image_processor
import backend.algorithm.config as config

def _setup_environment(video_path: str):
    """Initializes directories and logging for a new pipeline run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    main_output_folder = f"frames_{video_name}_{timestamp}"
    main_output_path = os.path.join(config.OUTPUT_DIR, main_output_folder)
    os.makedirs(main_output_path, exist_ok=True)

    # Configure logging
    log_file_path = os.path.join(main_output_path, 'processing.log')
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    logging.info(f"="*60)
    logging.info(f"开始处理流程 - 时间戳: {timestamp}")
    logging.info(f"视频文件: {video_path}")
    logging.info(f"输出目录: {main_output_path}")
    logging.info(f"="*60)
    
    return main_output_path, video_name, timestamp

def _run_asr_and_process(video_path: str, video_name: str, main_output_path: str, asr_engine=None):
    """Runs ASR on the video and processes the result."""
    logging.info("--- 步骤 0 & 1: 语音识别与数据处理 ---")
    if asr_engine is None:
        asr_engine = VideoDevourASRParaformerV2()
    asr_result = asr_engine.devour_video(video_path)
    asr_result_path = os.path.join(main_output_path, f"{video_name}_asr_result.json")
    with open(asr_result_path, 'w', encoding='utf-8') as f:
        json.dump([asr_result], f, ensure_ascii=False, indent=2)
    logging.info(f"ASR结果已保存到: {asr_result_path}")
    
    processor = ASRProcessor(asr_result_path)
    processed_dialogue = processor.process()
    if not processed_dialogue:
        logging.warning("处理后的对话为空。")
    logging.info("--- ASR数据处理完成 ---")
    return processed_dialogue

def _generate_and_match_outline(processed_dialogue: list, main_output_path: str):
    """Generates an outline and matches dialogue chunks to its headings."""
    logging.info("--- 步骤 2, 3, 4: 生成大纲并匹配文本块 ---")
    llm = LLMHandler()
    outline = llm.get_outline(processed_dialogue)
    outline_handler.save_outline(outline, output_dir=main_output_path)
    
    headings_with_level = outline_handler.parse_headings_from_outline(outline)
    if not headings_with_level:
        logging.warning("在大纲中未找到标题，跳过匹配。")
        return None, None, None, None
    
    headings = [title for level, title in headings_with_level]
    headings_with_content = outline_handler.parse_headings_with_content(outline)
    
    matcher = TextSimilarityMatcher(similarity_threshold=0.90, use_semantic=True)
    matcher.initialize_headings(headings_with_content)
    
    matched_data = {heading: [] for heading in headings}
    last_matched_heading_index = -1
    for i, chunk in enumerate(processed_dialogue):
        candidate_headings = headings[last_matched_heading_index + 1:]
        if not candidate_headings:
            if last_matched_heading_index != -1:
                last_matched_heading = headings[last_matched_heading_index]
                remaining_chunks = processed_dialogue[i:]
                matched_data[last_matched_heading].extend(remaining_chunks)
                logging.info(f"将 {len(remaining_chunks)} 个剩余文本块附加到 '{last_matched_heading}'")
            else:
                logging.warning("没有候选标题，也没有先前匹配的标题。")
            break
        
        matched_heading, similarity, used_fallback = matcher.match_chunk_with_fallback(
            chunk['text'], candidate_headings,
            fallback_heading=headings[last_matched_heading_index] if last_matched_heading_index != -1 else headings[0]
        )
        
        if matched_heading and matched_heading in headings and not used_fallback:
            last_matched_heading_index = headings.index(matched_heading)
            matched_data[matched_heading].append(chunk)
        else:
            if last_matched_heading_index != -1:
                previous_heading = headings[last_matched_heading_index]
                matched_data[previous_heading].append(chunk)
            elif headings:
                first_heading = headings[0]
                matched_data[first_heading].append(chunk)
    
    logging.info("--- 文本块匹配完成 ---")
    return matched_data, headings_with_level, headings, outline

def run_full_pipeline(video_path: str, asr_engine=None):
    """Orchestrates the full video processing pipeline."""
    try:
        main_output_path, video_name, timestamp = _setup_environment(video_path)
        
        processed_dialogue = _run_asr_and_process(video_path, video_name, main_output_path, asr_engine)
        if not processed_dialogue:
            raise ValueError("ASR处理后对话为空，流程中止。")

        matched_data, headings_with_level, headings, outline = _generate_and_match_outline(
            processed_dialogue, main_output_path
        )
        if not matched_data:
            raise ValueError("文本块与大纲匹配失败，流程中止。")
            
        logging.info("--- 步骤 5: 生成详细大纲 ---")
        detailed_outline_path = outline_handler.generate_detailed_outline(
            outline, headings, matched_data, output_dir=main_output_path
        )

        logging.info("--- 步骤 6: 根据大纲切分视频 ---")
        videocut_path = video_handler.cut_videos_by_headings(
            headings_with_level, matched_data, video_path, output_dir=main_output_path
        )

        if videocut_path:
            logging.info("--- 步骤 7: 从视频片段中提取帧 ---")
            video_handler.extract_frames_from_videos(
                videocut_path=videocut_path, output_dir=main_output_path
            )

        logging.info("--- 步骤 8: 处理并筛选帧 ---")
        image_processor.process_all_frames(output_dir=main_output_path)
        
        logging.info("--- 步骤 9: 使用VLM选择关键帧 ---")
        selected_keyframes = image_processor.select_keyframes_with_vlm(
            headings_with_level, main_output_path
        )

        if selected_keyframes:
            logging.info("--- 步骤 10: 更新大纲，添加关键帧 ---")
            outline_handler.update_detailed_outline_with_keyframes(
                detailed_outline_path, selected_keyframes
            )

        logging.info("--- 步骤 11: 生成最终报告 ---")
        outline_handler.generate_final_report(detailed_outline_path, main_output_path)
        
        logging.info(f"\n" + "="*60)
        logging.info(f"处理流程成功完成 - 时间戳: {timestamp}")
        logging.info(f"="*60)

    except Exception as e:
        logging.error(f"处理流程中发生错误: {e}", exc_info=True)
        print(f"处理失败，发生未知错误: {e}")
