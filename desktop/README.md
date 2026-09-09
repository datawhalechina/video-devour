# VideoDevour 桌面客户端

桌面壳（pywebview）+ 本地 FastAPI 后端（PyInstaller onedir）的客户端形态。
设计依据与阶段规划见 [../planning/桌面客户端化方案.md](../planning/桌面客户端化方案.md)。

## 当前形态：轻量包

只包含**字幕速记**与**在线 ASR 图文报告**两条链路，**不含** torch / funasr / modelscope /
sentence-transformers。本地 ASR 与本地语义匹配属后续增强（阶段 E）。

> ⚠️ 轻量包 ≠ 完全离线：报告生成仍调用 LLM/VLM 云端服务，部分可视化依赖 CDN。

## 目录

```
desktop/
├── app.py                  # 统一入口（双角色）
├── shell.py                # 桌面壳：窗口、单实例、进程守护、原生桥
├── backend_server.py       # 后端：端口握手、uvicorn 启动
├── videodevour.spec        # PyInstaller 配置（onedir）
├── build_mac.sh            # macOS 构建 + .app 组装 + 签名
├── build_win.ps1           # Windows 构建 + 安装包
├── installer.iss           # Inno Setup 安装包配置
├── fetch_binaries.sh       # 下载静态 ffmpeg/ffprobe
└── bin/                    # 捆绑二进制（构建时生成，不入库）
```

## 构建

### macOS（arm64）

```bash
# 1. 轻量依赖
uv venv .venv-lite --python 3.12
uv pip install --python .venv-lite/bin/python -r requirements-lite.txt pyinstaller pywebview

# 2. 静态 ffmpeg/ffprobe
./desktop/fetch_binaries.sh

# 3. 前端
cd frontend && npm run build && cd ..

# 4. 打包
PYTHON=.venv-lite/bin/python ./desktop/build_mac.sh --sign

# 5. 运行
open desktop/dist/VideoDevour.app
```

内测被 Gatekeeper 拦截时：`xattr -cr desktop/dist/VideoDevour.app`（**仅限内测**，正式分发需公证）。

### Windows（x64）

```powershell
python -m pip install -r requirements-lite.txt pyinstaller pywebview
bash desktop/fetch_binaries.sh windows    # 或手动放置 ffmpeg.exe/ffprobe.exe
cd frontend && npm run build && cd ..
powershell -ExecutionPolicy Bypass -File desktop/build_win.ps1
```

安装包需 Inno Setup 6（`winget install JRSoftware.InnoSetup`）。

### CI

`.github/workflows/desktop-build.yml` 在 macOS-14 与 windows-latest 上各自构建并做冒烟测试。

## 运行时目录

| 平台 | 数据目录 |
|------|---------|
| macOS | `~/Library/Application Support/VideoDevour` |
| Windows | `%LOCALAPPDATA%\VideoDevour` |
| 开发模式 | 项目根（行为不变） |

可用 `VIDEO_DEVOUR_DATA_DIR` 覆盖。存放：`settings.json`、`tasks.json`、`uploads/`、`output/`、`logs/`。

## 开发调试

```bash
# 只跑后端（源码模式，自动分配端口）
python desktop/backend_server.py --data-dir /tmp/vd-dev --frontend-dist frontend/dist

# 跑壳（源码模式）
VIDEO_DEVOUR_DATA_DIR=/tmp/vd-dev python desktop/shell.py
```

## 已知限制

- 仅 macOS arm64 完成实测；Windows 需 CI 验证
- 中文输入法、拖放、睡眠/唤醒、网络切换未验证
- 未实现本地会话鉴权（方案 4.2 要求，阶段 B2）
- 任务仍为内存态 + JSON，无队列与真实阶段事件（阶段 B3/B4）
- 仅 ad-hoc 签名，正式分发需开发者证书 + 公证
