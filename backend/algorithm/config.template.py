# -*- coding: utf-8 -*-
# VideoDevour 配置模板
#
# 使用方法：
#   cp config.template.py config.py
# 然后按需修改。config.py 已被 .gitignore 排除，不会被提交。
#
# 提示：无需手动编辑密钥 —— 启动后端后访问前端控制台（/settings）
# 填写 API 配置即可，控制台的设置会与本文件的默认值合并（控制台优先）。

import os

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_PROJECT_DIR, "..", ".."))

# 输出目录
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# ASR 结果与输入视频的默认路径
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, "asr_results_paraformer_v2.json")
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, "input_video", "video.mp4")

# ---------------------------------------------------------------------------
# LLM 配置（OpenAI 兼容接口）
# 密钥推荐通过环境变量注入，也可以在前端控制台（/settings）填写
# ---------------------------------------------------------------------------
LLM_MODEL_TYPE = "deepseek-chat"
LLM_API_URL = "https://api.deepseek.com"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_TEMPERATURE = 0.4
LLM_TOKEN_COUNTER = 128000

# ---------------------------------------------------------------------------
# VLM 配置（OpenAI 兼容接口，用于关键帧评分）
# ---------------------------------------------------------------------------
VLM_MODEL_TYPE = "doubao-seed-1-6-flash-250828"
VLM_API_URL = "https://ark.cn-beijing.volces.com/api/v3"
VLM_API_KEY = os.getenv("VLM_API_KEY", "")
