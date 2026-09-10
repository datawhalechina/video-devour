# -*- coding: utf-8 -*-
"""
运行时路径与外部二进制解析

桌面客户端打包后，程序所在目录只读、当前工作目录不可靠，因此所有"可写数据"
必须集中到统一的 data_root；外部二进制（ffmpeg/ffprobe）需按固定优先级查找。

路径优先级（B1 完整实现前的 A3 最小可用版本）：
    data_root = --data-dir / VIDEO_DEVOUR_DATA_DIR / 平台默认目录 / 源码根（开发模式）
    resource_root = PyInstaller 解包目录（冻结时） / 源码根

外部二进制查找顺序：
    1. 环境变量显式覆盖（VIDEO_DEVOUR_FFMPEG / VIDEO_DEVOUR_FFPROBE）
    2. 资源目录内捆绑的 bin/（打包分发）
    3. 系统 PATH
"""
import os
import shutil
import sys
import logging
from pathlib import Path

_APP_NAME = "VideoDevour"


def is_frozen() -> bool:
    """是否运行在 PyInstaller 冻结环境中。"""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """只读资源根目录：前端 dist、捆绑二进制、默认模板。"""
    if is_frozen():
        # onedir 模式下 _MEIPASS 指向解包目录
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent.parent


def source_root() -> Path:
    """源码根目录（开发模式下的项目根）。"""
    return Path(__file__).resolve().parent.parent.parent


def _platform_default_data_dir() -> Path:
    """按平台约定返回用户数据目录。"""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / _APP_NAME
    if sys.platform.startswith("win"):
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(home)
        return Path(base) / _APP_NAME
    return home / ".local" / "share" / _APP_NAME


def data_root() -> Path:
    """
    可写数据根目录：设置、任务、文档、上传、输出、日志、模型缓存。

    开发模式（未设置环境变量且未冻结）下沿用源码根，保持现有行为不变。
    """
    explicit = os.getenv("VIDEO_DEVOUR_DATA_DIR")
    if explicit:
        root = Path(explicit).expanduser()
    elif is_frozen():
        root = _platform_default_data_dir()
    else:
        root = source_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def subdir(name: str) -> Path:
    """data_root 下的子目录，确保存在。"""
    path = data_root() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# 外部二进制解析
# ---------------------------------------------------------------------------

def _resolve_binary(name: str, env_var: str) -> str:
    """
    按优先级解析外部二进制，返回绝对路径或裸名（交由系统 PATH 解析）。

    捆绑目录优先于 PATH，确保发行包不依赖用户环境。
    """
    override = os.getenv(env_var)
    if override and Path(override).exists():
        return override

    exe_name = f"{name}.exe" if sys.platform.startswith("win") else name
    bundled = resource_root() / "bin" / exe_name
    if bundled.exists():
        return str(bundled)

    found = shutil.which(name)
    if found:
        return found

    logging.warning(
        f"未找到 {name}：请安装后加入 PATH，或将其放入 {resource_root() / 'bin'}"
    )
    return name


def ffmpeg_path() -> str:
    return _resolve_binary("ffmpeg", "VIDEO_DEVOUR_FFMPEG")


def ffprobe_path() -> str:
    return _resolve_binary("ffprobe", "VIDEO_DEVOUR_FFPROBE")
