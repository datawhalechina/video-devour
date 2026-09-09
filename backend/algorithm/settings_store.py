# -*- coding: utf-8 -*-
"""
运行时设置存储

提供以下能力：
1. 持久化运行时设置（settings.json）：ASR 模式（离线/在线）、各 API Key 与模型配置
2. 将设置注入到 algorithm 的 config 模块（config.py 缺失时可自动构建默认模块），
   使 LLMHandler / VLMHandler 等在运行期读取到控制台配置
3. 连通性自检（在线 ASR / LLM / VLM）

安全约定：settings.json 含密钥，已被 .gitignore 排除；对外读取时密钥一律脱敏。
"""
import json
import logging
import os
import random
import sys
import types
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ALGORITHM_DIR = Path(__file__).resolve().parent

# 可写数据目录统一走运行时路径解析（冻结/客户端模式下指向用户数据目录，
# 开发模式下仍为源码根，行为不变）。见 backend/runtime/paths.py。
from backend.runtime import paths as _rt_paths

SETTINGS_FILE = _rt_paths.data_root() / "settings.json"

DEFAULT_SETTINGS = {
    # ASR 模式：offline = 本地 FunASR Paraformer（需下载模型，依赖 torch/funasr）；
    # online = 云端识别，提供商由 online_asr_provider 决定。
    # 默认 online：新安装无需下载模型即可使用；本地引擎属增强能力（桌面轻量包不含 torch）。
    # 已有用户 settings.json 中的 offline 配置会被保留，不会被静默改写。
    "asr_mode": "online",
    "dashscope_api_key": "",
    "online_asr_model": "fun-asr-realtime",
    "online_asr_provider": "dashscope",   # dashscope | stepfun
    "stepfun_api_key": "",
    # LLM（OpenAI 兼容接口）
    "llm_api_key": "",
    "llm_api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "llm_model_type": "qwen-max",
    "llm_temperature": 0.4,
    # VLM（OpenAI 兼容接口）
    "vlm_api_key": "",
    "vlm_api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "vlm_model_type": "qwen-vl-max",
    # 默认学习阶段
    "default_education_level": "自由学习",
    # 大纲-文本块匹配策略：
    #   auto     = 有本地语义模型则用语义匹配，否则回退字符串匹配（默认，行为同旧版）
    #   semantic = 强制语义匹配（需要 sentence-transformers/torch）
    #   string   = 强制字符串匹配（无需本地 ML 依赖，轻量包推荐）
    "outline_match_strategy": "auto",
    # 启动时是否预加载离线 ASR 模型。默认 false：避免轻量/客户端场景首启即拉起
    # torch/funasr 并下载模型；离线模式下首个任务再按需加载。
    "preload_asr_on_startup": False,
    # 微信视频号：元宝网页 Cookie 用于分享链接解析（见设置页说明）；
    # 也可选配自建解析服务（ltaoo/wx_channels_download 的 sph worker）
    "wechat_yuanbao_cookie": "",
    "wechat_resolver_url": "",
    "wechat_resolver_token": "",
    # YouTube cookies.txt 内容（Netscape 格式，绕过下载 bot 检查）
    "youtube_cookies": "",
    # B站登录态（SESSDATA，可选）：AI 字幕轨仅对登录态可见，用于字幕速记
    "bilibili_sessdata": "",
    # 一键读取浏览器 Cookie 时使用的浏览器（空 = 自动按序尝试）
    "cookie_browser": "",
}

# 各在线 ASR 提供商的默认模型名（切换 provider 时用于联动，避免模型名串台）
PROVIDER_DEFAULT_ASR_MODEL = {
    "dashscope": "fun-asr-realtime",
    "stepfun": "stepaudio-2.5-asr",
}

# settings 字段 -> config 模块属性 的映射（仅非空时覆盖 config）
_SETTINGS_TO_CONFIG = {
    "llm_api_key": "LLM_API_KEY",
    "llm_api_url": "LLM_API_URL",
    "llm_model_type": "LLM_MODEL_TYPE",
    "vlm_api_key": "VLM_API_KEY",
    "vlm_api_url": "VLM_API_URL",
    "vlm_model_type": "VLM_MODEL_TYPE",
}

EDUCATION_LEVELS = [
    "自由学习",        # 默认：面向普通学习者，不做阶段化适配
    "小学",
    "初中",
    "高中",
    "大学",
    "硕士",
    "博士",
    "深入研究",        # 研究导向：原理/方法/局限的系统性深挖
    "垂直领域研究",    # 面向特定行业/领域的从业者与研究者
]


def load_settings() -> dict:
    """读取 settings.json，缺失的字段用默认值补齐"""
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
            for key in DEFAULT_SETTINGS:
                if key in stored and stored[key] not in (None, ""):
                    settings[key] = stored[key]
        except Exception as e:
            logging.warning(f"读取设置文件失败，使用默认设置: {e}")
    return settings


def save_settings(settings: dict):
    """写入 settings.json"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return value[:2] + "****"
    return value[:6] + "****" + value[-4:]


# 需要脱敏的敏感字段
_SECRET_KEYS = ("dashscope_api_key", "llm_api_key", "vlm_api_key",
                "stepfun_api_key", "wechat_yuanbao_cookie", "wechat_resolver_token",
                "youtube_cookies", "bilibili_sessdata")


def get_settings(mask: bool = True) -> dict:
    settings = load_settings()
    if mask:
        for key in _SECRET_KEYS:
            settings[key] = mask_key(settings.get(key, ""))
    return settings


def update_settings(updates: dict) -> dict:
    """合并更新设置并持久化，返回脱敏后的最新设置"""
    settings = load_settings()
    for key in DEFAULT_SETTINGS:
        if key in updates and updates[key] not in (None, ""):
            # 脱敏值（含 ****）不回写，避免把掩码存成真密钥
            if key in _SECRET_KEYS and "****" in str(updates[key]):
                continue
            settings[key] = updates[key]
    save_settings(settings)
    apply_to_config(settings)
    return get_settings(mask=True)


def _build_default_config_module() -> types.ModuleType:
    """构建一个默认的 config 模块（用于用户尚未创建 config.py 的场景）"""
    module = types.ModuleType("config")
    module.PROJECT_ROOT = str(PROJECT_ROOT)
    module.OUTPUT_DIR = str(_rt_paths.data_root() / "output")
    module.LLM_MODEL_TYPE = "deepseek-chat"
    module.LLM_API_URL = "https://api.deepseek.com"
    module.LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    module.LLM_TEMPERATURE = 0.4
    module.LLM_TOKEN_COUNTER = 128000
    module.VLM_MODEL_TYPE = "doubao-seed-1-6-flash-250828"
    module.VLM_API_URL = "https://ark.cn-beijing.volces.com/api/v3"
    module.VLM_API_KEY = os.getenv("VLM_API_KEY", "")
    return module


def apply_to_config(settings: dict = None):
    """
    将设置注入 config 模块。

    config.py 存在时覆盖其属性；不存在时构建默认模块并注册到 sys.modules
    （同时注册 "config" 与 "backend.algorithm.config" 两个名字，兼容两种导入写法）。
    空值不覆盖：保留 config.py / 环境变量中的原有配置。
    """
    if settings is None:
        settings = load_settings()

    try:
        import config  # noqa
    except ImportError:
        config = _build_default_config_module()
        sys.modules["config"] = config
        sys.modules["backend.algorithm.config"] = config
        logging.info("未找到 config.py，已使用内置默认配置模块（可在控制台填写 API 配置）")

    for setting_key, config_attr in _SETTINGS_TO_CONFIG.items():
        value = settings.get(setting_key)
        if value not in (None, ""):
            setattr(config, config_attr, value)
    if settings.get("llm_temperature") is not None:
        config.LLM_TEMPERATURE = settings["llm_temperature"]

    logging.info(
        f"配置已应用: asr_mode={settings.get('asr_mode')}, "
        f"llm_model={settings.get('llm_model_type')}, vlm_model={settings.get('vlm_model_type')}"
    )
    return config


# ---------------------------------------------------------------------------
# 连通性自检
# ---------------------------------------------------------------------------

def _make_silent_wav(duration_seconds: float = 1.0) -> str:
    """生成一段极短的静音 WAV，用于在线 ASR 连通性测试（不产生识别费用差）"""
    import tempfile
    sample_rate = 16000
    path = os.path.join(tempfile.gettempdir(), "videodevour_asr_test.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * int(sample_rate * duration_seconds))
    return path


def test_asr_online() -> tuple:
    """测试在线 ASR 连通性（按提供商分支），返回 (ok, message)"""
    settings = load_settings()
    provider = settings.get("online_asr_provider", "dashscope")
    if provider == "stepfun":
        return _test_asr_stepfun(settings)
    api_key = settings.get("dashscope_api_key")
    if not api_key:
        return False, "未配置 DashScope API Key"
    try:
        import dashscope
        from dashscope.audio.asr import Recognition
        from http import HTTPStatus

        dashscope.api_key = api_key
        wav_path = _make_silent_wav()
        recognition = Recognition(
            model=settings.get("online_asr_model", "fun-asr-realtime"),
            format="wav",
            sample_rate=16000,
            callback=None,
        )
        result = recognition.call(wav_path)
        if result.status_code == HTTPStatus.OK:
            return True, "在线 ASR 连通正常"
        return False, f"在线 ASR 连接失败: {result.message} (code={result.status_code})"
    except Exception as e:
        return False, f"在线 ASR 测试异常: {e}"
    finally:
        try:
            os.remove(wav_path)
        except Exception:
            pass


def _test_asr_stepfun(settings: dict) -> tuple:
    """StepFun ASR 连通性测试：上传 1 秒静音 PCM，检查接口是否正常响应"""
    api_key = settings.get("stepfun_api_key")
    if not api_key:
        return False, "未配置 StepFun API Key"
    try:
        import base64
        import io
        import wave

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 16000)
        pcm_b64 = base64.b64encode(buf.getvalue()).decode()

        import requests

        body = {
            "audio": {
                "data": pcm_b64,
                "input": {
                    "transcription": {
                        "model": settings.get("online_asr_model", "stepaudio-2.5-asr"),
                        "language": "zh",
                        "enable_itn": True,
                    },
                    "format": {"type": "pcm", "codec": "pcm_s16le",
                               "rate": 16000, "bits": 16, "channel": 1},
                },
            }
        }
        resp = requests.post(
            "https://api.stepfun.com/step_plan/v1/audio/asr/sse",
            json=body,
            headers={"Content-Type": "application/json", "Accept": "text/event-stream",
                     "Authorization": f"Bearer {api_key}"},
            stream=True, timeout=30,
        )
        if resp.status_code == 200:
            resp.close()
            return True, "StepFun 在线 ASR 连通正常"
        return False, f"StepFun ASR 连接失败: HTTP {resp.status_code} {resp.text[:150]}"
    except Exception as e:
        return False, f"StepFun ASR 测试异常: {e}"


def _test_openai_compatible(name: str, base_url: str, api_key: str, model: str) -> tuple:
    """对 OpenAI 兼容接口做一次最小调用，返回 (ok, message)"""
    if not api_key:
        return False, f"未配置 {name} API Key"
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "回复：OK"}],
            max_tokens=8,
        )
        content = (completion.choices[0].message.content or "").strip()
        return True, f"{name} 连通正常（模型: {model}）"
    except Exception as e:
        return False, f"{name} 测试失败: {e}"


def test_llm() -> tuple:
    settings = load_settings()
    return _test_openai_compatible(
        "LLM",
        settings.get("llm_api_url"),
        settings.get("llm_api_key"),
        settings.get("llm_model_type"),
    )


def test_vlm() -> tuple:
    settings = load_settings()
    return _test_openai_compatible(
        "VLM",
        settings.get("vlm_api_url"),
        settings.get("vlm_api_key"),
        settings.get("vlm_model_type"),
    )


def run_tests(target: str = "all") -> dict:
    """运行连通性自检，target: asr | llm | vlm | all"""
    targets = {
        "asr": test_asr_online,
        "llm": test_llm,
        "vlm": test_vlm,
    }
    if target in targets:
        names = [target]
    else:
        names = list(targets.keys())
    results = {}
    for name in names:
        ok, message = targets[name]()
        results[name] = {"ok": ok, "message": message}
    return results


def _bootstrap():
    """
    导入时自举：
    1. 将 backend/algorithm 加入 sys.path（历史代码大量使用 `import config` 裸导入，
       原先依赖 ASR 引擎导入时的 sys.path 副作用，这里改为显式保证）
    2. 若 config.py 不存在，构建默认 config 模块并注册到 sys.modules，
       使 llm_handler / vlm_handler 等模块可正常导入
    """
    if str(ALGORITHM_DIR) not in sys.path:
        sys.path.insert(0, str(ALGORITHM_DIR))
    try:
        import config  # noqa: F401
    except ImportError:
        apply_to_config(load_settings())


_bootstrap()
