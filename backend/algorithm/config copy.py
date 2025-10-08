# -*- coding: utf-8 -*-
"""
Configuration file for the Video-to-Report project.

This file centralizes settings for file paths, LLM parameters, and API keys
to allow for easy management and modification without altering the core logic.
"""

import os

# --- File and Directory Paths ---

# Get the absolute path of the directory where this script is located (the 'algorithm' directory)
_ALGORITHM_DIR = os.path.dirname(os.path.abspath(__file__))

# Get the root directory of the project ('VideoDevour') by going up two levels
PROJECT_ROOT = os.path.abspath(os.path.join(_ALGORITHM_DIR, '..', '..'))

# Define the output directory
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

# Input ASR result file
# 支持多种格式：
# - asr_results_paraformer_v2.json (推荐，新格式，已包含说话人信息)
# - asr_results_paraformer.json (旧格式，需要时间戳匹配)
# - asr_results_whisper.json (Whisper 格式)
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_paraformer_v2.json')

# Input video file
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, 'input_video', 'minvideo.mp4')

# 最大token数
LLM_TOKEN_COUNTER = 128000
# --- 输出路径说明 ---
# 所有输出文件都统一保存在 OUTPUT_DIR 目录或其子目录中
# 
# 实际输出结构：
# output/
#   ├── frames_视频名_时间戳/          # 统一的大文件夹（由 main.py 创建）
#   │   ├── outline.md                 # 大纲文件
#   │   ├── detailed_outline.md        # 详细大纲文件
#   │   ├── videocut/                  # 视频切片目录
#   │   │   ├── 01_标题1.mp4
#   │   │   └── 02_标题2.mp4
#   │   └── frames_XX/                 # 帧提取目录
#   │       ├── frame_0001.jpg
#   │       └── frame_0002.jpg
#   └── asr_results_*.json             # ASR 结果文件


# --- LLM Configuration ---

# The model type to be used (e.g., "qwen-plus")
LLM_MODEL_TYPE = "deepseek-chat"

# The API endpoint URL for the OpenAI-compatible model
LLM_API_URL = "https://api.deepseek.com"

# The temperature setting for the LLM, controlling randomness
LLM_TEMPERATURE = 0.4


# --- VLM Configuration ---

# The model type for the Vision Language Model
VLM_MODEL_TYPE = "doubao-seed-1-6-flash-250828"

# The API endpoint URL for the VLM
VLM_API_URL = "https://ark.cn-beijing.volces.com/api/v3"

# The API key for the VLM
VLM_API_KEY = "eb4ff0cf-"  # Replace with your actual key or use environment variables


# --- API Key Management ---

def get_api_key():
    """
    Retrieves the DashScope API key.

    It first attempts to get the key from the 'DASHSCOPE_API_KEY' environment
    variable. If not found, it falls back to a hardcoded example key and issues
    a warning.

    Returns:
        str: The API key.
    """
    api_key = os.getenv("DASHSCOPE_API_KEY", "sk-")
    if api_key == "sk-":
        print("Warning: Using a hardcoded example API key. For security, it's recommended to set the DASHSCOPE_API_KEY environment variable.")
    return api_key
