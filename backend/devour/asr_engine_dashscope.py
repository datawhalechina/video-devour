# -*- coding: utf-8 -*-
"""
VideoDevour ASR Engine - DashScope 云端版

使用 DashScope 的 fun-asr-realtime（Paraformer 系列）流式识别接口，
直接对本地音频文件进行转写，无需将音频上传到第三方对象存储。

输出格式与离线引擎 VideoDevourASRParaformerV2 完全一致：
{
    "transcript": [ {"index", "spk_id", "sentence", "start_time"(秒), "end_time"(秒)}, ... ],
    "video_path": str,
    "processed_at": iso,
    "text_stats": {...}
}
"""
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from backend.runtime import paths as _rt_paths


class VideoDevourASRDashScope:
    """
    VideoDevour ASR 引擎 - DashScope 云端版本

    功能特性：
    - 使用 DashScope 云端识别接口，本地无需下载任何 ASR 模型
    - 音频直接从本地流式上传，不经过七牛云等对象存储
    - 自动通过 ffmpeg 将视频/音频转换为 16kHz 单声道 WAV
    - 输出格式与离线 Paraformer V2 引擎一致
    """

    def __init__(self, api_key: str = None, model: str = "fun-asr-realtime"):
        """
        Args:
            api_key: DashScope API Key；为空时回退到环境变量 DASHSCOPE_API_KEY
            model: 识别模型名，默认 fun-asr-realtime
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model
        if not self.api_key:
            raise ValueError(
                "未配置 DashScope API Key。请在控制台（/settings）填写，"
                "或设置环境变量 DASHSCOPE_API_KEY。"
            )
        logging.info(f"DashScope ASR 引擎初始化完成（模型: {self.model}）")

    def _extract_audio_to_wav(self, video_path: str) -> str:
        """用 ffmpeg 将视频/音频转换为 16kHz 单声道 WAV，返回临时文件路径"""
        fd, wav_path = tempfile.mkstemp(prefix="videodevour_asr_", suffix=".wav")
        os.close(fd)
        command = [
            _rt_paths.ffmpeg_path(), "-i", video_path,
            "-ac", "1",          # 单声道
            "-ar", "16000",      # 16kHz，识别接口要求
            "-vn",               # 去掉视频流
            "-y", wav_path,
        ]
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            if os.path.exists(wav_path):
                os.remove(wav_path)
            raise RuntimeError(f"ffmpeg 音频提取失败: {e.stderr[-500:] if e.stderr else e}")
        except FileNotFoundError:
            if os.path.exists(wav_path):
                os.remove(wav_path)
            raise RuntimeError("未找到 ffmpeg，请先安装（brew install ffmpeg / apt install ffmpeg）")
        return wav_path

    def normalize_result(self, sentences: List[Dict]) -> List[Dict]:
        """
        将 DashScope 识别结果规范化为与离线引擎一致的标准格式

        Args:
            sentences: Recognition 结果的句级列表
                [{"text": "...", "begin_time": 0, "end_time": 1500}, ...]  时间单位毫秒

        Returns:
            List[Dict]: 标准化后的结果列表（时间单位：秒）
        """
        results: List[Dict] = []
        for idx, s in enumerate(sentences, start=1):
            sent_text = (s.get("text") or "").strip()
            if not sent_text:
                continue
            try:
                st = float(s.get("begin_time", 0))
            except Exception:
                st = 0.0
            try:
                ed = float(s.get("end_time", st))
            except Exception:
                ed = st
            results.append({
                "index": len(results) + 1,
                "spk_id": "spk0",
                "sentence": sent_text,
                "start_time": st / 1000,
                "end_time": ed / 1000,
            })
        logging.info(f"规范化完成，共 {len(results)} 个句子")
        return results

    def devour_video(self, video_path: str) -> Dict:
        """
        核心处理方法 - 对视频进行语音识别（云端）

        Args:
            video_path: 视频或音频文件路径

        Returns:
            Dict: 与离线引擎格式一致的识别结果
        """
        logging.info(f"[DashScope] 开始处理视频: {video_path}")
        wav_path = None
        try:
            from dashscope.audio.asr import Recognition
            from http import HTTPStatus
            import dashscope

            dashscope.api_key = self.api_key

            wav_path = self._extract_audio_to_wav(video_path)
            logging.info("[DashScope] 正在进行语音识别...")

            recognition = Recognition(
                model=self.model,
                format="wav",
                sample_rate=16000,
                callback=None,
            )
            result = recognition.call(wav_path)

            if result.status_code != HTTPStatus.OK:
                raise RuntimeError(f"DashScope 识别失败: {result.message} (code={result.status_code})")

            sentences = result.get_sentence() or []
            if not sentences:
                raise RuntimeError("DashScope 未识别出任何内容（音频可能没有语音）")

            transcript = self.normalize_result(sentences)

            text_stats = {}
            if transcript:
                total_text = " ".join([seg.get("sentence", "") for seg in transcript])
                text_stats = {
                    "total_segments": len(transcript),
                    "total_words": len(total_text.split()),
                    "total_chars": len(total_text),
                    "avg_segment_duration": sum([
                        seg.get("end_time", 0) - seg.get("start_time", 0)
                        for seg in transcript
                    ]) / len(transcript),
                }

            logging.info(f"[DashScope] 识别完成，共 {len(transcript)} 句")
            return {
                "transcript": transcript,
                "video_path": video_path,
                "processed_at": datetime.now().isoformat(),
                "text_stats": text_stats,
            }
        except Exception as e:
            logging.error(f"[DashScope] ASR 处理失败: {str(e)}")
            raise
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
