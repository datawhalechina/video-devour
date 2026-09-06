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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# settings_store 先于 pipeline 导入：负责引导 config 模块（config.py 缺失时自动构建）
from backend.algorithm import settings_store
settings_store.apply_to_config()

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

def save_tasks():
    """保存任务数据到文件"""
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(processing_tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存任务文件失败: {e}")

# 启动时加载任务数据
load_tasks()

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


def _run_link_probe(handler, **kwargs):
    """在线程池中执行 yt-dlp 操作（网络阻塞型）"""
    import functools
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return loop.run_in_executor(executor, functools.partial(handler, **kwargs))


@app.post("/api/video/link/info")
async def get_link_info(request: LinkInfoRequest):
    """获取链接视频的元数据（不下载），用于预览确认"""
    url = (request.url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请提供有效的视频链接")
    try:
        from backend.devour.video_downloader import probe_video_info
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


@app.post("/api/video/link", response_model=UploadResponse)
async def process_link_video(request: LinkProcessRequest):
    """
    通过链接一键下载并处理视频（B站/YouTube）。

    流程：yt-dlp 下载到 uploads/{task_id}.mp4 → 复用现有处理 pipeline
    """
    url = (request.url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请提供有效的视频链接")
    if request.education_level not in settings_store.EDUCATION_LEVELS:
        raise HTTPException(status_code=400, detail=f"学习阶段仅支持: {'/'.join(settings_store.EDUCATION_LEVELS)}")

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
        "created_at": datetime.now().isoformat(),
    }
    save_tasks()

    task = asyncio.create_task(_download_and_process(task_id, url, file_path, request.education_level))
    running_tasks[task_id] = task

    return UploadResponse(task_id=task_id, message="链接任务已创建，开始下载", filename=url)


async def _download_and_process(task_id: str, url: str, file_path: Path, education_level: str):
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
        await process_video_async(task_id, file_path, education_level)
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
async def upload_video(file: UploadFile = File(...), education_level: str = Form("自由学习")):
    """
    上传视频文件并开始处理

    education_level: 学习阶段（小学/初中/高中），影响大纲与报告的语言风格
    """
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
            "created_at": datetime.now().isoformat()
        }

        # 保存任务数据
        save_tasks()

        # 启动后台处理任务并存储任务引用
        task = asyncio.create_task(process_video_async(task_id, file_path, education_level))
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
    
    detailed_outline = ""
    final_report = ""
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
    
    return {
        "task_id": task_id,
        "video_name": video_name,
        "duration": duration,
        "detailed_outline": detailed_outline,
        "final_report": final_report,
        "output_dir": output_dir.name,  # 添加输出目录名称
        "created_at": created_at,
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
    else:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content}
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


CARD_SYSTEM_PROMPT = (
    "你是一位专业的教育科技产品设计师与前端开发专家，擅长设计适合学生学习和复习的交互式学习卡片页面。"
    "你深谙学习心理学和认知科学原理，能够将复杂的学习内容转化为清晰、易记、视觉友好的学习卡片。"
    "注意只输出一段完整的HTML代码，不要输出任何其他内容。"
)

CARD_PROMPT_TEMPLATE = """请根据以下Markdown笔记内容，生成一个适合{level}学生学习的学习卡片HTML页面。

## 设计要求（必须严格遵守）
1. 页面为手机尺寸设计，卡片宽度写死 393px，提供完整的HTML文件代码，确保可以直接运行
2. 使用 Bento Grid 风格布局，柔和深色背景（#1a1a2e 或 #16213e），高亮色区分内容类型（#4CAF50重点、#FF9800提醒、#2196F3概念）
3. 通过 CDN 引入 TailwindCSS 3.0+ 和图标库（Font Awesome 或 Material Icons）
4. 核心知识点使用超大字体粗体突出，形成清晰的视觉层次
5. 使用图标或符号标记重点内容，关键概念使用卡片式设计
6. 【重要】必须完整保留笔记中的所有标题、要点和关键信息，不要遗漏任何内容
7. 【重要】只输出HTML代码，不要输出多段，不要包含解释文字

## 笔记内容
---
{notes}
---
"""

@app.post("/api/task/{task_id}/card")
async def generate_task_card(task_id: str):
    """
    根据任务的最终报告生成学习卡片HTML（结果缓存到任务目录）
    """
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在或尚未完成")

    card_path = output_dir / "learning_card.html"
    if card_path.exists():
        return {"html": card_path.read_text(encoding="utf-8"), "cached": True}

    report_path = output_dir / "final_report.md"
    if not report_path.exists():
        raise HTTPException(status_code=400, detail="任务尚未生成报告，无法生成学习卡片")

    notes = report_path.read_text(encoding="utf-8")
    if len(notes) > 24000:
        notes = notes[:24000] + "\n\n... (内容过长，已截取部分内容)"

    education_level = _get_task_education_level(task_id)

    def _generate():
        from backend.algorithm.llm_handler import LLMHandler
        llm = LLMHandler(education_level=education_level)
        prompt = CARD_PROMPT_TEMPLATE.format(level=education_level, notes=notes)
        html = llm.get_response(prompt, system_message=CARD_SYSTEM_PROMPT)
        # 清理 LLM 可能返回的 Markdown 代码块标记
        import re
        html = re.sub(r'^```html\s*|```$', '', html.strip(), flags=re.MULTILINE).strip()
        return html

    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        html = await loop.run_in_executor(executor, _generate)

    try:
        card_path.write_text(html, encoding="utf-8")
    except Exception as e:
        logging.warning(f"学习卡片缓存写入失败: {e}")

    return {"html": html, "cached": False}


# --- 思维导图（markmap 渲染）与知识图谱（ECharts 力导向图） ---

MINDMAP_SYSTEM_PROMPT = (
    "你是一位专业的知识架构师，擅长把课程内容整理成层级清晰的思维导图。"
    "只输出大纲本身，不要任何解释文字。"
)

MINDMAP_PROMPT_TEMPLATE = """请把以下课程报告整理为思维导图的层级大纲，用于 markmap 渲染。

要求：
1. 第一行为一级标题：# 课程中心主题（≤15字）
2. 用无序列表表达 3 层左右的分支结构（章节 → 核心要点 → 关键细节）
3. 每个节点不超过 20 字，保留关键术语与英文专有名词
4. 忠于原报告内容，不要新增报告之外的观点
5. 只输出 Markdown（标题+列表），不要 markdown 代码块标记

课程报告：
---
{report}
---
"""

KNOWLEDGE_GRAPH_SYSTEM_PROMPT = (
    "你是知识图谱构建专家，擅长从教学内容中抽取概念与关系。"
    "只输出严格的 JSON，不要 markdown 代码块标记，不要任何解释。"
)

KNOWLEDGE_GRAPH_PROMPT_TEMPLATE = """分析以下课程报告，构建知识图谱。

输出严格 JSON，结构如下：
{{
  "categories": ["类别1", "类别2", ...],
  "nodes": [{{"name": "概念名", "category": 0, "desc": "一句话说明"}}],
  "links": [{{"source": "概念A", "target": "概念B", "relation": "关系（≤8字）"}}]
}}

要求：
1. categories 为节点类别（如 核心概念 / 技术方法 / 应用场景 / 实践要点 等），3-5 个
2. nodes 8-16 个，覆盖报告的主要概念；category 为类别下标（从 0 开始）
3. links 10-20 条，关系准确、简明；source/target 必须是 nodes 中已有的 name
4. 使用简体中文

课程报告：
---
{report}
---
"""


def _read_report_text(output_dir: Path) -> str:
    report_path = output_dir / "final_report.md"
    if not report_path.exists():
        report_path = output_dir / "detailed_outline.md"
    if not report_path.exists():
        raise HTTPException(status_code=400, detail="任务尚未生成报告")
    text = report_path.read_text(encoding="utf-8")
    if len(text) > 20000:
        text = text[:20000] + "\n\n... (内容过长，已截取)"
    return text


def _run_llm_sync(education_level: str, system_prompt: str, prompt: str) -> str:
    from backend.algorithm.llm_handler import LLMHandler
    import re as _re
    llm = LLMHandler(education_level=education_level)
    out = llm.get_response(prompt, system_message=system_prompt)
    # 清理可能的 markdown 代码块包裹
    out = _re.sub(r"^```(?:html|markdown|json)?\s*|```$", "", out.strip(), flags=_re.MULTILINE).strip()
    return out


@app.post("/api/task/{task_id}/mindmap")
async def generate_task_mindmap(task_id: str):
    """生成课程思维导图（markmap HTML，结果缓存到任务目录）"""
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在或尚未完成")

    cache = output_dir / "mindmap.html"
    if cache.exists():
        return {"html": cache.read_text(encoding="utf-8"), "cached": True}

    report_text = _read_report_text(output_dir)
    education_level = _get_task_education_level(task_id)
    prompt = MINDMAP_PROMPT_TEMPLATE.format(report=report_text)

    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        md = await loop.run_in_executor(
            executor, _run_llm_sync, education_level, MINDMAP_SYSTEM_PROMPT, prompt
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>课程思维导图</title>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: #f8fafc; }}
  .markmap {{ position: absolute; inset: 0; }}
  .markmap > svg {{ width: 100%; height: 100%; }}
  .toolbar {{ position: fixed; top: 12px; left: 16px; z-index: 10;
    font: 14px/1.6 -apple-system, "PingFang SC", sans-serif; color: #334155; }}
  .toolbar small {{ color: #94a3b8; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script>
</head>
<body>
<div class="toolbar"><b>课程思维导图</b> <small>滚轮缩放 · 拖动平移 · 点击节点折叠</small></div>
<div class="markmap"><script type="text/template">
{md}
</script></div>
</body>
</html>"""

    try:
        cache.write_text(html, encoding="utf-8")
    except Exception as e:
        logging.warning(f"思维导图缓存写入失败: {e}")
    return {"html": html, "cached": False}


@app.get("/api/task/{task_id}/mindmap")
async def get_task_mindmap(task_id: str):
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在")
    cache = output_dir / "mindmap.html"
    if not cache.exists():
        raise HTTPException(status_code=404, detail="思维导图尚未生成")
    return {"html": cache.read_text(encoding="utf-8"), "cached": True}


KNOWLEDGE_GRAPH_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>课程知识图谱</title>
<style>
  html, body { margin: 0; padding: 0; height: 100%; background: #f8fafc; }
  /* 固定最小尺寸：后台/隐藏标签初始化时容器可能为 0，导致空白 */
  #graph { position: absolute; inset: 0; min-width: 1024px; min-height: 600px; }
  .toolbar { position: fixed; top: 12px; left: 16px; z-index: 10;
    font: 14px/1.6 -apple-system, "PingFang SC", sans-serif; color: #334155; }
  .toolbar small { color: #94a3b8; }
</style>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body>
<div class="toolbar"><b>课程知识图谱</b> <small>拖动平移 · 滚轮缩放 · 拖拽节点调整布局 · 悬停查看说明</small></div>
<div id="graph"></div>
<script>
const graphData = __GRAPH_DATA__;
const chart = echarts.init(document.getElementById('graph'));
const option = {
  backgroundColor: '#f8fafc',
  tooltip: {
    formatter: (p) => p.dataType === 'edge'
      ? (p.data.source + ' —[' + p.data.relation + ']→ ' + p.data.target)
      : (p.data.desc ? '<b>' + p.name + '</b><br/>' + p.data.desc : '<b>' + p.name + '</b>')
  },
  legend: {
    data: graphData.categories.map(c => c.name),
    top: 10, textStyle: { color: '#334155' }
  },
  series: [{
    type: 'graph', layout: 'force', roam: true,
    label: { show: true, fontSize: 12, color: '#0f172a' },
    edgeLabel: { show: true, fontSize: 10, color: '#64748b',
      formatter: (p) => p.data.relation || '' },
    edgeSymbol: ['none', 'arrow'], edgeSymbolSize: 8,
    lineStyle: { color: '#94a3b8', width: 1.5, curveness: 0.1 },
    force: { repulsion: 420, edgeLength: 130, gravity: 0.08 },
    emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
    categories: graphData.categories,
    data: graphData.nodes,
    links: graphData.links,
  }]
};
chart.setOption(option);
window.addEventListener('resize', () => chart.resize());
// 标签页从后台切换到前台时重新量取容器尺寸，避免空白
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) setTimeout(() => chart.resize(), 100);
});
</script>
</body>
</html>"""


@app.post("/api/task/{task_id}/knowledge-graph")
async def generate_task_knowledge_graph(task_id: str):
    """生成课程知识图谱（ECharts 力导向图 HTML，结果缓存到任务目录）"""
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在或尚未完成")

    cache = output_dir / "knowledge_graph.html"
    if cache.exists():
        return {"html": cache.read_text(encoding="utf-8"), "cached": True}

    report_text = _read_report_text(output_dir)
    education_level = _get_task_education_level(task_id)
    prompt = KNOWLEDGE_GRAPH_PROMPT_TEMPLATE.format(report=report_text)

    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        raw = await loop.run_in_executor(
            executor, _run_llm_sync, education_level, KNOWLEDGE_GRAPH_SYSTEM_PROMPT, prompt
        )

    # 容错解析 JSON（截取首个 { 到最后一个 }）
    import json as _json
    try:
        graph = _json.loads(raw)
    except _json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise HTTPException(status_code=502, detail="知识图谱 JSON 解析失败，请重试")
        graph = _json.loads(raw[start:end + 1])

    # 数据校验与兜底
    categories = [{"name": c} for c in graph.get("categories", [])] or [{"name": "概念"}]
    nodes = [
        {
            "name": n.get("name", f"节点{i}"),
            "category": min(int(n.get("category", 0)), len(categories) - 1),
            "desc": n.get("desc", ""),
            "symbolSize": 30 + min(len(graph.get("links", [])), 40) // 10,
        }
        for i, n in enumerate(graph.get("nodes", []))
    ]
    names = {n["name"] for n in nodes}
    links = [
        {"source": l["source"], "target": l["target"], "relation": l.get("relation", "关联")}
        for l in graph.get("links", [])
        if l.get("source") in names and l.get("target") in names and l["source"] != l["target"]
    ]
    if len(nodes) < 2 or not links:
        raise HTTPException(status_code=502, detail="知识图谱抽取结果过于稀疏，请重试")

    graph_data = {"categories": categories, "nodes": nodes, "links": links}
    html = KNOWLEDGE_GRAPH_TEMPLATE.replace(
        "__GRAPH_DATA__", json.dumps(graph_data, ensure_ascii=False)
    )

    try:
        cache.write_text(html, encoding="utf-8")
    except Exception as e:
        logging.warning(f"知识图谱缓存写入失败: {e}")
    return {"html": html, "cached": False}


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
async def export_task_markdown(task_id: str):
    """
    将任务的大纲与最终报告合并导出为单个 Markdown 文件
    """
    output_dir = _find_task_output_dir(task_id)
    if not output_dir:
        raise HTTPException(status_code=404, detail="任务不存在")

    outline_path = output_dir / "detailed_outline.md"
    if not outline_path.exists():
        outline_path = output_dir / "outline.md"
    report_path = output_dir / "final_report.md"

    if not outline_path.exists() and not report_path.exists():
        raise HTTPException(status_code=400, detail="任务尚未完成，无可导出的内容")

    def _read(path):
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _embed_local_images(md_text: str) -> str:
        """
        把 Markdown 中的本地相对路径图片（keyframes/xxx.jpg 等）内嵌为 base64，
        使导出的单个 .md 文件在任意本地查看器中都能直接显示图片。
        """
        import base64
        import mimetypes
        import re

        def _replace(match):
            alt, rel_path = match.group(1), match.group(2)
            rel_path = rel_path.replace("\\", "/").lstrip("./")
            img_path = output_dir / rel_path
            if not img_path.exists():
                return match.group(0)
            mime = mimetypes.guess_type(str(img_path))[0] or "image/jpeg"
            data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            return f"![{alt}](data:{mime};base64,{data})"

        return re.sub(r"!\[([^\]]*)\]\((?!https?://)([^)]+)\)", _replace, md_text)

    parts = []
    outline_content = _read(outline_path)
    report_content = _read(report_path)
    if outline_content:
        parts.append(f"# 内容大纲\n\n{_embed_local_images(outline_content)}")
    if report_content:
        parts.append(f"# 详细报告\n\n{_embed_local_images(report_content)}")
    full_content = "\n\n---\n\n".join(parts)

    filename = f"videodevour_{task_id[:8]}.md"
    return Response(
        content=full_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@app.get("/api/history")
async def get_history():
    """
    获取处理历史记录，从output目录读取
    """
    history = []
    
    # 扫描output目录中的frames_开头的文件夹
    for dir_path in OUTPUT_DIR.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith("frames_"):
            try:
                # 解析目录名获取task_id和时间戳
                # 格式: frames_{task_id}_{timestamp}
                parts = dir_path.name.split("_")
                if len(parts) >= 3:
                    task_id = parts[1]
                    timestamp_str = "_".join(parts[2:])
                    
                    # 获取目录创建时间
                    created_at = datetime.fromtimestamp(dir_path.stat().st_ctime).isoformat()
                    
                    # 检查是否有final_report.md文件来判断状态
                    final_report_path = dir_path / "final_report.md"
                    detailed_outline_path = dir_path / "detailed_outline.md"
                    
                    # 如果有任一报告文件且内容不为空，则认为已完成
                    status = "processing"
                    if final_report_path.exists() and final_report_path.stat().st_size > 0:
                        status = "completed"
                    elif detailed_outline_path.exists() and detailed_outline_path.stat().st_size > 0:
                        status = "completed"
                    
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
                        "progress": 100 if status == "completed" else 90,
                        "created_at": created_at
                    })
            except Exception as e:
                print(f"解析目录 {dir_path.name} 时出错: {e}")
                continue
    
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

async def process_video_async(task_id: str, file_path: Path, education_level: str = None):
    """
    异步处理视频文件
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
        
        # 处理完成
        processing_tasks[task_id].update({
            "status": "completed",
            "stage": "completed",
            "progress": 100,
            "message": "处理完成"
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