# backend/algorithm/video_handler.py
import os
import re
import logging
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import config
from backend.runtime import paths as _rt_paths

# 视频切分/抽帧并发度。
# ffmpeg 本身已多线程（libx264 会用满多核），叠加多个 ffmpeg 进程会指数级抢占 CPU：
# 实测 4 路并发 + 多任务并行把系统 load 打到 80 导致整机卡死。
# 因此按 CPU 核数保守取值：最多 2 路，可用 VIDEO_DEVOUR_FFMPEG_CONCURRENCY 覆盖。
# 单个 ffmpeg 进程的编码线程数：核数的一半，给系统留出余量
FFMPEG_THREADS = max(1, (os.cpu_count() or 4) // 2)

VIDEO_CONCURRENCY = max(1, min(2, int(os.getenv(
    "VIDEO_DEVOUR_FFMPEG_CONCURRENCY",
    "2" if (os.cpu_count() or 4) >= 8 else "1",
))))

def _ffmpeg_cmd(*args):
    """
    构造受资源约束的 ffmpeg 命令：
    - nice 降低优先级（交互式请求优先）
    - -threads 限制编码线程数（避免多进程叠加打满 CPU）
    注意 -threads 需放在输入之前作为全局参数。
    """
    cmd = ["nice", "-n", "10", _rt_paths.ffmpeg_path(), "-threads", str(FFMPEG_THREADS)]
    cmd.extend(args)
    return cmd


def cut_videos_by_headings(headings_with_level, matched_data, input_video_path, output_dir=None):
    """
    根据匹配块的时间戳将源视频切分为片段
    
    视频片段保存结构：
    output_dir/videocut/
        ├── 01_标题1.mp4
        ├── 02_标题2.mp4
        └── ...
    
    Args:
        headings (list): 标题列表
        matched_data (dict): 标题到匹配文本块的映射字典
        input_video_path (str): 输入视频文件的路径。
        output_dir (str, optional): 输出目录路径。如果未提供，使用默认输出目录
        
    Returns:
        str: 视频片段保存的目录路径
    """
    logging.info(f"--- 步骤 6: 开始根据大纲切分视频 ---")
    
    # 确定输出目录
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    # 构建videocut子目录
    videocut_folder = "videocut"
    videocut_path = os.path.join(output_dir, videocut_folder)
    os.makedirs(videocut_path, exist_ok=True)
    
    logging.info(f"视频片段将保存到: {videocut_path}")
    
    video_cut_count = 0
    cut_jobs = []   # (heading, output_path, ffmpeg_command)
    for i, (level, heading) in enumerate(headings_with_level):
        # 只为二级标题创建视频剪辑
        if level != 2:
            logging.info(f"跳过非二级标题 '{heading}' (级别: {level})")
            continue
            
        if heading in matched_data and matched_data[heading]:
            chunks = matched_data[heading]
            
            # 确保chunks按时间戳排序（应该已经是排序的，但为了安全起见再排一次）
            chunks_sorted = sorted(chunks, key=lambda x: x['start'])
            
            # 获取第一个块的开始时间和最后一个块的结束时间
            start_time = chunks_sorted[0]['start']
            end_time = chunks_sorted[-1]['end']
            
            # 记录匹配的块数量和时间范围
            chunk_count = len(chunks_sorted)
            duration = end_time - start_time
            
            logging.info(f"标题 '{heading}' 匹配了 {chunk_count} 个文本块")
            if chunk_count > 1:
                # 显示所有块的时间范围
                time_ranges = []
                for chunk in chunks_sorted:
                    s = f"{int(chunk['start'] // 60):02d}:{int(chunk['start'] % 60):02d}"
                    e = f"{int(chunk['end'] // 60):02d}:{int(chunk['end'] % 60):02d}"
                    time_ranges.append(f"[{s}-{e}]")
                logging.info(f"  文本块时间范围: {', '.join(time_ranges)}")
            
            safe_heading = re.sub(r'[\\/*?:"<>|]', "", heading).replace(" ", "_")
            output_filename = f"{i+1:02d}_{safe_heading}.mp4"
            output_path = os.path.join(videocut_path, output_filename)
            
            logging.info(f"正在切分视频片段: '{heading}' ({start_time:.2f}s 到 {end_time:.2f}s, 时长: {duration:.2f}s)")
            
            # 使用重新编码而不是 -c copy，确保视频流完整
            # -c:v libx264: 使用 H.264 编码视频
            # -c:a aac: 使用 AAC 编码音频
            # -avoid_negative_ts make_zero: 避免负时间戳问题
            ffmpeg_command = _ffmpeg_cmd(
                '-i', input_video_path,
                '-ss', str(start_time), '-to', str(end_time),
                '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                '-y', output_path
            )
            
            cut_jobs.append((heading, output_path, ffmpeg_command))

    # 并行切分所有片段（每段独立 ffmpeg 重编码，互不依赖）
    if cut_jobs:
        def _run_cut(job):
            heading, output_path, cmd = job
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logging.info(f"成功保存视频片段到: {output_path}")
                return True
            except subprocess.CalledProcessError as e:
                logging.error(f"ffmpeg 执行失败({heading}): {e.stderr.decode('utf-8', errors='ignore')[:300]}")
                return False
            except FileNotFoundError:
                logging.error("错误: 'ffmpeg' 未找到。请确保 ffmpeg 已安装并处于系统的 PATH 中。")
                return None

        with ThreadPoolExecutor(max_workers=min(VIDEO_CONCURRENCY, len(cut_jobs))) as pool:
            for ok in pool.map(_run_cut, cut_jobs):
                if ok is None:      # ffmpeg 缺失，直接终止
                    print("错误: 'ffmpeg' 未找到。视频切分步骤无法执行。")
                    return None
                if ok:
                    video_cut_count += 1

    if video_cut_count > 0:
        logging.info(f"--- 视频切分完成，共生成 {video_cut_count} 个视频片段 ---")
        print(f"视频切分完成！共 {video_cut_count} 个片段已保存至: {videocut_path}")
    else:
        # 兜底：二级标题均未匹配到文本块（常见于短视频或标题为 LLM 转述的场景）。
        # 按二级标题数量把整体时间范围均分切分，保证每个章节有独立的抽帧来源；
        # 若所有章节共用一段，后续关键帧环节会因候选帧相同而插出重复图片。
        logging.warning("--- 未切分任何视频片段，尝试兜底切分 ---")
        all_chunks = [c for chunks in matched_data.values() for c in chunks]
        level2_items = [(i, h) for i, (lvl, h) in enumerate(headings_with_level) if lvl == 2]
        if all_chunks and level2_items:
            start_time = min(c['start'] for c in all_chunks)
            end_time = max(c['end'] for c in all_chunks)
            total = end_time - start_time
            k = len(level2_items)
            if k == 1:
                ranges = [(start_time, end_time)]
            else:
                step = total / k
                ranges = [(start_time + step * j, start_time + step * (j + 1))
                          for j in range(k)]
            logging.info(f"按 {k} 个二级标题均分时间范围 {start_time:.1f}s - {end_time:.1f}s")
            for (i, heading), (seg_start, seg_end) in zip(level2_items, ranges):
                safe_heading = re.sub(r'[\\/*?:"<>|]', "", heading).replace(" ", "_")
                output_path = os.path.join(videocut_path, f"{i+1:02d}_{safe_heading}.mp4")
                ffmpeg_command = [
                    _rt_paths.ffmpeg_path(), '-i', input_video_path,
                    '-ss', f"{seg_start:.2f}", '-to', f"{seg_end:.2f}",
                    '-c:v', 'libx264', '-c:a', 'aac',
                    '-avoid_negative_ts', 'make_zero',
                    '-y', output_path
                ]
                try:
                    subprocess.run(ffmpeg_command, check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    logging.info(f"兜底切分成功: {output_path} ({seg_start:.1f}s - {seg_end:.1f}s)")
                    video_cut_count += 1
                except subprocess.CalledProcessError as e:
                    logging.error(f"兜底切分失败({heading}): "
                                  f"{e.stderr.decode('utf-8', errors='ignore')[:300]}")
        elif all_chunks:
            # 无二级标题的扁平大纲：按所有匹配文本块的整体时间范围切一整段
            start_time = min(c['start'] for c in all_chunks)
            end_time = max(c['end'] for c in all_chunks)
            heading = next((h for lvl, h in headings_with_level if lvl == 1), None)
            if heading:
                safe_heading = re.sub(r'[\\/*?:"<>|]', "", heading).replace(" ", "_")
                output_path = os.path.join(videocut_path, f"01_{safe_heading}.mp4")
                ffmpeg_command = _ffmpeg_cmd(
                    '-i', input_video_path,
                    '-ss', str(start_time), '-to', str(end_time),
                    '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac',
                    '-avoid_negative_ts', 'make_zero',
                    '-y', output_path
                )
                try:
                    subprocess.run(ffmpeg_command, check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    logging.info(f"兜底切分成功: {output_path} ({start_time:.1f}s - {end_time:.1f}s)")
                    video_cut_count = 1
                except subprocess.CalledProcessError as e:
                    logging.error(f"兜底切分失败: {e.stderr.decode('utf-8', errors='ignore')[:500]}")
        if video_cut_count == 0:
            logging.warning("--- 未切分任何视频片段 ---")

    return videocut_path

def extract_frames_from_videos(videocut_path=None, output_dir=None):
    """
    从视频剪辑目录中的所有视频片段提取帧
    
    帧文件保存结构：
    output_dir/frames_视频名/
        ├── frame_0001.jpg
        ├── frame_0002.jpg
        └── ...
    
    Args:
        videocut_path (str, optional): 视频切片目录路径。如果未提供，使用默认路径
        output_dir (str, optional): 输出目录路径。如果未提供，使用默认输出目录
        
    Returns:
        list: 包含所有生成的帧目录路径的列表
    """
    logging.info(f"--- 步骤 7: 开始从视频片段中提取帧 ---")
    
    # 确定视频切片目录
    if videocut_path is None:
        videocut_path = os.path.join(config.OUTPUT_DIR, 'videocut')
    
    if not os.path.isdir(videocut_path):
        logging.warning(f"视频剪辑目录 '{videocut_path}' 未找到，跳过帧提取。")
        return []

    # 确定输出目录
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    frame_extraction_count = 0
    video_files = [f for f in os.listdir(videocut_path) if f.endswith('.mp4')]
    frame_dirs = []
    
    logging.info(f"从目录读取视频文件: {videocut_path}")
    logging.info(f"找到 {len(video_files)} 个视频文件")
    
    def _extract_one(video_file):
        """抽取单个片段的帧，返回 (帧数, 帧目录) 或 (None, None)"""
        video_path = os.path.join(videocut_path, video_file)
        video_name = os.path.splitext(video_file)[0]
        frame_output_dir = os.path.join(output_dir, f"frames_{video_name}")
        os.makedirs(frame_output_dir, exist_ok=True)
        logging.info(f"正在从 '{video_file}' 提取帧到 '{frame_output_dir}'...")
        cmd = _ffmpeg_cmd(
            '-i', video_path, '-vf', 'fps=1',
            '-q:v', '2', os.path.join(frame_output_dir, 'frame_%04d.jpg')
        )
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            num = len([f for f in os.listdir(frame_output_dir) if f.endswith('.jpg')])
            logging.info(f"成功从 '{video_file}' 提取了 {num} 帧。")
            return num, frame_output_dir
        except subprocess.CalledProcessError as e:
            logging.error(f"从 '{video_file}' 提取帧失败: {e.stderr.decode('utf-8', errors='ignore')[:300]}")
            return None, None
        except FileNotFoundError:
            return 'no_ffmpeg', None

    # 并行抽帧（每个片段独立，按视频文件名排序保证 frame_dirs 顺序稳定）
    if video_files:
        with ThreadPoolExecutor(max_workers=min(VIDEO_CONCURRENCY, len(video_files))) as pool:
            results = list(pool.map(_extract_one, sorted(video_files)))
        if any(r[0] == 'no_ffmpeg' for r in results):
            logging.error("错误: 'ffmpeg' 未找到。")
            print("错误: 'ffmpeg' 未找到。帧提取步骤无法执行。")
            return []
        for num, fdir in results:
            if num:
                frame_extraction_count += num
                frame_dirs.append(fdir)

    if frame_extraction_count > 0:
        logging.info(f"--- 帧提取完成，总共提取了 {frame_extraction_count} 帧 ---")
        print(f"帧提取完成！共 {frame_extraction_count} 帧已保存。")
    else:
        logging.warning("--- 未提取任何帧 ---")
    
    return frame_dirs
