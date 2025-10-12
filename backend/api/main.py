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
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.algorithm.pipeline import run_full_pipeline

# 创建FastAPI应用
app = FastAPI(
    title="VideoDevour API",
    description="视频处理和分析服务",
    version="1.0.0"
)

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

@app.post("/api/video/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    上传视频文件并开始处理
    """
    try:
        # 检查文件是否存在
        if not file.filename:
            raise HTTPException(status_code=400, detail="未选择文件")
        
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
            "created_at": datetime.now().isoformat()
        }
        
        # 保存任务数据
        save_tasks()
        
        # 启动后台处理任务并存储任务引用
        task = asyncio.create_task(process_video_async(task_id, file_path))
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

async def process_video_async(task_id: str, file_path: Path):
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
        result = await run_pipeline_with_progress(str(file_path), task_id)
        
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

async def run_pipeline_with_progress(video_path: str, task_id: str):
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
            future = executor.submit(run_full_pipeline, video_path)
            
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