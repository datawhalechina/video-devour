# -*- coding: utf-8 -*-
"""
Main entry point for the video processing pipeline.
"""
import os
import sys
import argparse
import logging

# 将项目根目录添加到sys.path以支持绝对导入
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from backend.algorithm.pipeline import run_full_pipeline

def main():
    """Parses command-line arguments and starts the processing pipeline."""
    parser = argparse.ArgumentParser(description="视频处理流程，从ASR到生成最终报告。")
    parser.add_argument("video_path", type=str, help="需要处理的视频文件的路径。")
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.video_path):
        print(f"错误: 视频文件未找到 '{args.video_path}'")
        logging.error(f"视频文件未找到 '{args.video_path}'")
        return
        
    # 启动完整的处理流程
    run_full_pipeline(args.video_path)

if __name__ == '__main__':
    main()
