# -*- coding: utf-8 -*-
"""
Main entry point for the video processing pipeline.
"""
import logging
import os
from datetime import datetime
import config
from data_processor import ASRProcessor
from llm_handler import LLMHandler
from text_similarity_matcher import TextSimilarityMatcher
import outline_handler
import video_handler
import image_processor

def main():
    """
    执行完整的流程：从数据加载到关键帧提取
    
    所有输出文件组织在统一的大文件夹下：
    frames_视频名_时间戳/
        ├── outline.md
        ├── detailed_outline.md
        ├── videocut/
        └── frames_XX/
    """
    try:
        # 生成本次运行的时间戳（格式：YYYYMMDD_HHMMSS）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 从输入视频路径提取视频名（不含扩展名）
        video_name = os.path.splitext(os.path.basename(config.INPUT_VIDEO_PATH))[0]
        
        # 创建大文件夹：frames_视频名_时间戳
        main_output_folder = f"frames_{video_name}_{timestamp}"
        main_output_path = os.path.join(config.OUTPUT_DIR, main_output_folder)
        os.makedirs(main_output_path, exist_ok=True)

        # --- 配置日志记录 ---
        log_file_path = os.path.join(main_output_path, 'processing.log')
        
        # 获取根记录器并移除现有处理器
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 设置日志级别
        logger.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # 文件处理器：写入到 processing.log
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 控制台处理器：输出到屏幕
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
        logging.info(f"="*60)
        logging.info(f"开始处理流程 - 时间戳: {timestamp}")
        logging.info(f"视频文件: {video_name}")
        logging.info(f"输出目录: {main_output_path}")
        logging.info(f"="*60)
        
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

        # Step 3: Save the initial outline (in main output folder)
        outline_path = outline_handler.save_outline(outline, output_dir=main_output_path)

        # Step 4: Match dialogue chunks to outline headings using text similarity
        logging.info("--- 步骤 4: 正在将文本块与大纲标题进行匹配（使用文本重复率检测）---")
        headings = outline_handler.parse_headings_from_outline(outline)
        if not headings:
            logging.warning("在大纲中未找到标题，流程提前结束。")
            return
        
        # 解析大纲，提取每个标题及其内容
        headings_with_content = outline_handler.parse_headings_with_content(outline)
        logging.info(f"解析出 {len(headings_with_content)} 个标题的内容")
        
        # 初始化文本相似度匹配器
        matcher = TextSimilarityMatcher(similarity_threshold=0.90, use_semantic=True)
        matcher.initialize_headings(headings_with_content)

        matched_data = {heading: [] for heading in headings}
        unmatched_chunks = []
        last_matched_heading_index = -1

        total_chunks = len(processed_dialogue)
        for i, chunk in enumerate(processed_dialogue):
            logging.info(f"正在处理块 {i+1}/{total_chunks}...")
            candidate_headings = headings[last_matched_heading_index + 1:]
            
            if not candidate_headings:
                # 没有候选标题了，将当前及之后的块附加到最后一个已匹配的标题下
                if last_matched_heading_index != -1:
                    last_matched_heading = headings[last_matched_heading_index]
                    remaining_chunks = processed_dialogue[i:]
                    matched_data[last_matched_heading].extend(remaining_chunks)
                    logging.info(f"块 {i+1} 及之后的 {len(remaining_chunks)} 个块没有候选标题，已附加到标题 '{last_matched_heading}' 下")
                else:
                    logging.warning(f"块 {i+1} 及之后的所有块没有候选标题可匹配，且没有已匹配的标题。")
                break

            # 使用文本相似度匹配
            chunk_text = chunk['text']
            matched_heading, similarity, used_fallback = matcher.match_chunk_with_fallback(
                chunk_text,
                candidate_headings,
                fallback_heading=headings[last_matched_heading_index] if last_matched_heading_index != -1 else headings[0]
            )
            
            # 检查匹配结果
            if matched_heading and matched_heading in headings and not used_fallback:
                # 文本相似度匹配成功（重复率 >= 90%）
                newly_matched_index = headings.index(matched_heading)
                last_matched_heading_index = newly_matched_index
                matched_data[matched_heading].append(chunk)
                logging.info(f"块 {i+1} 匹配到标题: '{matched_heading}' (相似度: {similarity:.2%})")
            else:
                # 相似度不足，使用回退逻辑
                if last_matched_heading_index != -1:
                    # 如果有上一个匹配的标题，附加到它下面
                    previous_heading = headings[last_matched_heading_index]
                    matched_data[previous_heading].append(chunk)
                    if used_fallback:
                        logging.warning(f"块 {i+1} 相似度不足 ({similarity:.2%} < 90%)，已附加到前一个标题 '{previous_heading}' 下")
                    else:
                        logging.warning(f"块 {i+1} 匹配失败，已附加到前一个标题 '{previous_heading}' 下")
                else:
                    # 如果是第一个块或之前的都未匹配，附加到第一个标题下
                    if headings:
                        first_heading = headings[0]
                        matched_data[first_heading].append(chunk)
                        logging.warning(f"块 {i+1} 匹配失败且无前置标题，已附加到第一个标题 '{first_heading}' 下")
                    else:
                        logging.error(f"块 {i+1} 匹配失败且没有任何可用标题。")
                        unmatched_chunks.append(chunk)

        # Step 5: Generate the detailed outline file (in main output folder)
        detailed_outline_path = outline_handler.generate_detailed_outline(
            outline, headings, matched_data, output_dir=main_output_path
        )

        # Step 6: Cut video based on headings (in main output folder)
        videocut_path = video_handler.cut_videos_by_headings(
            headings, matched_data, output_dir=main_output_path
        )

        # Step 7: Extract frames from video clips (in main output folder)
        if videocut_path:
            frame_dirs = video_handler.extract_frames_from_videos(
                videocut_path=videocut_path, 
                output_dir=main_output_path
            )

        # Step 8: Process and filter frames to get keyframes (in main output folder)
        image_processor.process_all_frames(output_dir=main_output_path)
        
        logging.info(f"\n" + "="*60)
        logging.info(f"处理流程完成 - 时间戳: {timestamp}")
        logging.info(f"="*60)

    except FileNotFoundError:
        logging.error(f"关键错误：输入文件 {config.ASR_RESULT_PATH} 未找到。请检查文件路径配置。")
        print(f"处理失败。错误：输入文件 {config.ASR_RESULT_PATH} 未找到。")
    except Exception as e:
        logging.error(f"处理流程中发生未知错误: {e}", exc_info=True)
        print(f"处理失败，发生未知错误: {e}")

if __name__ == '__main__':
    main()
