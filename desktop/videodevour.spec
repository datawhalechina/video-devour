# -*- mode: python ; coding: utf-8 -*-
"""
VideoDevour 桌面客户端打包配置（PyInstaller onedir）

构建：
    pyinstaller desktop/videodevour.spec --noconfirm

产物：
    dist/VideoDevour/            # 后端 + 壳 + 前端产物
    dist/VideoDevour.app         # macOS 应用包（在 build_mac.sh 中组装）

设计要点：
- onedir 模式（非 onefile）：onefile 每次启动解压到临时目录，首启慢且杀软误报率高
- 轻量依赖集合：不含 torch/funasr/modelscope/sentence-transformers
- 前端 dist 与 ffmpeg 二进制作为数据文件一并收集
"""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

PROJECT_ROOT = Path(SPECPATH).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
BIN_DIR = PROJECT_ROOT / "desktop" / "bin"

datas = []

# 前端构建产物：由后端同源托管
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
else:
    raise SystemExit(
        "缺少前端构建产物：请先执行 `cd frontend && npm run build`"
    )

# 捆绑的 ffmpeg/ffprobe（可选：不存在时回退系统 PATH）
if BIN_DIR.exists():
    for name in ("ffmpeg", "ffprobe"):
        candidate = BIN_DIR / (name + (".exe" if sys.platform.startswith("win") else ""))
        if candidate.exists():
            datas.append((str(candidate), "bin"))

# uvicorn / fastapi 的动态导入需要显式收集
hiddenimports = []
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("anyio")

# camel-ai 在运行期按 provider 动态导入模型后端
hiddenimports += collect_submodules("camel")

# tiktoken 的编码表通过 tiktoken_ext 动态发现（camel 用它做 token 计数）。
# 不显式收集会在运行期报 "Unknown encoding o200k_base"。
# tiktoken_ext 是命名空间包（__file__ 为 None），需用 find_spec 定位目录。
hiddenimports += collect_submodules("tiktoken_ext")
import importlib.util as _ilu
_spec = _ilu.find_spec("tiktoken_ext")
if _spec and _spec.submodule_search_locations:
    for _loc in _spec.submodule_search_locations:
        datas.append((_loc, "tiktoken_ext"))

# yt-dlp 的 extractor 也是动态加载
hiddenimports += collect_submodules("yt_dlp")

# reportlab：PDF 导出（backend/algorithm/pdf_export.py）在函数内被导入，
# PyInstaller 静态分析看不到，必须显式收集，否则运行时报
# ModuleNotFoundError: No module named 'reportlab'。
hiddenimports += collect_submodules("reportlab")
datas += collect_data_files("reportlab")

# 项目自身的后端模块：用文件系统枚举，不要依赖 collect_submodules。
# 原因：backend/、backend/algorithm/、backend/devour/ 都没有 __init__.py（隐式命名空间包），
# collect_submodules("backend") 只会返回 backend.api / backend.runtime 两个包下的模块
# （实测 5 个），algorithm 与 devour 下的模块一个都收不到。
# 之前能运行只是碰巧：PyInstaller 顺着入口的静态 import 链收到了大部分模块，
# 而仅被“函数内裸导入”引用的模块（如 vlm_handler）被静默漏掉，
# 表现为关键帧选择失败、报告无图。
def _iter_backend_modules():
    names = set()
    for py in (PROJECT_ROOT / "backend").rglob("*.py"):
        if py.name == "__init__.py":
            continue
        if py.name.startswith("test_") or py.name == "config.template.py":
            continue
        rel = py.relative_to(PROJECT_ROOT).with_suffix("")
        names.add(".".join(rel.parts))
    return sorted(names)


hiddenimports += _iter_backend_modules()
hiddenimports += collect_submodules("desktop")

# pywebview 在 macOS 下依赖 pyobjc WebKit 桥，需显式收集
hiddenimports += collect_submodules("webview")

datas += collect_data_files("yt_dlp")
datas += collect_data_files("webview")

block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / "desktop" / "app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 明确排除本地 ML 重依赖，避免误收集（轻量包）
    excludes=[
        "torch", "torchaudio", "funasr", "modelscope",
        "sentence_transformers", "moviepy", "soundfile",
        "matplotlib", "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VideoDevour",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # 必须 console=True：窗口模式（macOS 的 runw 引导器）不保留标准文件描述符，
    # uvicorn 启动后会静默退出（实测无任何错误日志）。后端是子进程，
    # 窗口可见性由桌面壳控制（Windows 用 CREATE_NO_WINDOW，macOS 无控制台窗口概念）。
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VideoDevour",
)
