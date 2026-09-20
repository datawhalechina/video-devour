# -*- coding: utf-8 -*-
"""阶跃星辰 StepFun TTS 引擎：/audio/speech 合成语音（返回音频字节）。

Step Plan 音频合成接口（OpenAI 风格 /audio/speech）：
    POST {base}/audio/speech
    body: {model, input, voice, instruction?, response_format}
    返回音频二进制（如 mp3）。

默认模型 stepaudio-2.5-tts；可在设置页选 stepaudio-3-tts 等（需账号已开通该模型，
否则接口返回 404 model_invalid）。音色/指令参数透传，具体取值见阶跃星辰音频文档。
"""
import logging

import requests

DEFAULT_BASE_URL = "https://api.stepfun.com/step_plan/v1"
DEFAULT_MODEL = "stepaudio-2.5-tts"
DEFAULT_VOICE = "cixingnansheng"
DEFAULT_FORMAT = "mp3"

# 单次合成文本长度上限（超长分段由调用方处理，避免接口报错）
MAX_INPUT_CHARS = 2000


class StepFunTTS:
    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL,
                 base_url: str = DEFAULT_BASE_URL, voice: str = DEFAULT_VOICE):
        if not api_key:
            raise ValueError("未配置阶跃星辰 StepFun API Key（stepfun_api_key），请在设置页「阶跃星辰」填写")
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.voice = voice or DEFAULT_VOICE

    def synthesize(self, text: str, voice: str = None, model: str = None,
                   response_format: str = DEFAULT_FORMAT, instruction: str = None) -> bytes:
        """合成语音，返回音频字节（默认 mp3）。"""
        text = (text or "").strip()
        if not text:
            raise ValueError("合成文本不能为空")
        if len(text) > MAX_INPUT_CHARS:
            text = text[:MAX_INPUT_CHARS]
        body = {
            "model": model or self.model,
            "input": text,
            "voice": voice or self.voice,
            "response_format": response_format,
        }
        if instruction:
            body["instruction"] = instruction
        logging.info(f"[StepFun TTS] 合成 {len(text)} 字，模型 {body['model']}，音色 {body['voice']}")
        resp = requests.post(
            f"{self.base_url}/audio/speech",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=120,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"StepFun 语音合成失败: HTTP {resp.status_code} {resp.text[:200]}")
        return resp.content
