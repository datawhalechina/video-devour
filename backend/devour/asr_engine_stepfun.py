# -*- coding: utf-8 -*-
"""
VideoDevour ASR Engine - 阶跃星辰 StepFun 云端版

使用 Step Plan 的 stepaudio-2.5-asr 流式识别接口（HTTP + SSE）：
本地音频经 ffmpeg 转为 16kHz 单声道 PCM 后 base64 上传，无需对象存储。

说明：
- 该接口为增量流式转写，不提供句级时间戳。引擎按标点切句，并按字符占比
  线性分配时间戳（近似），以保持下游章节切分 / 关键帧流程可用。
- 输出格式与离线 / DashScope 引擎完全一致。
"""
import base64
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests

DEFAULT_BASE_URL = "https://api.stepfun.com/step_plan/v1"

# 句末标点（用于近似分句）。英文句号单独处理：避免吞掉 "3.5" 这类数字小数点
_SENTENCE_ENDINGS = "。！？!?；;"
_SENTENCE_PERIOD = "."


class VideoDevourASRStepFun:
    """
    VideoDevour ASR 引擎 - StepFun 云端版本

    功能特性：
    - 使用 stepaudio-2.5-asr，本地无模型依赖
    - 音频 base64 直传，HTTP + SSE 流式返回
    - 输出格式与离线 / DashScope 引擎一致
    """

    def __init__(self, api_key: str = None, model: str = "stepaudio-2.5-asr",
                 base_url: str = DEFAULT_BASE_URL):
        self.api_key = api_key or os.getenv("STEP_API_KEY", "")
        self.model = model
        self.base_url = base_url.rstrip("/")
        if not self.api_key:
            raise ValueError(
                "未配置 StepFun API Key。请在控制台（/settings）填写，"
                "或设置环境变量 STEP_API_KEY。"
            )
        logging.info(f"StepFun ASR 引擎初始化完成（模型: {self.model}）")

    def _extract_audio_to_pcm(self, video_path: str) -> str:
        """ffmpeg 转 16kHz 单声道 s16le 裸 PCM（接口要求的格式）"""
        fd, pcm_path = tempfile.mkstemp(prefix="videodevour_step_", suffix=".pcm")
        os.close(fd)
        command = [
            "ffmpeg", "-i", video_path,
            "-ac", "1", "-ar", "16000",
            "-f", "s16le", "-vn", "-y", pcm_path,
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            if os.path.exists(pcm_path):
                os.remove(pcm_path)
            raise RuntimeError(f"ffmpeg 音频提取失败: {e.stderr[-500:] if e.stderr else e}")
        except FileNotFoundError:
            if os.path.exists(pcm_path):
                os.remove(pcm_path)
            raise RuntimeError("未找到 ffmpeg，请先安装")
        return pcm_path

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """按句末标点切句，保留标点。英文句号要求后随空白，避免切碎小数/缩写"""
        sentences, buf = [], ""
        for i, ch in enumerate(text):
            buf += ch
            if ch in _SENTENCE_ENDINGS:
                sentences.append(buf.strip())
                buf = ""
            elif ch == _SENTENCE_PERIOD:
                # 句号后必须是空白/结尾，且前一个字符为字母数字或右括号，
                # 避免切碎 "3.5"、"u.s." 之外的正常小数与缩写
                nxt = text[i + 1] if i + 1 < len(text) else " "
                prev = buf[-2] if len(buf) >= 2 else ""
                if nxt.isspace() and (prev.isalnum() or prev in ")]"):
                    sentences.append(buf.strip())
                    buf = ""
        if buf.strip():
            sentences.append(buf.strip())
        return [s for s in sentences if s]

    def normalize_result(self, text: str, audio_duration: float) -> List[Dict]:
        """
        将完整转写文本按标点分句，按字符占比线性分配时间戳（近似）。
        输出与离线引擎一致：start_time / end_time 单位秒。
        """
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        total_chars = sum(len(s) for s in sentences)
        results, cursor = [], 0.0
        for idx, sent in enumerate(sentences):
            span = audio_duration * (len(sent) / total_chars)
            start = cursor
            end = audio_duration if idx == len(sentences) - 1 else min(cursor + span, audio_duration)
            cursor = end
            results.append({
                "index": idx + 1,
                "spk_id": "spk0",
                "sentence": sent,
                "start_time": round(start, 2),
                "end_time": round(end, 2),
            })
        logging.info(f"规范化完成，共 {len(results)} 个句子（时间为按字数线性近似）")
        return results

    def devour_video(self, video_path: str) -> Dict:
        """核心处理方法：转音频 → base64 上传 → SSE 解析 → 标准化输出"""
        logging.info(f"[StepFun] 开始处理视频: {video_path}")
        pcm_path = None
        try:
            pcm_path = self._extract_audio_to_pcm(video_path)

            # 音频时长（秒）＝ 字节数 / (采样率 × 声道数 × 采样宽度)。
            # 裸 PCM 无容器头，ffprobe 无法读取，直接按大小计算。
            sample_rate, channels, bytes_per_sample = 16000, 1, 2
            duration = os.path.getsize(pcm_path) / (sample_rate * channels * bytes_per_sample)

            with open(pcm_path, "rb") as f:
                pcm_b64 = base64.b64encode(f.read()).decode()

            body = {
                "audio": {
                    "data": pcm_b64,
                    "input": {
                        "transcription": {
                            "model": self.model,
                            "language": "zh",
                            "enable_itn": True,
                        },
                        "format": {
                            "type": "pcm", "codec": "pcm_s16le",
                            "rate": 16000, "bits": 16, "channel": 1,
                        },
                    },
                }
            }
            logging.info("[StepFun] 正在进行语音识别（SSE 流式）...")
            resp = requests.post(
                f"{self.base_url}/audio/asr/sse",
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "Authorization": f"Bearer {self.api_key}",
                },
                stream=True,
                timeout=300,
            )
            if resp.status_code != 200:
                detail = resp.text[:300]
                raise RuntimeError(f"StepFun 识别失败: HTTP {resp.status_code} {detail}")

            full_text = ""
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    event = json.loads(raw[len("data:"):].strip())
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "transcript.text.done":
                    full_text = event.get("text", "")
                    break
                if event.get("type") == "transcript.text.delta":
                    full_text += event.get("delta", "")

            if not full_text.strip():
                raise RuntimeError("StepFun 未识别出任何内容（音频可能没有语音）")

            transcript = self.normalize_result(full_text.strip(), duration)
            text_stats = {}
            if transcript:
                total_text = "".join(seg["sentence"] for seg in transcript)
                text_stats = {
                    "total_segments": len(transcript),
                    "total_words": len(total_text.split()),
                    "total_chars": len(total_text),
                    "avg_segment_duration": sum(
                        seg["end_time"] - seg["start_time"] for seg in transcript
                    ) / len(transcript),
                }

            logging.info(f"[StepFun] 识别完成，共 {len(transcript)} 句")
            return {
                "transcript": transcript,
                "video_path": video_path,
                "processed_at": datetime.now().isoformat(),
                "text_stats": text_stats,
            }
        except Exception as e:
            logging.error(f"[StepFun] ASR 处理失败: {str(e)}")
            raise
        finally:
            if pcm_path and os.path.exists(pcm_path):
                try:
                    os.remove(pcm_path)
                except Exception:
                    pass
