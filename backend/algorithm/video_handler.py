# backend/algorithm/video_handler.py
import os
import re
import logging
import subprocess
from datetime import datetime
import config

def cut_videos_by_headings(headings, matched_data, output_dir=None):
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
    for i, heading in enumerate(headings):
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
            ffmpeg_command = [
                'ffmpeg', '-i', config.INPUT_VIDEO_PATH,
                '-ss', str(start_time), '-to', str(end_time),
                '-c:v', 'libx264', '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                '-y', output_path
            ]
            
            try:
                subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logging.info(f"成功保存视频片段到: {output_path}")
                video_cut_count += 1
            except subprocess.CalledProcessError as e:
                logging.error(f"ffmpeg 执行失败，命令为: {' '.join(ffmpeg_command)}")
                logging.error(f"ffmpeg 错误输出:\\n{e.stderr.decode('utf-8')}")
            except FileNotFoundError:
                logging.error("错误: 'ffmpeg' 未找到。请确保 ffmpeg 已安装并处于系统的 PATH 中。")
                print("错误: 'ffmpeg' 未找到。视频切分步骤无法执行。")
                return None

    if video_cut_count > 0:
        logging.info(f"--- 视频切分完成，共生成 {video_cut_count} 个视频片段 ---")
        print(f"视频切分完成！共 {video_cut_count} 个片段已保存至: {videocut_path}")
    else:
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
    
    for video_file in video_files:
        video_path = os.path.join(videocut_path, video_file)
        video_name = os.path.splitext(video_file)[0]
        
        # 构建帧文件夹名称：frames_视频名
        frame_folder_name = f"frames_{video_name}"
        frame_output_dir = os.path.join(output_dir, frame_folder_name)
        os.makedirs(frame_output_dir, exist_ok=True)
        
        logging.info(f"正在从 '{video_file}' 提取帧到 '{frame_output_dir}'...")
        
        ffmpeg_command = [
            'ffmpeg', '-i', video_path, '-vf', 'fps=1',
            '-q:v', '2', os.path.join(frame_output_dir, 'frame_%04d.jpg')
        ]

        try:
            subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            num_frames = len([f for f in os.listdir(frame_output_dir) if f.endswith('.jpg')])
            logging.info(f"成功从 '{video_file}' 提取了 {num_frames} 帧。")
            logging.info(f"帧已保存到: {frame_output_dir}")
            frame_extraction_count += num_frames
            frame_dirs.append(frame_output_dir)
        except subprocess.CalledProcessError as e:
            logging.error(f"从 '{video_file}' 提取帧失败。")
            logging.error(f"ffmpeg 错误输出:\\n{e.stderr.decode('utf-8')}")
        except FileNotFoundError:
            logging.error("错误: 'ffmpeg' 未找到。")
            print("错误: 'ffmpeg' 未找到。帧提取步骤无法执行。")
            return []

    if frame_extraction_count > 0:
        logging.info(f"--- 帧提取完成，总共提取了 {frame_extraction_count} 帧 ---")
        print(f"帧提取完成！共 {frame_extraction_count} 帧已保存。")
    else:
        logging.warning("--- 未提取任何帧 ---")
    
    return frame_dirs
