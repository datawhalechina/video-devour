# -*- coding: utf-8 -*-
"""
ASR 引擎工厂

根据运行时设置（settings.json 中的 asr_mode）创建对应的 ASR 引擎：
- offline: 本地 FunASR Paraformer V2（需要下载模型，依赖 torch/funasr，按需惰性导入）
- online:  云端识别，提供商可选 DashScope 或 阶跃星辰 StepFun（零本地模型，
           音频直接流式上传，不依赖对象存储）

两个引擎的 devour_video() 输出格式完全一致，pipeline 无需感知差异。
"""
import logging

from backend.algorithm.settings_store import PROVIDER_DEFAULT_ASR_MODEL


def get_asr_mode() -> str:
    """
    读取当前 ASR 模式。

    默认 online：本地离线模型（FunASR Paraformer，约 2GB）下载慢且吃 CPU/内存，
    不应作为新用户的默认路径；需要离线识别时再到设置页显式切换并安装。
    """
    try:
        from backend.algorithm.settings_store import load_settings
        return load_settings().get("asr_mode") or "online"
    except Exception:
        return "online"


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
        settings = load_settings()
        provider = settings.get("online_asr_provider", "dashscope")

        if provider == "stepfun":
            from backend.devour.asr_engine_stepfun import VideoDevourASRStepFun

            engine = VideoDevourASRStepFun(
                api_key=settings.get("stepfun_api_key") or None,
                model=settings.get("online_asr_model")
                    or PROVIDER_DEFAULT_ASR_MODEL["stepfun"],
            )
            logging.info("已创建在线 ASR 引擎（StepFun 阶跃星辰）")
            return engine

        from backend.devour.asr_engine_dashscope import VideoDevourASRDashScope

        engine = VideoDevourASRDashScope(
            api_key=settings.get("dashscope_api_key") or None,
            model=settings.get("online_asr_model")
                or PROVIDER_DEFAULT_ASR_MODEL["dashscope"],
        )
        logging.info("已创建在线 ASR 引擎（DashScope）")
        return engine

    # offline：重量级依赖（torch/funasr）延迟到真正使用时才导入
    try:
        from backend.devour.asr_engine_paraformer_v2 import VideoDevourASRParaformerV2
    except ImportError as e:
        # 轻量包不含 torch/funasr：给出可操作提示，而非裸的 ModuleNotFoundError
        raise RuntimeError(
            "当前为离线 ASR 模式，但本安装包不包含本地语音识别引擎"
            "（缺少 torch/funasr）。请在「偏好设置」中切换为在线 ASR，"
            f"或安装带本地引擎的增强版。（{e}）"
        ) from e

    logging.info("已创建离线 ASR 引擎（本地 Paraformer V2）")
    return VideoDevourASRParaformerV2()
