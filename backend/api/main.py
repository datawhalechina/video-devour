# -*- coding: utf-8 -*-
"""
FastAPI 后端服务
提供视频上传、处理状态查询等 API 接口
"""

import os
import sys
import uuid
import shutil
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from urllib.parse import quote
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# settings_store 先于 pipeline 导入：负责引导 config 模块（config.py 缺失时自动构建）
from backend.algorithm import settings_store
settings_store.apply_to_config()

from backend.algorithm import report_viz
from backend.algorithm.pipeline import run_full_pipeline

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 创建FastAPI应用
app = FastAPI(
    title="VideoDevour API",
    description="视频处理和分析服务",
    version="1.0.0"
)
asr_engine = None

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置目录
UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "output"

# 挂载静态文件服务，用于访问output目录中的图片
app.mount("/static", StaticFiles(directory=str(OUTPUT_DIR)), name="static")
TASKS_FILE = PROJECT_ROOT / "tasks.json"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 内存中的任务存储
processing_tasks: Dict[str, Dict] = {}
running_tasks: Dict[str, asyncio.Task] = {}  # 存储正在运行的异步任务

def load_tasks():
    """从文件加载任务数据"""
    global processing_tasks
    if TASKS_FILE.exists():
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                processing_tasks = json.load(f)
        except Exception as e:
            print(f"加载任务文件失败: {e}")
            processing_tasks = {}
    else:
        processing_tasks = {}
    # 服务重启后，内存中的处理协程已不存在：
    # 把遗留的 pending/processing/downloading 任务标记为失败，避免历史页出现永久"处理中"的僵尸任务
    for task in processing_tasks.values():
        if task.get("status") in ("pending", "processing", "downloading"):
            task.update({
                "status": "failed",
                "stage": "error",
                "progress": 0,
                "message": "服务重启导致任务中断",
                "error": task.get("error") or "服务重启导致任务中断，请重新提交",
            })

def save_tasks():
    """保存任务数据到文件"""
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(processing_tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存任务文件失败: {e}")

# 启动时加载任务数据（遗留的未完成任务标记为中断并持久化）
load_tasks()
save_tasks()

@app.on_event("startup")
async def startup_event():
    """
    按 ASR 模式初始化引擎：
    - offline: 预加载本地 Paraformer 模型
    - online:  无需预加载，启动即用（任务时通过 DashScope 云端调用）
    """
    global asr_engine
    settings_store.apply_to_config()
    mode = settings_store.load_settings().get("asr_mode", "offline")
    if mode == "online":
        asr_engine = None
        logging.info("当前为在线 ASR 模式（DashScope），跳过本地模型预加载")
        return
    try:
        logging.info("正在预加载 ASR 模型...")
        from backend.devour.asr_factory import create_asr_engine
        asr_engine = create_asr_engine(mode="offline")
        _ = asr_engine.asr_model
        logging.info("ASR 模型预加载完成")
    except Exception as e:
        logging.error(f"ASR 模型预加载失败: {str(e)}")
        asr_engine = None

# 数据模型
class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    stage: str   # uploading, extracting_audio, asr, generating_outline, extracting_frames, vlm_analysis, generating_report, completed
    progress: int  # 0-100
    message: str
    filename: Optional[str] = None
    error: Optional[str] = None
    created_at: str

class UploadResponse(BaseModel):
    task_id: str
    message: str
    filename: str

@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "message": "VideoDevour API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# 设置控制台 API（离线/在线模式切换、API 配置、连通性测试）
# ---------------------------------------------------------------------------

class SettingsUpdateRequest(BaseModel):
    asr_mode: Optional[str] = None            # offline | online
    dashscope_api_key: Optional[str] = None
    online_asr_model: Optional[str] = None
    online_asr_provider: Optional[str] = None   # dashscope | stepfun
    stepfun_api_key: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_api_url: Optional[str] = None
    llm_model_type: Optional[str] = None
    llm_temperature: Optional[float] = None
    vlm_api_key: Optional[str] = None
    vlm_api_url: Optional[str] = None
    vlm_model_type: Optional[str] = None
    default_education_level: Optional[str] = None


class SettingsTestRequest(BaseModel):
    target: str = "all"  # asr | llm | vlm | all


@app.get("/api/settings")
async def get_app_settings():
    """获取当前设置（密钥脱敏）"""
    settings = settings_store.get_settings(mask=True)
    settings["education_levels"] = settings_store.EDUCATION_LEVELS
    return settings


@app.put("/api/settings")
async def update_app_settings(request: SettingsUpdateRequest):
    """
    更新设置并立即生效。

    - 设置会注入 config 模块并持久化到 settings.json
    - 切换到 online 模式时释放已预加载的本地模型
    - 切换到 offline 模式时后台预加载本地模型
    """
    global asr_engine
    dump = getattr(request, "model_dump", None) or request.dict
    updates = {k: v for k, v in dump().items() if v is not None}
    if updates.get("asr_mode") not in (None, "offline", "online"):
        raise HTTPException(status_code=400, detail="asr_mode 仅支持 offline 或 online")
    if updates.get("online_asr_provider") not in (None, "dashscope", "stepfun"):
        raise HTTPException(status_code=400, detail="online_asr_provider 仅支持 dashscope 或 stepfun")
    if updates.get("default_education_level") not in (None,) + tuple(settings_store.EDUCATION_LEVELS):
        raise HTTPException(status_code=400, detail="default_education_level 取值非法")

    old_mode = settings_store.load_settings().get("asr_mode", "offline")
    settings = settings_store.update_settings(updates)
    new_mode = settings["asr_mode"]

    if new_mode != old_mode:
        asr_engine = None
        if new_mode == "offline":
            # 后台预加载本地模型，不阻塞请求
            def _preload():
                global asr_engine
                try:
                    from backend.devour.asr_factory import create_asr_engine
                    engine = create_asr_engine(mode="offline")
                    _ = engine.asr_model
                    asr_engine = engine
                    logging.info("离线 ASR 模型预加载完成")
                except Exception as e:
                    logging.error(f"离线 ASR 模型预加载失败: {e}")
            asyncio.get_event_loop().run_in_executor(None, _preload)
        else:
            logging.info("已切换为在线 ASR 模式，本地模型已释放")
    settings["education_levels"] = settings_store.EDUCATION_LEVELS
    return {"message": "设置已保存并生效", "settings": settings}


@app.post("/api/settings/test")
async def test_app_settings(request: SettingsTestRequest):
    """测试 API 连通性（asr: 在线语音识别 / llm / vlm）"""
    import concurrent.futures
    target = request.target if request.target in ("asr", "llm", "vlm", "all") else "all"
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = await loop.run_in_executor(executor, settings_store.run_tests, target)
    return {"results": results}


# ---------------------------------------------------------------------------
# 在线视频链接处理（Bilibili / YouTube，移植自 bilibili/youtube 下载工具）
# ---------------------------------------------------------------------------

class LinkInfoRequest(BaseModel):
    url: str


class LinkSearchRequest(BaseModel):
    query: str
    platform: str = "bilibili"   # bilibili | youtube
    max_results: int = 8


class LinkProcessRequest(BaseModel):
    url: str
    education_level: str = "自由学习"
    extras: List[str] = []       # 可选附加产物：mindmap / graph / card


class LinkNotesRequest(BaseModel):
    url: str
    education_level: str = "自由学习"


class BrowserCookieRequest(BaseModel):
    browser: str = ""   # 空 = 自动按序尝试（chrome/edge/firefox/safari/...）


# 任务完成后可选自动生成的附加产物（默认不生成，按需勾选，节省处理时间）
VALID_EXTRAS = {"mindmap", "graph", "card"}
EXTRA_LABELS = {"mindmap": "思维导图", "graph": "知识图谱", "card": "学习卡片"}


def _parse_extras(raw) -> List[str]:
    """解析并校验 extras（逗号分隔字符串或列表），去重保序"""
    if not raw:
        return []
    items = raw.split(",") if isinstance(raw, str) else list(raw)
    seen = []
    for item in items:
        item = (item or "").strip().lower()
        if item in VALID_EXTRAS and item not in seen:
            seen.append(item)
    return seen


async def _generate_extras(task_id: str, extras: List[str], education_level: str):
    """任务报告完成后按勾选顺序生成附加产物；单项失败不影响任务状态"""
    results = {}
    total = len(extras)
    for i, kind in enumerate(extras):
        label = EXTRA_LABELS[kind]
        processing_tasks[task_id].update({
            "stage": "generating_extras",
            "message": f"正在生成{label}...（{i + 1}/{total}）"
        })
        save_tasks()
        try:
            def _gen(kind=kind):
                output_dir = _find_task_output_dir(task_id)
                if not output_dir:
                    raise ValueError("未找到任务输出目录")
                if kind == "card":
                    return report_viz.generate_learning_card(output_dir, education_level)
                fn = report_viz.generate_mindmap if kind == "mindmap" else report_viz.generate_knowledge_graph
                return fn(output_dir, education_level)
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                path = await loop.run_in_executor(executor, _gen)
            results[kind] = {"ok": True, "path": str(path)}
        except Exception as e:
            logging.error(f"附加产物 {kind} 生成失败: {e}", exc_info=True)
            results[kind] = {"ok": False, "error": str(e)[:200]}
    return results


def _run_link_probe(handler, **kwargs):
    """在线程池中执行 yt-dlp 操作（网络阻塞型）"""
    import functools
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return loop.run_in_executor(executor, functools.partial(handler, **kwargs))


@app.post("/api/video/link/info")
async def get_link_info(request: LinkInfoRequest):
    """获取链接视频的元数据（不下载），用于预览确认。支持直接粘贴 App 分享文案"""
    from backend.devour.video_downloader import probe_video_info, extract_share_url
    url = extract_share_url(request.url or "")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请提供有效的视频链接")
    try:
        return await _run_link_probe(probe_video_info, url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"获取链接信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"获取视频信息失败: {e}")


@app.post("/api/video/link/search")
async def search_link_videos(request: LinkSearchRequest):
    """按关键词搜索 B站/YouTube 视频，返回预览卡片列表"""
    try:
        from backend.devour.video_downloader import search_videos
        return {"results": await _run_link_probe(
            search_videos,
            query=request.query,
            platform=request.platform,
            max_results=max(1, min(request.max_results, 15)),
        )}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"搜索失败: {e}")


@app.post("/api/video/link/notes")
async def generate_subtitle_notes(request: LinkNotesRequest):
    """
    字幕速记：直接用 B站/YouTube 已有字幕生成纯文本笔记（不下载视频、不走 ASR）
    """
    from backend.devour.video_downloader import detect_platform, extract_share_url
    url = extract_share_url(request.url or "")
    platform = detect_platform(url)
    if platform not in ("bilibili", "youtube"):
        raise HTTPException(status_code=400, detail="字幕笔记仅支持 B站 / YouTube 链接")
    if request.education_level not in settings_store.EDUCATION_LEVELS:
        raise HTTPException(status_code=400, detail=f"学习阶段仅支持: {'/'.join(settings_store.EDUCATION_LEVELS)}")

    try:
        from backend.devour.subtitles import generate_subtitle_notes
        return await _run_link_probe(
            generate_subtitle_notes, url=url, platform=platform,
            education_level=request.education_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"字幕笔记生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"字幕笔记生成失败: {e}")


@app.post("/api/settings/cookies/from-browser")
async def import_cookies_from_browser(request: BrowserCookieRequest):
    """
    一键读取本机浏览器中的 B站 / YouTube / 元宝登录 Cookie 并写入设置。

    仅读取三个目标域的 cookie，不接触浏览器中的其他数据；
    macOS 首次读取 Chrome/Edge 时会弹钥匙串授权，需点「允许」。
    """
    try:
        from backend.devour.browser_cookies import collect_target_cookies
        result = await _run_link_probe(collect_target_cookies, browser=request.browser)
    except Exception as e:
        logging.error(f"浏览器 Cookie 读取失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"读取浏览器 Cookie 失败: {e}")

    fields = result.get("fields") or {}
    if fields:
        settings_store.update_settings(fields)
    found = {k: bool(v) for k, v in fields.items()}
    labels = {"bilibili_sessdata": "B站 SESSDATA", "youtube_cookies": "YouTube cookies",
              "wechat_yuanbao_cookie": "元宝 Cookie"}
    hit = [labels[k] for k in fields if fields.get(k)]
    if hit:
        message = f"已从 {result.get('browser_used')} 读取并保存：{'、'.join(hit)}"
    elif result.get("browser_used"):
        message = f"已打开 {result.get('browser_used')} 的 cookie 库，但未找到目标站登录 cookie（可能未在浏览器登录）"
    else:
        message = "未能读取到浏览器 cookie（原因见读取明细）。请改用手动粘贴，或换一个浏览器重试"
    return {"browser_used": result.get("browser_used"), "found": found,
            "attempts": result.get("attempts") or [], "message": message}


@app.get("/api/video/link/youtube-check")
async def youtube_env_check():
    """
    YouTube 下载环境自检：yt-dlp 版本 / cookies / PO Token 脚本 / node 运行时，
    并给出下一步建议（供设置页与排障使用）
    """
    import shutil
    import subprocess

    checks: Dict = {}
    try:
        import yt_dlp
        checks["yt_dlp_version"] = yt_dlp.version.__version__
    except Exception:
        checks["yt_dlp_version"] = None

    cookies_text = (settings_store.load_settings().get("youtube_cookies") or "").strip()
    env_cookies = os.getenv("YTDLP_COOKIES_FILE")
    checks["cookies_configured"] = bool(
        (cookies_text and "youtube.com" in cookies_text.lower())
        or (env_cookies and os.path.exists(env_cookies))
    )

    from backend.devour.video_downloader import _bgutil_script_path, _youtube_js_runtime
    checks["pot_script"] = bool(_bgutil_script_path())

    # yt-dlp EJS：YouTube n challenge 求解脚本（yt-dlp[default] 自带）
    try:
        import importlib.metadata as _md
        checks["ejs_version"] = _md.version("yt-dlp-ejs")
    except Exception:
        checks["ejs_version"] = None

    checks["js_runtime"] = _youtube_js_runtime()

    node = shutil.which("node")
    checks["node_available"] = bool(node)
    checks["node_version"] = None
    if node:
        try:
            proc = await asyncio.to_thread(
                subprocess.run, [node, "--version"], capture_output=True,
                text=True, timeout=10)
            checks["node_version"] = (proc.stdout or "").strip()
        except Exception:
            pass

    suggestions = []
    if not checks["cookies_configured"]:
        suggestions.append("未配置 YouTube cookies：可在本卡片点「一键读取浏览器 Cookie」，"
                           "或手动粘贴浏览器导出的 cookies.txt")
    if not checks["ejs_version"]:
        suggestions.append("缺少 yt-dlp EJS 求解脚本：执行 uv sync（或 pip install -U \"yt-dlp[default]\"）")
    if not checks["js_runtime"]:
        suggestions.append("缺少 JS 运行时：安装 Deno（推荐）或 Node ≥22，用于解 YouTube 的 n challenge")
    if not checks["pot_script"]:
        suggestions.append("未安装 PO Token 支持：在项目目录执行 bash scripts/install_yt_pot.sh（需要 node）")
    if checks["pot_script"] and not checks["node_available"]:
        suggestions.append("已安装 PO Token 脚本但缺少 node 运行时：请安装 node")
    if checks["cookies_configured"] and checks["ejs_version"] and checks["js_runtime"]:
        suggestions.append("环境已就绪。若仍报错，尝试更换网络/代理节点后重试")
    return {"checks": checks, "suggestions": suggestions}


@app.post("/api/video/link", response_model=UploadResponse)
async def process_link_video(request: LinkProcessRequest):
    """
    通过链接一键下载并处理视频（B站/YouTube/微信视频号）。

    流程：yt-dlp 或解析服务下载到 uploads/{task_id}.mp4 → 复用现有处理 pipeline
    """
    from backend.devour.video_downloader import extract_share_url
    url = extract_share_url(request.url or "")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请提供有效的视频链接")
    if request.education_level not in settings_store.EDUCATION_LEVELS:
        raise HTTPException(status_code=400, detail=f"学习阶段仅支持: {'/'.join(settings_store.EDUCATION_LEVELS)}")
    extras_list = _parse_extras(request.extras)

    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}.mp4"

    processing_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "stage": "downloading",
        "progress": 0,
        "message": "等待下载视频...",
        "filename": url,
        "file_path": str(file_path),
        "source_url": url,
        "education_level": request.education_level,
        "extras": extras_list,
        "created_at": datetime.now().isoformat(),
    }
    save_tasks()

    task = asyncio.create_task(
        _download_and_process(task_id, url, file_path, request.education_level, extras_list)
    )
    running_tasks[task_id] = task

    return UploadResponse(task_id=task_id, message="链接任务已创建，开始下载", filename=url)


async def _download_and_process(task_id: str, url: str, file_path: Path, education_level: str,
                                extras: List[str] = None):
    """下载链接视频后接续标准处理流程"""
    try:
        def _hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                done = d.get("downloaded_bytes", 0)
                if total:
                    processing_tasks[task_id]["progress"] = min(15, int(15 * done / total))
                processing_tasks[task_id]["message"] = f"正在下载视频... {done / 1024 / 1024:.1f}MB"
                save_tasks()

        processing_tasks[task_id].update({"status": "processing", "message": "正在下载视频..."})
        save_tasks()

        from backend.devour.video_downloader import download_video
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: download_video(url, str(UPLOAD_DIR), progress_hook=_hook)
        )
        downloaded_path = Path(result["file_path"])
        if downloaded_path.resolve() != file_path.resolve():
            if downloaded_path.suffix.lower() == ".mp4":
                downloaded_path.replace(file_path)
            else:
                # 非 mp4 容器（如 webm/vp9）转码为 mp4，copy 失败时回退到重编码
                import subprocess
                proc = subprocess.run(
                    ["ffmpeg", "-y", "-i", str(downloaded_path), "-c", "copy", str(file_path)],
                    capture_output=True,
                )
                if proc.returncode != 0:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(downloaded_path),
                         "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", str(file_path)],
                        check=True, capture_output=True,
                    )
                downloaded_path.unlink()

        info = result.get("info", {})
        processing_tasks[task_id].update({
            "filename": info.get("title") or url,
            "message": "下载完成，开始处理",
        })
        save_tasks()

        # 清理下载占位文件后接续标准流程
        await process_video_async(task_id, file_path, education_level, extras)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logging.error(f"链接任务失败: {e}", exc_info=True)
        processing_tasks[task_id].update({
            "status": "failed",
            "stage": "error",
            "progress": 0,
            "message": "下载或处理失败",
            "error": str(e),
        })
        save_tasks()

@app.post("/api/video/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...), education_level: str = Form("自由学习"),
                       extras: str = Form("")):
    """
    上传视频文件并开始处理

    education_level: 学习阶段（小学/初中/高中），影响大纲与报告的语言风格
    extras: 逗号分隔的可选附加产物（mindmap/graph/card），完成后自动生成
    """
    extras_list = _parse_extras(extras)
    try:
        # 检查文件是否存在
        if not file.filename:
            raise HTTPException(status_code=400, detail="未选择文件")

        if education_level not in settings_store.EDUCATION_LEVELS:
            raise HTTPException(status_code=400, detail=f"学习阶段仅支持: {'/'.join(settings_store.EDUCATION_LEVELS)}")
        
        # 检查文件扩展名（更宽松的验证）
        file_extension = Path(file.filename).suffix.lower()
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        
        if file_extension not in video_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_extension}。支持的格式: {', '.join(video_extensions)}")
        
        # 生成唯一任务 ID
        task_id = str(uuid.uuid4())
        
        # 处理重复文件名，类似微信的命名方式
        original_name = Path(file.filename).stem  # 不包含扩展名的文件名
        display_filename = file.filename
        
        # 检查是否存在同名文件（基于原始文件名）
        existing_files = []
        for existing_task_id, task_data in processing_tasks.items():
            if task_data.get("filename"):
                existing_name = Path(task_data["filename"]).stem
                if existing_name.startswith(original_name):
                    existing_files.append(task_data["filename"])
        
        # 如果存在同名文件，添加数字后缀
        if existing_files:
            # 找出已存在的最大后缀数字
            max_suffix = 0
            for existing_file in existing_files:
                existing_stem = Path(existing_file).stem
                if existing_stem == original_name:
                    max_suffix = max(max_suffix, 1)
                elif existing_stem.startswith(f"{original_name}(") and existing_stem.endswith(")"):
                    try:
                        suffix_part = existing_stem[len(original_name)+1:-1]
                        if suffix_part.isdigit():
                            max_suffix = max(max_suffix, int(suffix_part))
                    except:
                        pass
            
            # 生成新的显示文件名
            if max_suffix > 0:
                display_filename = f"{original_name}({max_suffix + 1}){file_extension}"
        
        # 保存上传的文件（仍使用task_id作为实际文件名）
        saved_filename = f"{task_id}{file_extension}"
        file_path = UPLOAD_DIR / saved_filename
        
        # 读取并保存文件内容
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # 初始化任务状态
        processing_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "stage": "uploading",
            "progress": 0,
            "message": "文件上传完成，等待处理",
            "filename": display_filename,  # 使用处理后的显示文件名
            "file_path": str(file_path),
            "education_level": education_level,
            "extras": extras_list,
            "created_at": datetime.now().isoformat()
        }

        # 保存任务数据
        save_tasks()

        # 启动后台处理任务并存储任务引用
        task = asyncio.create_task(process_video_async(task_id, file_path, education_level, extras_list))
        running_tasks[task_id] = task
        
        return UploadResponse(
            task_id=task_id,
            message="文件上传成功，开始处理",
            filename=display_filename  # 返回处理后的显示文件名
        )
        
    except HTTPException as he:
        # 重新抛出 HTTP 异常，保持原始状态码
        raise he
    except Exception as e:
        # 记录详细错误信息
        import traceback
        error_details = traceback.format_exc()
        print(f"Upload error: {error_details}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/api/task/{task_id}/timing")
async def get_task_timing(task_id: str):
    """
    获取任务的阶段/函数耗时报告（timing_report.json + 汇总摘要）。
    用于定位性能瓶颈，任务目录下也会落盘同名文件。
    """
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在或尚未生成输出目录")
    report_path = output_dir / "timing_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="该任务尚无耗时报告（可能未完成或为旧任务）")
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"耗时报告解析失败: {e}")
    summary = (data or {}).get("summary") or {}
    return {
        "task_id": task_id,
        "output_dir": output_dir.name,
        "summary": summary,
        "top_slowest": summary.get("phases", [])[:15],
        "timing_url": f"/static/{output_dir.name}/timing_summary.txt",
    }


@app.get("/api/task/{task_id}/status", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    获取任务处理状态
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = processing_tasks[task_id]
    return TaskStatus(**task)

@app.get("/api/task/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务处理结果，从output目录读取
    """
    # 查找输出文件
    output_files = []
    
    # 查找以frames_开头包含task_id的目录（pipeline生成的实际输出）
    for dir_path in OUTPUT_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"frames_{task_id}"):
            # 检查是否有final_report.md文件来判断任务状态
            final_report_path = dir_path / "final_report.md"
            if not final_report_path.exists():
                raise HTTPException(status_code=400, detail="任务尚未完成")
            
            # 收集所有文件
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    output_files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(OUTPUT_DIR)),
                        "size": file_path.stat().st_size
                    })
            break
    else:
        # 如果没找到frames目录，检查是否有以task_id命名的目录
        task_output_dir = OUTPUT_DIR / task_id
        if task_output_dir.exists():
            for file_path in task_output_dir.rglob("*"):
                if file_path.is_file():
                    output_files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(OUTPUT_DIR)),
                        "size": file_path.stat().st_size
                    })
        else:
            raise HTTPException(status_code=404, detail="任务结果不存在")
    
    return {
        "task_id": task_id,
        "status": "completed",
        "files": output_files
    }

@app.get("/api/download/{task_id}/{filename}")
async def download_file(task_id: str, filename: str):
    """
    下载处理结果文件
    """
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    file_path = OUTPUT_DIR / task_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/api/task/{task_id}/report")
async def get_task_report(task_id: str):
    """
    获取任务的详细报告内容，包括视频时长、图文大纲和精简报告
    """
    # 查找输出目录
    output_dir = None
    
    # 查找以frames_开头包含task_id的目录
    for dir_path in OUTPUT_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"frames_{task_id}"):
            output_dir = dir_path
            break
    
    if not output_dir:
        # 如果没找到frames目录，检查是否有以task_id命名的目录
        task_output_dir = OUTPUT_DIR / task_id
        if task_output_dir.exists():
            output_dir = task_output_dir
        else:
            raise HTTPException(status_code=404, detail="报告不存在")
    
    # 读取报告文件
    detailed_outline_path = output_dir / "detailed_outline.md"
    final_report_path = output_dir / "final_report.md"
    detailed_report_path = output_dir / "detailed_report.md"

    detailed_outline = ""
    final_report = ""
    detailed_report = ""
    duration = "未知"
    video_name = "未知视频"
    
    # 读取图文大纲
    if detailed_outline_path.exists():
        try:
            with open(detailed_outline_path, 'r', encoding='utf-8') as f:
                detailed_outline = f.read()
        except Exception as e:
            print(f"读取详细大纲失败: {e}")
    
    # 读取精简报告
    if final_report_path.exists():
        try:
            with open(final_report_path, 'r', encoding='utf-8') as f:
                final_report = f.read()
        except Exception as e:
            print(f"读取最终报告失败: {e}")

    # 读取详细报告（原文+笔记对照）
    if detailed_report_path.exists():
        try:
            with open(detailed_report_path, 'r', encoding='utf-8') as f:
                detailed_report = f.read()
        except Exception as e:
            print(f"读取详细报告失败: {e}")
    
    # 优先从任务数据获取原始文件名
    if task_id in processing_tasks:
        original_filename = processing_tasks[task_id].get('filename', '')
        if original_filename:
            video_name = Path(original_filename).stem
    
    # 读取视频时长信息
    asr_files = list(output_dir.glob("*_asr_result.json"))
    if asr_files:
        try:
            with open(asr_files[0], 'r', encoding='utf-8') as f:
                asr_data = json.load(f)
                if asr_data and len(asr_data) > 0:
                    transcript = asr_data[0].get('transcript', [])
                    if transcript:
                        # 获取最后一个片段的结束时间作为视频总时长
                        last_segment = transcript[-1]
                        total_seconds = last_segment.get('end_time', 0)
                        
                        # 格式化时长为 MM:SS 或 HH:MM:SS
                        if total_seconds >= 3600:  # 超过1小时
                            hours = int(total_seconds // 3600)
                            minutes = int((total_seconds % 3600) // 60)
                            seconds = int(total_seconds % 60)
                            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        else:
                            minutes = int(total_seconds // 60)
                            seconds = int(total_seconds % 60)
                            duration = f"{minutes:02d}:{seconds:02d}"
                    
                    # 如果任务数据中没有获取到文件名，尝试从video_path获取文件名（备用方案）
                    if video_name == "未知视频":
                        video_path = asr_data[0].get('video_path', '')
                        if video_path:
                            video_name = Path(video_path).stem
        except Exception as e:
            print(f"读取ASR结果失败: {e}")
    
    # 获取创建时间
    created_at = datetime.fromtimestamp(output_dir.stat().st_ctime).isoformat()
    
    # 来源链接（链接任务才有）：用于报告页展示原渠道
    source_url = ""
    platform = ""
    task_record = processing_tasks.get(task_id) or {}
    source_url = task_record.get("source_url") or ""
    if source_url:
        try:
            from backend.devour.video_downloader import detect_platform
            platform = detect_platform(source_url)
        except Exception:
            platform = "other"

    return {
        "task_id": task_id,
        "video_name": video_name,
        "duration": duration,
        "detailed_outline": detailed_outline,
        "final_report": final_report,
        "detailed_report": detailed_report,
        "output_dir": output_dir.name,  # 添加输出目录名称
        "created_at": created_at,
        "source_url": source_url,
        "platform": platform,
        "status": "completed" if (detailed_outline or final_report) else "processing"
    }

@app.get("/api/reports/{task_id}/{file_type}")
async def get_report_file(task_id: str, file_type: str):
    """
    获取单个报告文件内容（用于编辑器）
    file_type: 'detailed' 或 'final'
    """
    # 查找输出目录
    output_dir = None
    
    # 查找以frames_开头包含task_id的目录
    for dir_path in OUTPUT_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"frames_{task_id}"):
            output_dir = dir_path
            break
    
    if not output_dir:
        # 如果没找到frames目录，检查是否有以task_id命名的目录
        task_output_dir = OUTPUT_DIR / task_id
        if task_output_dir.exists():
            output_dir = task_output_dir
        else:
            raise HTTPException(status_code=404, detail="报告不存在")
    
    # 根据文件类型确定文件路径
    if file_type == "detailed":
        file_path = output_dir / "detailed_outline.md"
    elif file_type == "final":
        file_path = output_dir / "final_report.md"
    elif file_type == "detailed_report":
        file_path = output_dir / "detailed_report.md"
    else:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 附带输出目录名：编辑器预览需要拼接相对路径图片的静态地址
        return {"content": content, "output_dir": output_dir.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

@app.put("/api/reports/{task_id}/{file_type}")
async def save_report_file(task_id: str, file_type: str, request: dict):
    """
    保存单个报告文件内容（用于编辑器）
    file_type: 'detailed' 或 'final'
    """
    # 查找输出目录
    output_dir = None
    
    # 查找以frames_开头包含task_id的目录
    for dir_path in OUTPUT_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"frames_{task_id}"):
            output_dir = dir_path
            break
    
    if not output_dir:
        # 如果没找到frames目录，检查是否有以task_id命名的目录
        task_output_dir = OUTPUT_DIR / task_id
        if task_output_dir.exists():
            output_dir = task_output_dir
        else:
            raise HTTPException(status_code=404, detail="报告不存在")
    
    # 根据文件类型确定文件路径
    if file_type == "detailed":
        file_path = output_dir / "detailed_outline.md"
    elif file_type == "final":
        file_path = output_dir / "final_report.md"
    elif file_type == "detailed_report":
        file_path = output_dir / "detailed_report.md"
    else:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    try:
        content = request.get("content", "")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {"message": "保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")


# ---------------------------------------------------------------------------
# 学习卡片与 Markdown 导出（移植自 light 版核心功能）
# ---------------------------------------------------------------------------

def _find_task_output_dir(task_id: str):
    """查找任务的输出目录（pipeline 生成的 frames_{task_id}_* 目录）"""
    for dir_path in OUTPUT_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(f"frames_{task_id}"):
            return dir_path
    task_output_dir = OUTPUT_DIR / task_id
    if task_output_dir.exists():
        return task_output_dir
    return None


def _get_task_education_level(task_id: str, default: str = "高中") -> str:
    task = processing_tasks.get(task_id, {})
    return task.get("education_level") or default


@app.post("/api/task/{task_id}/card")
async def generate_task_card(task_id: str):
    """
    根据任务的最终报告生成学习卡片HTML（结果缓存到任务目录，生成逻辑见 report_viz）
    """
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在或尚未完成")

    cached = (output_dir / "learning_card.html").exists()
    education_level = _get_task_education_level(task_id)

    def _generate():
        return report_viz.generate_learning_card(output_dir, education_level)

    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        card_path = await loop.run_in_executor(executor, _generate)

    return {"html": card_path.read_text(encoding="utf-8"), "cached": cached}


# --- 思维导图与知识图谱（生成逻辑见 backend/algorithm/report_viz.py） ---


async def _viz_html(task_id: str, kind: str) -> dict:
    """生成或读取缓存的知识可视化 HTML（mindmap / knowledge-graph 共用）"""
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在或尚未完成")

    education_level = _get_task_education_level(task_id)
    cache_name = "mindmap.html" if kind == "mindmap" else "knowledge_graph.html"
    cached = (output_dir / cache_name).exists()

    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = loop.run_in_executor(
            executor,
            report_viz.generate_mindmap if kind == "mindmap" else report_viz.generate_knowledge_graph,
            output_dir, education_level,
        )
        try:
            # 必须 await：run_in_executor 返回 asyncio Future，
            # 同步调用 result() 会在未完成时抛 InvalidStateError("Result is not set.")
            path = await future
        except ValueError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            logging.error(f"知识可视化生成失败({kind}): {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=str(e))

    return {"html": Path(path).read_text(encoding="utf-8"), "cached": cached}


@app.post("/api/task/{task_id}/mindmap")
async def generate_task_mindmap(task_id: str):
    """生成课程思维导图（markmap HTML，结果缓存到任务目录）"""
    return await _viz_html(task_id, "mindmap")


@app.get("/api/task/{task_id}/mindmap")
async def get_task_mindmap(task_id: str):
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在")
    cache = output_dir / "mindmap.html"
    if not cache.exists():
        raise HTTPException(status_code=404, detail="思维导图尚未生成")
    return {"html": cache.read_text(encoding="utf-8"), "cached": True}


@app.post("/api/task/{task_id}/knowledge-graph")
async def generate_task_knowledge_graph(task_id: str):
    """生成课程知识图谱（ECharts 力导向图 HTML，结果缓存到任务目录）"""
    return await _viz_html(task_id, "graph")


@app.get("/api/task/{task_id}/knowledge-graph")
async def get_task_knowledge_graph(task_id: str):
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在")
    cache = output_dir / "knowledge_graph.html"
    if not cache.exists():
        raise HTTPException(status_code=404, detail="知识图谱尚未生成")
    return {"html": cache.read_text(encoding="utf-8"), "cached": True}


@app.get("/api/task/{task_id}/card")
async def get_task_card(task_id: str):
    """获取已生成的学习卡片HTML"""
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在")
    card_path = output_dir / "learning_card.html"
    if not card_path.exists():
        raise HTTPException(status_code=404, detail="学习卡片尚未生成")
    return {"html": card_path.read_text(encoding="utf-8"), "cached": True}


@app.get("/api/export/{task_id}")
async def export_task_markdown(task_id: str, type: str = "all", mode: str = "inline"):
    """
    导出任务的 Markdown。

    type: outline（图文大纲）/ report（精简报告）/ detailed（详细报告）/ all（全部合并）
    mode: inline（图片内嵌，单文件可移植）/ zip（md + 原图打包，查看器 100% 兼容）

    说明：base64 内嵌会让单行超长（25KB+），部分查看器会截断导致图片显示失败，
    因此内嵌模式会把图片压缩到 800px 内、单张控制在约 8KB；追求原图质量用 zip 模式。
    """
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在")

    outline_path = output_dir / "detailed_outline.md"
    if not outline_path.exists():
        outline_path = output_dir / "outline.md"
    report_path = output_dir / "final_report.md"
    detailed_report_path = output_dir / "detailed_report.md"

    if not outline_path.exists() and not report_path.exists() and not detailed_report_path.exists():
        raise HTTPException(status_code=400, detail="任务尚未完成，无可导出的内容")

    def _read(path):
        return path.read_text(encoding="utf-8") if path.exists() else ""

    import base64
    import io
    import mimetypes
    import re

    # 内嵌模式的目标：单张 base64 尽量 ≤ 8KB（约 6KB 二进制），
    # 否则单行超长会被部分 Markdown 查看器截断导致图片不显示
    _INLINE_TARGET_BYTES = 6 * 1024

    def _compress_image(img_path) -> tuple:
        """把图片压缩到目标体积内（逐档降质量/降分辨率），返回 (mime, bytes)"""
        try:
            from PIL import Image
            img = Image.open(img_path)
            img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
            # 先按最长边 640 缩放，再逐档降质量；仍超标则继续缩小分辨率
            for max_side in (640, 480, 360, 280):
                work = img.copy()
                if max(work.size) > max_side:
                    work.thumbnail((max_side, max_side), Image.LANCZOS)
                for quality in (70, 60, 50, 40):
                    buf = io.BytesIO()
                    work.save(buf, format="JPEG", quality=quality, optimize=True)
                    data = buf.getvalue()
                    if len(data) <= _INLINE_TARGET_BYTES:
                        return "image/jpeg", data
            # 兜底：返回最后一次压缩结果（体积最小）
            return "image/jpeg", data
        except Exception as e:
            logging.warning(f"图片压缩失败，使用原图 {img_path.name}: {e}")
            mime = mimetypes.guess_type(str(img_path))[0] or "image/jpeg"
            return mime, img_path.read_bytes()

    def _resolve(rel_path: str):
        rel_path = rel_path.replace("\\", "/").lstrip("./")
        p = output_dir / rel_path
        return p if p.exists() else None

    def _embed_local_images(md_text: str) -> str:
        """把本地相对路径图片压缩后内嵌为 base64（控制单行长度）"""
        def _replace(match):
            alt, rel_path = match.group(1), match.group(2)
            img_path = _resolve(rel_path)
            if not img_path:
                return match.group(0)
            mime, data = _compress_image(img_path)
            return f"![{alt}](data:{mime};base64,{base64.b64encode(data).decode('ascii')})"

        return re.sub(r"!\[([^\]]*)\]\((?!https?://|data:)([^)]+)\)", _replace, md_text)

    # 组装内容
    outline_content = _read(outline_path)
    report_content = _read(report_path)
    detailed_content = _read(detailed_report_path)

    if type == "detailed":
        if not detailed_content:
            raise HTTPException(status_code=400, detail="该任务没有详细报告")
        parts, base_name = [detailed_content], f"详细报告_{task_id[:8]}"
    elif type == "outline":
        if not outline_content:
            raise HTTPException(status_code=400, detail="该任务没有图文大纲")
        parts, base_name = [outline_content], f"图文大纲_{task_id[:8]}"
    elif type == "report":
        if not report_content:
            raise HTTPException(status_code=400, detail="该任务没有精简报告")
        parts, base_name = [report_content], f"精简报告_{task_id[:8]}"
    else:
        parts = []
        if outline_content:
            parts.append(f"# 内容大纲\n\n{outline_content}")
        if report_content:
            parts.append(f"# 详细报告\n\n{report_content}")
        if detailed_content:
            parts.append(f"# 原文对照报告\n\n{detailed_content}")
        base_name = f"videodevour_{task_id[:8]}"

    from urllib.parse import quote

    # ---------- ZIP 模式：md 用相对路径 + 原图一起打包 ----------
    if mode == "zip":
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{base_name}.md", "\n\n---\n\n".join(parts))
            kf_dir = output_dir / "keyframes"
            if kf_dir.exists():
                for img in sorted(kf_dir.iterdir()):
                    if img.is_file():
                        zf.write(img, f"keyframes/{img.name}")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition":
                     f"attachment; filename=\"export.zip\"; "
                     f"filename*=UTF-8''{quote(base_name + '.zip')}"},
        )

    # ---------- 内嵌模式：压缩后 base64 内嵌，单文件 ----------
    content = "\n\n---\n\n".join(_embed_local_images(x) for x in parts)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition":
                 f"attachment; filename=\"videodevour.md\"; "
                 f"filename*=UTF-8''{quote(base_name + '.md')}"},
    )

@app.get("/api/subtitle-notes/download")
async def download_subtitle_notes(name: str, fmt: str = "md"):
    """
    下载字幕笔记（md / txt）。用专用端点而非直接指向 /static，
    以确保 Content-Disposition 正确、中文文件名不乱码。
    """
    from urllib.parse import quote
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="非法的文件名")
    fmt = "md" if fmt == "md" else "txt"
    path = OUTPUT_DIR / "subtitle_notes" / f"{name}.{fmt}"
    if not path.exists():
        raise HTTPException(status_code=404, detail="笔记文件不存在")
    media = "text/markdown" if fmt == "md" else "text/plain"
    # Content-Disposition 头只能是 latin-1：ASCII 回退名 + RFC 5987 UTF-8 名
    ascii_name = f"subtitle_notes.{fmt}"
    utf8_name = quote(f"{name}.{fmt}")
    return Response(
        content=path.read_bytes(),
        media_type=f"{media}; charset=utf-8",
        headers={"Content-Disposition":
                 f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}"},
    )


@app.get("/api/library/search")
async def library_search(q: str = "", scope: str = "all", top_k: int = 10):
    """
    个人文档库检索：BM25 相关度排序，返回 top-k 命中（标题/类型/摘要/分数/来源）。
    q 为空时返回全部文档索引。
    """
    from backend.algorithm.document_library import search_library, list_library
    if scope not in ("all", "outline", "report", "detailed"):
        raise HTTPException(status_code=400, detail="scope 仅支持 all/outline/report/detailed")
    try:
        if (q or "").strip():
            return await _run_link_probe(search_library, query=q, scope=scope, top_k=max(1, min(top_k, 30)))
        return await _run_link_probe(list_library, scope=scope)
    except Exception as e:
        logging.error(f"文档库检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"检索失败: {e}")


@app.get("/api/library/article/{doc_id}/{scope}")
async def library_get_article(doc_id: str, scope: str):
    """获取单篇文章全文（Markdown），供前端全文预览与 LLM/MCP 取用"""
    from backend.algorithm.document_library import get_article
    result = await _run_link_probe(get_article, doc_id=doc_id, scope=scope)
    if not result:
        raise HTTPException(status_code=404, detail="文章不存在")
    doc = result["doc"]
    return {
        "doc_id": doc_id,
        "scope": scope,
        "label": result["label"],
        "title": doc["title"],
        "platform": doc["platform"],
        "platform_label": doc["platform_label"],
        "source_url": doc["source_url"],
        "output_dir": doc["dir"],
        "content": result["content"],
        "download_url": f"/api/library/article/{doc_id}/{scope}/download",
    }


@app.get("/api/library/article/{doc_id}/{scope}/download")
async def library_download_article(doc_id: str, scope: str):
    """单篇文章下载（.md，附 Content-Disposition）"""
    from urllib.parse import quote
    from backend.algorithm.document_library import get_article, ARTICLE_TYPES
    if scope not in ARTICLE_TYPES:
        raise HTTPException(status_code=400, detail="不支持的文档类型")
    result = await _run_link_probe(get_article, doc_id=doc_id, scope=scope)
    if not result:
        raise HTTPException(status_code=404, detail="文章不存在")

    content = result["content"]
    doc = result["doc"]
    output_dir = OUTPUT_DIR / doc["dir"]
    label = ARTICLE_TYPES[scope][1]

    # 把 Markdown 里的本地相对路径图片内嵌为 base64：
    # 单独下载的 .md 脱离了任务的 keyframes 目录，不内嵌图片会全部裂开
    import base64
    import mimetypes as _mimetypes
    import re as _re

    def _embed(match):
        alt, rel_path = match.group(1), match.group(2)
        rel_path = rel_path.replace("\\", "/").lstrip("./")
        img_path = output_dir / rel_path
        if not img_path.exists():
            return match.group(0)
        mime = _mimetypes.guess_type(str(img_path))[0] or "image/jpeg"
        data = base64.b64encode(img_path.read_bytes()).decode("ascii")
        return f"![{alt}](data:{mime};base64,{data})"

    content = _re.sub(r"!\[([^\]]*)\]\((?!https?://|data:)([^)]+)\)", _embed, content)

    safe_title = _re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9_-]+", "_", doc["title"])[:40] or "article"
    filename = quote(f"{safe_title}_{label}.md")
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition":
                 f"attachment; filename=\"export.md\"; filename*=UTF-8''{filename}"},
    )


@app.get("/api/library/export")
async def library_export_all():
    """整库导出：全部任务的文档（md）+ 关键帧 + manifest.json 打包 ZIP"""
    from backend.algorithm.document_library import export_library_zip
    content, filename = await _run_link_probe(export_library_zip)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition":
                 f"attachment; filename=\"library.zip\"; filename*=UTF-8''{quote(filename)}"},
    )


@app.get("/api/history")
async def get_history():
    """
    获取处理历史记录，从output目录读取
    """
    history = []
    seen_task_ids = set()

    # 扫描output目录中的frames_开头的文件夹
    for dir_path in OUTPUT_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith("frames_"):
            try:
                # 解析目录名获取task_id和时间戳
                # 格式: frames_{task_id}_{timestamp}
                parts = dir_path.name.split("_")
                if len(parts) >= 3:
                    task_id = parts[1]
                    seen_task_ids.add(task_id)
                    timestamp_str = "_".join(parts[2:])

                    # 获取目录创建时间
                    created_at = datetime.fromtimestamp(dir_path.stat().st_ctime).isoformat()

                    # 检查是否有final_report.md文件来判断状态
                    final_report_path = dir_path / "final_report.md"
                    detailed_outline_path = dir_path / "detailed_outline.md"
                    task_state = processing_tasks.get(task_id) or {}

                    # 如果有任一报告文件且内容不为空，则认为已完成
                    status = "processing"
                    if final_report_path.exists() and final_report_path.stat().st_size > 0:
                        status = "completed"
                    elif detailed_outline_path.exists() and detailed_outline_path.stat().st_size > 0:
                        status = "completed"
                    elif task_state.get("status") == "completed":
                        # 管线声称完成但目录缺报告：历史遗留的失败任务
                        status = "failed"
                        task_state["message"] = "处理失败，报告未生成"

                    # 实时任务状态优先（下载/处理中的真实进度与阶段消息）
                    if task_state.get("status") in ("pending", "processing", "downloading"):
                        status = "processing"
                    elif task_state.get("status") == "failed":
                        status = "failed"
                    progress = task_state.get("progress") if status == "processing" else (
                        100 if status == "completed" else 0)
                    message = task_state.get("message") or ""

                    # 优先从processing_tasks中获取文件名
                    filename = "unknown"
                    if task_id in processing_tasks and processing_tasks[task_id].get("filename"):
                        filename = processing_tasks[task_id]["filename"]
                    else:
                        # 备用方案：从ASR结果文件获取原始文件名
                        asr_files = list(dir_path.glob("*_asr_result.json"))
                        if asr_files:
                            asr_filename = asr_files[0].name
                            # 从ASR文件名提取原始文件名
                            filename_part = asr_filename.replace("_asr_result.json", "")
                            if filename_part != task_id:
                                filename = f"{filename_part}.mp4"
                            else:
                                filename = f"{task_id}.mp4"

                    history.append({
                        "task_id": task_id,
                        "filename": filename,
                        "status": status,
                        "progress": progress,
                        "message": message,
                        "created_at": created_at
                    })
            except Exception as e:
                print(f"解析目录 {dir_path.name} 时出错: {e}")
                continue

    # 补充尚未生成输出目录的活动任务（如链接任务仍在下载阶段）
    for task_id, task in processing_tasks.items():
        if task_id in seen_task_ids:
            continue
        if task.get("status") in ("pending", "processing", "downloading"):
            history.append({
                "task_id": task_id,
                "filename": task.get("filename") or task_id,
                "status": "processing",
                "progress": task.get("progress") or 0,
                "message": task.get("message") or "",
                "created_at": task.get("created_at") or datetime.now().isoformat()
            })
    
    # 按创建时间倒序排列
    history.sort(key=lambda x: x["created_at"], reverse=True)
    
    return history

@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务和相关文件，并取消正在运行的处理进程
    """
    try:
        # 检查任务是否存在 - 从output目录或processing_tasks中查找
        task_exists = False
        
        # 首先检查是否在processing_tasks中（正在处理的任务）
        if task_id in processing_tasks:
            task_exists = True
            task = processing_tasks[task_id]
            
            # 取消正在运行的异步任务
            if task_id in running_tasks:
                running_task = running_tasks[task_id]
                if not running_task.done():
                    print(f"正在取消任务 {task_id}...")
                    running_task.cancel()
                    try:
                        await running_task
                    except asyncio.CancelledError:
                        print(f"任务 {task_id} 已被成功取消")
                    except Exception as e:
                        print(f"取消任务 {task_id} 时发生错误: {e}")
                del running_tasks[task_id]
            
            # 删除上传的文件
            if "file_path" in task:
                try:
                    file_path = Path(task["file_path"])
                    if file_path.exists():
                        file_path.unlink()
                        print(f"已删除上传文件: {file_path}")
                except Exception as e:
                    print(f"删除上传文件时出错: {e}")
            
            # 从任务列表中删除
            del processing_tasks[task_id]
            save_tasks()
        
        # 删除uploads目录中所有相关的文件（以task_id开头的文件）
        upload_files_to_delete = []
        try:
            for file_path in UPLOAD_DIR.iterdir():
                if file_path.is_file() and file_path.stem.startswith(task_id):
                    upload_files_to_delete.append(file_path)
                    task_exists = True
        except Exception as e:
            print(f"扫描上传目录时出错: {e}")
        
        for file_path in upload_files_to_delete:
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"已删除上传文件: {file_path}")
            except Exception as e:
                print(f"删除上传文件 {file_path} 时出错: {e}")
        
        # 检查output目录中是否存在相关文件
        output_dirs_to_delete = []
        
        try:
            # 查找frames_开头的目录
            for dir_path in OUTPUT_DIR.iterdir():
                if dir_path.is_dir() and dir_path.name.startswith("frames_"):
                    parts = dir_path.name.split("_")
                    if len(parts) >= 2 and parts[1] == task_id:
                        output_dirs_to_delete.append(dir_path)
                        task_exists = True
            
            # 查找直接以task_id命名的目录
            task_output_dir = OUTPUT_DIR / task_id
            if task_output_dir.exists():
                output_dirs_to_delete.append(task_output_dir)
                task_exists = True
        except Exception as e:
            print(f"扫描输出目录时出错: {e}")
        
        if not task_exists:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 删除所有相关的输出目录
        for dir_path in output_dirs_to_delete:
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    print(f"已删除目录: {dir_path}")
            except Exception as e:
                print(f"删除目录 {dir_path} 时出错: {e}")
        
        return {"message": "任务已删除"}
    
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"删除任务 {task_id} 时发生未知错误: {e}")
        raise HTTPException(status_code=500, detail=f"删除任务时发生错误: {str(e)}")

async def process_video_async(task_id: str, file_path: Path, education_level: str = None,
                              extras: List[str] = None):
    """
    异步处理视频文件（extras: 报告完成后可选生成的附加产物）
    """
    try:
        # 更新状态为处理中
        processing_tasks[task_id].update({
            "status": "processing",
            "stage": "extracting_audio",
            "progress": 10,
            "message": "开始处理视频..."
        })
        save_tasks()

        # 不创建额外的task_id目录，让pipeline自己创建frames_开头的目录

        # 调用核心处理流程
        processing_tasks[task_id].update({
            "stage": "asr",
            "progress": 20,
            "message": "正在进行语音识别..."
        })
        save_tasks()

        # 这里调用实际的处理函数
        # 注意：run_full_pipeline 可能需要修改以支持异步和进度回调
        result = await run_pipeline_with_progress(str(file_path), task_id, education_level)

        # 报告完成后按需生成附加产物（导图/图谱/卡片），未勾选则直接完成
        extras = extras or []
        extras_note = ""
        if extras:
            extras_results = await _generate_extras(task_id, extras, education_level)
            ok = [EXTRA_LABELS[k] for k, r in extras_results.items() if r["ok"]]
            failed = [EXTRA_LABELS[k] for k, r in extras_results.items() if not r["ok"]]
            if ok:
                extras_note = f"（含{'、'.join(ok)}）"
            if failed:
                extras_note += f"（{'、'.join(failed)}生成失败，可在报告页重试）"

        # 处理完成
        processing_tasks[task_id].update({
            "status": "completed",
            "stage": "completed",
            "progress": 100,
            "message": f"处理完成{extras_note}"
        })
        save_tasks()
        
    except asyncio.CancelledError:
        # 任务被取消
        processing_tasks[task_id].update({
            "status": "cancelled",
            "stage": "error",
            "progress": 0,
            "message": "任务已取消",
            "error": "任务被用户取消"
        })
        save_tasks()
    except Exception as e:
        # 处理失败
        processing_tasks[task_id].update({
            "status": "failed",
            "stage": "error",
            "progress": 0,
            "message": "处理失败",
            "error": str(e)
        })
        save_tasks()
        raise

async def run_pipeline_with_progress(video_path: str, task_id: str, education_level: str = None):
    """
    带进度更新的处理流程
    """
    def update_progress(progress: int, message: str, stage: str = None):
        if task_id in processing_tasks:
            update_data = {
                "progress": progress,
                "message": message
            }
            if stage:
                update_data["stage"] = stage
            processing_tasks[task_id].update(update_data)
            save_tasks()
    
    try:
        # 调用真实的处理流程
        update_progress(10, "初始化处理环境...", "uploading")
        await asyncio.sleep(0.5)
        
        update_progress(20, "开始语音识别...", "asr")
        await asyncio.sleep(0.5)
        
        # 在线程池中运行同步的 pipeline 函数
        import concurrent.futures
        loop = asyncio.get_event_loop()
        
        # 使用线程池执行器运行同步函数
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 在执行过程中定期更新进度
            future = executor.submit(run_full_pipeline, video_path, asr_engine, education_level)
            
            # 模拟进度更新
            progress_steps = [
                (30, "正在进行语音识别...", "asr"),
                (50, "处理ASR数据...", "generating_outline"),
                (60, "生成大纲...", "generating_outline"),
                (70, "匹配文本块...", "extracting_frames"),
                (80, "切分视频...", "extracting_frames"),
                (90, "处理图像帧...", "vlm_analysis"),
                (95, "生成最终报告...", "generating_report")
            ]
            
            for progress, message, stage in progress_steps:
                if not future.done():
                    update_progress(progress, message, stage)
                    await asyncio.sleep(2)  # 给处理一些时间
                else:
                    break
            
            # 等待处理完成
            result = await loop.run_in_executor(executor, lambda: future.result())
        
        update_progress(100, "处理完成", "completed")
        return {"success": True, "result": result}
        
    except Exception as e:
        update_progress(0, f"处理失败: {str(e)}", "error")
        raise e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )