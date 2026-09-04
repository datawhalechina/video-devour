# -*- coding: utf-8 -*-
"""
ASR 引擎工厂

根据运行时设置（settings.json 中的 asr_mode）创建对应的 ASR 引擎：
- offline: 本地 FunASR Paraformer V2（需要下载模型，依赖 torch/funasr，按需惰性导入）
- online:  DashScope 云端识别（零本地模型，直接流式上传本地音频，不依赖对象存储）

两个引擎的 devour_video() 输出格式完全一致，pipeline 无需感知差异。
"""
import logging


def get_asr_mode() -> str:
    """读取当前 ASR 模式，默认 offline"""
    try:
        from backend.algorithm.settings_store import load_settings
        return load_settings().get("asr_mode", "offline")
    except Exception:
        return "offline"


def create_asr_engine(mode: str = None):
    """
    创建 ASR 引擎实例

    Args:
        mode: "offline" | "online"；为空时读取 settings.json 中的 asr_mode

    Returns:
        具有 devour_video(video_path) 方法的引擎实例
    """
    if mode is None:
        mode = get_asr_mode()

    if mode == "online":
        from backend.algorithm.settings_store import load_settings
        from backend.devour.asr_engine_dashscope import VideoDevourASRDashScope

        settings = load_settings()
        engine = VideoDevourASRDashScope(
            api_key=settings.get("dashscope_api_key") or None,
            model=settings.get("online_asr_model", "fun-asr-realtime"),
        )
        logging.info("已创建在线 ASR 引擎（DashScope）")
        return engine

    # offline：重量级依赖（torch/funasr）延迟到真正使用时才导入
    from backend.devour.asr_engine_paraformer_v2 import VideoDevourASRParaformerV2

    logging.info("已创建离线 ASR 引擎（本地 Paraformer V2）")
    return VideoDevourASRParaformerV2()
