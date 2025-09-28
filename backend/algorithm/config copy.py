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
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_whisper.json')

# Final Markdown outline output file
OUTLINE_MD_PATH = os.path.join(OUTPUT_DIR, 'outline.md')


# --- LLM Configuration ---

# The model type to be used (e.g., "qwen-plus")
LLM_MODEL_TYPE = "deepseek-v3.1"

# The API endpoint URL for the OpenAI-compatible model
LLM_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# The temperature setting for the LLM, controlling randomness
LLM_TEMPERATURE = 0.4


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
