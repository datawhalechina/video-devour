# -*- coding: utf-8 -*-
"""
This module contains the core pipeline logic for processing videos.
"""
import logging
import os
import json
from datetime import datetime
from pathlib import Path
from backend.runtime import paths as runtime_paths
from backend.algorithm.chapter_alignment import align_outline_chunks

# Local imports from the project
# settings_store 需最先导入：它负责把 backend/algorithm 加入 sys.path 并引导 config 模块
from backend.algorithm import settings_store
from backend.algorithm.data_processor import ASRProcessor
from backend.algorithm.llm_handler import LLMHandler
import backend.algorithm.outline_handler as outline_handler
import backend.algorithm.video_handler as video_handler
import backend.algorithm.image_processor as image_processor
import backend.algorithm.config as config
from backend.algorithm import timing

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
        # 按运行时设置创建引擎（offline=本地 Paraformer / online=DashScope 云端）
        from backend.devour.asr_factory import create_asr_engine
        asr_engine = create_asr_engine()
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

def _resolve_use_semantic() -> bool:
    """
    解析大纲匹配策略（settings.json 的 outline_match_strategy）。

    - string:   强制字符串匹配，不加载 sentence-transformers/torch（轻量包推荐）
    - semantic: 强制语义匹配（依赖缺失时由 matcher 自行降级）
    - auto:     依赖可用则语义匹配，否则字符串匹配（默认）
    """
    try:
        strategy = settings_store.load_settings().get("outline_match_strategy", "auto")
    except Exception as e:
        logging.warning(f"读取匹配策略失败，回退 auto: {e}")
        strategy = "auto"

    if strategy == "string":
        logging.info("大纲匹配策略: string（纯字符串匹配，不加载本地语义模型）")
        return False
    if strategy == "semantic":
        logging.info("大纲匹配策略: semantic（强制语义匹配）")
        return True

    from backend.algorithm.text_similarity_matcher import is_semantic_available
    use_semantic = is_semantic_available()
    logging.info(f"大纲匹配策略: auto（语义匹配{'可用' if use_semantic else '不可用，回退字符串匹配'}）")
    return use_semantic


def _generate_and_match_outline(processed_dialogue: list, main_output_path: str, education_level: str = None):
    """Generates an outline and matches dialogue chunks to its headings."""
    logging.info("--- 步骤 2, 3, 4: 生成大纲并匹配文本块 ---")
    llm = LLMHandler(education_level=education_level)
    outline = llm.get_outline(processed_dialogue)
    outline_handler.save_outline(outline, output_dir=main_output_path)
    
    headings_with_level = outline_handler.parse_headings_from_outline(outline)
    if not headings_with_level:
        logging.warning("在大纲中未找到标题，跳过匹配。")
        return None, None, None, None
    
    headings = [title for level, title in headings_with_level]
    matched_data = align_outline_chunks(
        outline, processed_dialogue, getattr(llm, "chapter_starts", None)
    )
    return matched_data, headings_with_level, headings, outline

def run_full_pipeline(video_path: str, asr_engine=None, education_level: str = None,
                      progress_callback=None, media_ready_callback=None, managed_source=False):
    """处理前统一轻量视频；回调仅在真实阶段发生时触发。"""
    tracker = None
    main_output_path = None

    def progress(percent, message, stage):
        if progress_callback:
            progress_callback(percent, message, stage)

    try:
        # 应用控制台设置（密钥/模型/ASR模式），education_level 缺省取设置中的默认值
        settings_store.apply_to_config()
        if education_level is None:
            education_level = settings_store.load_settings().get("default_education_level", "高中")
        logging.info(f"本次处理参数: asr_mode={settings_store.load_settings().get('asr_mode')}, "
                     f"education_level={education_level}")

        main_output_path, video_name, timestamp = _setup_environment(video_path)

        # 启动本任务的耗时追踪（落盘到任务输出目录）
        tracker = timing.start_tracking(video_name)

        progress(16, "正在压缩视频（最高 720p / 10 帧）…", "preparing_video")
        with timing.track("步骤0_视频压缩"):
            source = Path(video_path)
            if managed_source:
                # 仅 API 的 uploads 副本可替换。CLI/外部路径始终保留原件。
                if source.resolve().parent != (runtime_paths.data_root() / "uploads").resolve():
                    raise ValueError("只允许替换应用 uploads 目录中的视频副本")
                destination = source.with_suffix('.mp4')
            else:
                destination = Path(main_output_path) / 'processing_video.mp4'
            prepared = video_handler.prepare_video(
                source, destination,
                progress=lambda fraction: progress(
                    16 + int(14 * fraction), f"视频压缩 {int(fraction * 100)}%（720p / 10 帧）",
                    "preparing_video"),
            )
            video_path = prepared['path']
            Path(main_output_path, 'media_profile.json').write_text(
                json.dumps(prepared, ensure_ascii=False, indent=2), encoding='utf-8')
            if media_ready_callback:
                media_ready_callback(prepared)
            if managed_source and source != destination:
                source.unlink()

        progress(30, "正在进行语音识别…", "asr")
        with timing.track("步骤1-2_ASR与数据处理"):
            processed_dialogue = _run_asr_and_process(video_path, video_name, main_output_path, asr_engine)
        if not processed_dialogue:
            raise ValueError("ASR处理后对话为空，流程中止。")

        progress(45, "正在生成大纲并定位章节…", "generating_outline")
        with timing.track("步骤3-4_大纲生成与匹配"):
            matched_data, headings_with_level, headings, outline = _generate_and_match_outline(
                processed_dialogue, main_output_path, education_level
            )
        if not matched_data:
            raise ValueError("文本块与大纲匹配失败，流程中止。")
            
        logging.info("--- 步骤 5: 生成详细大纲 ---")
        with timing.track("步骤5_生成详细大纲"):
            detailed_outline_path = outline_handler.generate_detailed_outline(
                outline, headings, matched_data, output_dir=main_output_path
            )

        progress(60, "正在按章节直接提取画面…", "extracting_frames")
        with timing.track("步骤6-7_章节直接抽帧"):
            video_handler.extract_frames_by_headings(
                headings_with_level, matched_data, video_path, main_output_path,
                duration=prepared['duration'],
                progress=lambda done, total: progress(
                    60 + int(12 * done / total), f"章节抽帧 {done}/{total}", "extracting_frames"),
            )

        logging.info("--- 步骤 8: 处理并筛选帧 ---")
        progress(73, "正在筛选重复画面…", "extracting_frames")
        with timing.track("步骤8_帧去重处理"):
            image_processor.process_all_frames(output_dir=main_output_path)
        
        logging.info("--- 步骤 9: 使用VLM选择关键帧 ---")
        progress(78, "正在选择关键画面…", "vlm_analysis")
        with timing.track("步骤9_VLM关键帧选择"):
            selected_keyframes = image_processor.select_keyframes_with_vlm(
                headings_with_level, main_output_path
            )

        if selected_keyframes:
            logging.info("--- 步骤 10: 更新大纲，添加关键帧 ---")
            with timing.track("步骤10_大纲插入关键帧"):
                outline_handler.update_detailed_outline_with_keyframes(
                    detailed_outline_path, selected_keyframes
                )

        logging.info("--- 步骤 11: 生成最终报告 ---")
        progress(86, "正在生成学习笔记…", "generating_report")
        with timing.track("步骤11_生成最终报告"):
            outline_handler.generate_final_report(detailed_outline_path, main_output_path,
                                                  education_level=education_level)

        logging.info("--- 步骤 12: 生成详细报告（视频原文+笔记对照）---")
        progress(92, "正在生成原文对照报告…", "generating_report")
        with timing.track("步骤12_生成详细报告"):
            outline_handler.generate_detailed_report(
                detailed_outline_path, main_output_path,
                education_level=education_level,
                headings_with_level=headings_with_level,
                matched_data=matched_data,
                dialogue=processed_dialogue,
            )

        
        logging.info(f"\n" + "="*60)
        logging.info(f"处理流程成功完成 - 时间戳: {timestamp}")
        logging.info(f"="*60)

        return {"video_path": video_path, "output_dir": main_output_path, "media_profile": prepared}

    except Exception as e:
        logging.error(f"处理流程中发生错误: {e}", exc_info=True)
        print(f"处理失败，发生未知错误: {e}")
        # 重新抛出：调用方（API/skill）依赖异常区分成败，
        # 吞掉异常会让失败任务被误标为"处理完成"
        raise

    finally:
        if tracker is not None and main_output_path:
            tracker.write_reports(main_output_path)
