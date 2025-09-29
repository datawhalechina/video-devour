# backend/algorithm/video_handler.py
import os
import re
import logging
import subprocess
import config

def cut_videos_by_headings(headings, matched_data):
    """
    Cuts the source video into clips based on the timestamps of matched chunks for each heading.
    
    Args:
        headings (list): The list of heading titles.
        matched_data (dict): A dictionary mapping headings to their matched text chunks.
    """
    logging.info(f"--- 步骤 6: 开始根据大纲切分视频 ---")
    
    os.makedirs(config.VIDEO_CUT_DIR, exist_ok=True)
    
    video_cut_count = 0
    for i, heading in enumerate(headings):
        if heading in matched_data and matched_data[heading]:
            chunks = matched_data[heading]
            
            start_time = chunks[0]['start']
            end_time = chunks[-1]['end']
            
            safe_heading = re.sub(r'[\\/*?:"<>|]', "", heading).replace(" ", "_")
            output_filename = f"{i+1:02d}_{safe_heading}.mp4"
            output_path = os.path.join(config.VIDEO_CUT_DIR, output_filename)
            
            logging.info(f"正在切分视频片段: '{heading}' ({start_time:.2f}s to {end_time:.2f}s)")
            
            ffmpeg_command = [
                'ffmpeg', '-i', config.INPUT_VIDEO_PATH,
                '-ss', str(start_time), '-to', str(end_time),
                '-c', 'copy', '-y', output_path
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
                return

    if video_cut_count > 0:
        logging.info(f"--- 视频切分完成，共生成 {video_cut_count} 个视频片段 ---")
        print(f"视频切分完成！共 {video_cut_count} 个片段已保存至: {config.VIDEO_CUT_DIR}")
    else:
        logging.warning("--- 未切分任何视频片段 ---")

def extract_frames_from_videos():
    """
    Extracts frames from all video clips in the video cut directory.
    """
    logging.info(f"--- 步骤 7: 开始从视频片段中提取帧 ---")
    os.makedirs(config.IMAGE_OUTPUT_DIR, exist_ok=True)
    
    if not os.path.isdir(config.VIDEO_CUT_DIR):
        logging.warning(f"视频剪辑目录 '{config.VIDEO_CUT_DIR}' 未找到，跳过帧提取。")
        return

    frame_extraction_count = 0
    video_files = [f for f in os.listdir(config.VIDEO_CUT_DIR) if f.endswith('.mp4')]
    
    for video_file in video_files:
        video_path = os.path.join(config.VIDEO_CUT_DIR, video_file)
        video_name = os.path.splitext(video_file)[0]
        frame_output_dir = os.path.join(config.IMAGE_OUTPUT_DIR, video_name)
        os.makedirs(frame_output_dir, exist_ok=True)
        
        logging.info(f"正在从 '{video_file}' 提取帧到 '{frame_output_dir}'...")
        
        ffmpeg_command = [
            'ffmpeg', '-i', video_path, '-vf', 'fps=12',
            '-q:v', '2', os.path.join(frame_output_dir, 'frame_%04d.jpg')
        ]

        try:
            subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            num_frames = len(os.listdir(frame_output_dir))
            logging.info(f"成功从 '{video_file}' 提取了 {num_frames} 帧。")
            frame_extraction_count += num_frames
        except subprocess.CalledProcessError as e:
            logging.error(f"从 '{video_file}' 提取帧失败。")
            logging.error(f"ffmpeg 错误输出:\\n{e.stderr.decode('utf-8')}")
        except FileNotFoundError:
            logging.error("错误: 'ffmpeg' 未找到。")
            print("错误: 'ffmpeg' 未找到。帧提取步骤无法执行。")
            return

    if frame_extraction_count > 0:
        logging.info(f"--- 帧提取完成，总共提取了 {frame_extraction_count} 帧 ---")
        print(f"帧提取完成！共 {frame_extraction_count} 帧已保存至: {config.IMAGE_OUTPUT_DIR}")
    else:
        logging.warning("--- 未提取任何帧 ---")
