# 后端集成指南

本文档说明如何将此前端项目与 video-devour 后端进行集成。

## 📁 推荐项目结构

建议将前后端整合为一个完整项目：

```
video-devour/
├── backend/                # Python 后端
│   ├── algorithm/          # 核心算法（已有）
│   ├── devour/             # ASR 引擎（已有）
│   ├── api/                # 新增：FastAPI 服务
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI 应用
│   │   ├── routes/         # API 路由
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务逻辑
│   └── requirements.txt
├── frontend/               # React 前端（本项目）
│   ├── src/
│   ├── public/
│   └── package.json
├── output/                 # 处理结果输出
├── models/                 # AI 模型文件
└── README.md
```

## 🔧 后端 API 实现

### 1. 安装 FastAPI 依赖

```bash
cd backend
pip install fastapi uvicorn python-multipart aiofiles
```

### 2. 创建 FastAPI 应用

**backend/api/main.py**：

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import shutil
from pathlib import Path
from typing import List
import asyncio

app = FastAPI(title="VideoDevour API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置路径
UPLOAD_DIR = Path("../output/uploads")
OUTPUT_DIR = Path("../output/reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 存储处理任务状态
processing_tasks = {}

@app.get("/")
def read_root():
    return {"message": "VideoDevour API is running"}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """上传视频文件"""
    try:
        # 生成唯一 ID
        video_id = str(uuid.uuid4())

        # 保存文件
        file_path = UPLOAD_DIR / f"{video_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 初始化处理状态
        processing_tasks[video_id] = {
            "status": "pending",
            "progress": 0,
            "filename": file.filename
        }

        # 启动后台处理任务
        asyncio.create_task(process_video(video_id, file_path))

        return {
            "videoId": video_id,
            "filename": file.filename,
            "status": "pending"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_video(video_id: str, file_path: Path):
    """后台处理视频"""
    try:
        # 更新状态：开始处理
        processing_tasks[video_id]["status"] = "processing"
        processing_tasks[video_id]["progress"] = 10

        # TODO: 调用你的核心算法处理视频
        # 这里需要集成你的 algorithm 和 devour 模块

        # 示例：模拟处理过程
        for progress in range(20, 100, 20):
            await asyncio.sleep(2)  # 模拟处理时间
            processing_tasks[video_id]["progress"] = progress

        # TODO: 生成报告（调用你的报告生成逻辑）
        report_path = OUTPUT_DIR / f"{video_id}_report.md"

        # 示例：生成简单报告
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# 视频分析报告\n\n")
            f.write(f"**视频ID**: {video_id}\n\n")
            f.write(f"**处理时间**: {datetime.now()}\n\n")
            f.write(f"## 分析结果\n\n处理完成！")

        # 更新状态：完成
        processing_tasks[video_id]["status"] = "completed"
        processing_tasks[video_id]["progress"] = 100
        processing_tasks[video_id]["reportPath"] = str(report_path)

    except Exception as e:
        processing_tasks[video_id]["status"] = "failed"
        processing_tasks[video_id]["error"] = str(e)

@app.get("/api/status/{video_id}")
def get_processing_status(video_id: str):
    """获取处理状态"""
    if video_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Video not found")

    return processing_tasks[video_id]

@app.get("/api/report/{video_id}")
def get_report(video_id: str):
    """获取报告内容"""
    if video_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Video not found")

    task = processing_tasks[video_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Report not ready")

    report_path = Path(task["reportPath"])
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "videoId": video_id,
        "content": content,
        "filename": task["filename"]
    }

@app.get("/api/history")
def get_history():
    """获取历史记录"""
    history = []
    for video_id, task in processing_tasks.items():
        if task["status"] == "completed":
            history.append({
                "id": video_id,
                "filename": task["filename"],
                "status": task["status"],
                "createdAt": "2024-10-10"  # TODO: 添加实际时间戳
            })
    return history

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. 集成现有算法

在 `process_video` 函数中集成你的核心算法：

```python
from algorithm import VideoAnalyzer  # 导入你的算法模块
from devour import ASREngine        # 导入 ASR 引擎

async def process_video(video_id: str, file_path: Path):
    try:
        processing_tasks[video_id]["status"] = "processing"

        # 1. ASR 语音识别
        processing_tasks[video_id]["progress"] = 20
        asr = ASREngine()
        transcript = await asr.transcribe(str(file_path))

        # 2. 视频分析
        processing_tasks[video_id]["progress"] = 50
        analyzer = VideoAnalyzer()
        analysis = await analyzer.analyze(str(file_path), transcript)

        # 3. 生成报告
        processing_tasks[video_id]["progress"] = 80
        report = generate_report(analysis)

        # 保存报告
        report_path = OUTPUT_DIR / f"{video_id}_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        processing_tasks[video_id]["status"] = "completed"
        processing_tasks[video_id]["progress"] = 100
        processing_tasks[video_id]["reportPath"] = str(report_path)

    except Exception as e:
        processing_tasks[video_id]["status"] = "failed"
        processing_tasks[video_id]["error"] = str(e)
```

## 🔗 前端配置

### 1. 更新 API 地址

修改前端 `src/api/videoService.js`：

```javascript
const API_BASE_URL = "http://localhost:8000/api"; // 指向 FastAPI 后端

export const uploadVideo = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      );
      onProgress?.(percentCompleted);
    },
  });

  return response.data;
};

export const checkProcessingStatus = async (videoId) => {
  const response = await axios.get(`${API_BASE_URL}/status/${videoId}`);
  return response.data;
};

export const getReport = async (videoId) => {
  const response = await axios.get(`${API_BASE_URL}/report/${videoId}`);
  return response.data;
};

export const getHistory = async () => {
  const response = await axios.get(`${API_BASE_URL}/history`);
  return response.data;
};
```

## 🚀 启动项目

### 1. 启动后端

```bash
cd backend/api
python main.py
```

后端将在 http://localhost:8000 运行

### 2. 启动前端

```bash
cd frontend
npm run dev
```

前端将在 http://localhost:5173 运行

### 3. 测试 API

访问 http://localhost:8000/docs 查看自动生成的 API 文档（Swagger UI）

## 📝 数据库集成（可选）

如果需要持久化存储，可以添加数据库支持：

### 使用 SQLite

```bash
pip install sqlalchemy
```

**backend/api/database.py**：

```python
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./videodevour.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True)
    filename = Column(String)
    status = Column(String)
    progress = Column(Integer, default=0)
    report_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(bind=engine)
```

## 🔒 生产环境配置

### 1. 环境变量

创建 `.env` 文件：

```env
# API 配置
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,https://your-domain.com

# 文件路径
UPLOAD_DIR=../output/uploads
OUTPUT_DIR=../output/reports

# 数据库
DATABASE_URL=sqlite:///./videodevour.db

# 安全
SECRET_KEY=your-secret-key-here
```

### 2. 使用 Gunicorn 部署

```bash
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 3. Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

## 📚 更多资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React + Vite 部署指南](https://vitejs.dev/guide/static-deploy.html)
- [CORS 配置说明](https://fastapi.tiangolo.com/tutorial/cors/)

## ❓ 常见问题

### Q: CORS 错误怎么办？

确保后端的 CORS 配置包含了前端地址：

```python
allow_origins=["http://localhost:5173"]
```

### Q: 如何处理大文件上传？

可以配置更大的上传限制：

```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_request_size=1024 * 1024 * 1024  # 1GB
)
```

### Q: 如何实现进度实时推送？

可以使用 WebSocket：

```python
from fastapi import WebSocket

@app.websocket("/ws/{video_id}")
async def websocket_endpoint(websocket: WebSocket, video_id: str):
    await websocket.accept()
    while True:
        if video_id in processing_tasks:
            await websocket.send_json(processing_tasks[video_id])
        await asyncio.sleep(1)
```
