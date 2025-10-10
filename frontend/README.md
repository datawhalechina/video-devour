# 🍽️ VideoDevour Frontend

基于 React + Vite 构建的 VideoDevour 智能视频分析工具前端界面。

## ✨ 功能特性

- 🎬 **视频上传**：支持拖拽上传，实时显示上传进度
- ⏳ **处理追踪**：实时显示视频处理状态和进度
- 📄 **报告查看**：查看图文并茂的视频分析报告（支持 Markdown 渲染）
- 📚 **历史记录**：管理和查看所有处理过的视频报告
- 🎨 **现代 UI**：美观的渐变色设计，流畅的动画效果
- 📱 **响应式设计**：完美适配桌面端和移动端

## 🛠️ 技术栈

- **框架**：React 18
- **构建工具**：Vite 5
- **样式方案**：Tailwind CSS 3
- **动画库**：Framer Motion
- **HTTP 客户端**：Axios
- **Markdown 渲染**：react-markdown
- **图标库**：lucide-react

## 📦 安装与运行

### 前置要求

- Node.js >= 18.0.0
- npm 或 yarn

### 安装依赖

\`\`\`bash
npm install

# 或

yarn
\`\`\`

### 启动开发服务器

\`\`\`bash
npm run dev

# 或

yarn dev
\`\`\`

服务器将在 http://localhost:3000 启动

### 构建生产版本

\`\`\`bash
npm run build

# 或

yarn build
\`\`\`

构建输出将保存在 `dist` 目录

### 预览生产版本

\`\`\`bash
npm run preview

# 或

yarn preview
\`\`\`

## 🔧 配置

### 后端 API 地址

在 `vite.config.js` 中配置后端 API 代理：

\`\`\`javascript
export default defineConfig({
server: {
proxy: {
'/api': {
target: 'http://localhost:8000', // 修改为你的后端地址
changeOrigin: true,
}
}
}
})
\`\`\`

## 📂 项目结构

\`\`\`
video-react/
├── public/ # 静态资源
├── src/
│ ├── api/ # API 服务层
│ │ ├── videoService.js # 视频相关 API
│ │ └── mockData.js # 模拟数据（开发用）
│ ├── components/ # React 组件
│ │ ├── Header.jsx # 头部导航
│ │ ├── VideoUpload.jsx # 视频上传组件
│ │ ├── ProcessingStatus.jsx # 处理状态显示
│ │ ├── ReportViewer.jsx # 报告查看器
│ │ └── HistoryList.jsx # 历史记录列表
│ ├── App.jsx # 主应用组件
│ ├── main.jsx # 应用入口
│ └── index.css # 全局样式
├── index.html # HTML 模板
├── vite.config.js # Vite 配置
├── tailwind.config.js # Tailwind 配置
└── package.json # 项目依赖
\`\`\`

## 🎨 主要组件说明

### VideoUpload

视频上传组件，支持：

- 拖拽上传
- 点击选择文件
- 文件格式验证
- 上传进度显示

### ProcessingStatus

处理状态组件，实时显示：

- 当前处理阶段
- 总体进度百分比
- 已用时间
- 各阶段完成状态

### ReportViewer

报告查看组件，提供：

- 图文大纲和精简报告切换
- Markdown 格式渲染
- 报告下载功能
- 相关文件管理

### HistoryList

历史记录组件，支持：

- 查看所有处理记录
- 快速访问已完成报告
- 删除历史记录

## 🔌 后端 API 接口

前端需要对接以下后端 API：

### 1. 上传视频

\`\`\`
POST /api/video/upload
Content-Type: multipart/form-data
Body: { video: File }

Response: {
taskId: string,
message: string
}
\`\`\`

### 2. 获取任务状态

\`\`\`
GET /api/task/{taskId}/status

Response: {
stage: string, // uploading, extracting_audio, asr, generating_outline, etc.
progress: number, // 0-100
message: string,
error: string | null
}
\`\`\`

### 3. 获取历史记录

\`\`\`
GET /api/history

Response: [{
id: string,
videoName: string,
createdAt: string,
duration: string,
status: string,
description: string
}]
\`\`\`

### 4. 删除报告

\`\`\`
DELETE /api/report/{reportId}

Response: {
success: boolean,
message: string
}
\`\`\`

### 5. 下载文件

\`\`\`
GET /api/report/{reportId}/download/{type}
Type: detailed | final | video | image

Response: Blob
\`\`\`

## 🎯 后续开发建议

### 与 video-devour 后端集成

1. **在后端项目中添加 FastAPI 服务**

在 video-devour 项目中创建 `backend/api/` 目录，实现 REST API：

\`\`\`python

# backend/api/main.py

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 配置 CORS

app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:3000"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

@app.post("/api/video/upload")
async def upload_video(video: UploadFile = File(...)): # 调用 videodevour.py 的处理逻辑
pass

@app.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str): # 返回任务处理状态
pass
\`\`\`

2. **启动后端服务**

\`\`\`bash
cd backend
uvicorn api.main:app --reload --port 8000
\`\`\`

3. **同时运行前后端**

终端 1：
\`\`\`bash
cd backend
uvicorn api.main:app --reload
\`\`\`

终端 2：
\`\`\`bash
cd frontend
npm run dev
\`\`\`

### 功能增强建议

- [ ] 添加用户认证系统
- [ ] 支持批量视频上传
- [ ] 添加视频预览功能
- [ ] 实现报告在线编辑
- [ ] 支持自定义处理参数
- [ ] 添加导出多种格式（PDF、Word 等）
- [ ] 实现实时协作功能

## 📝 开发注意事项

1. **开发模式下使用模拟数据**：在 `src/api/videoService.js` 中可以切换到模拟数据进行开发
2. **样式定制**：在 `tailwind.config.js` 中修改主题配置
3. **代码规范**：使用 ESLint 进行代码检查
4. **图片资源**：静态图片放在 `public` 目录

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [video-devour 后端项目](https://github.com/Hoshino-wind/video-devour)
- [React 文档](https://react.dev/)
- [Vite 文档](https://vitejs.dev/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
