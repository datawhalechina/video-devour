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

### macOS（arm64 / x86_64 双架构）

两个架构必须用**各自架构的 Python** 构建（PyInstaller 的输出架构由解释器决定）。

```bash
# 1. 依赖环境
#    arm64（Apple Silicon 本机）
uv venv .venv-lite --python 3.12
uv pip install --python .venv-lite/bin/python -r requirements-lite.txt pyinstaller pywebview

#    x86_64（Intel；在 Apple Silicon 上经 uv 安装 x86_64 Python）
uv python install cpython-3.12.13-macos-x86_64-none
uv venv .venv-x64 --python cpython-3.12.13-macos-x86_64-none
uv pip install --python .venv-x64/bin/python -r requirements-lite.txt pyinstaller pywebview

# 2. 静态 ffmpeg/ffprobe（按架构分目录存放，双架构可共存）
./desktop/fetch_binaries.sh --all-macos

# 3. 前端（两架构共用）
cd frontend && npm run build && cd ..

# 4. 打包
PYTHON_ARM64=.venv-lite/bin/python ./desktop/build_mac.sh --arm64 --sign
PYTHON_X64=.venv-x64/bin/python   ./desktop/build_mac.sh --x64 --sign
# 或一次构建两个架构：./desktop/build_mac.sh --both --sign

# 5. 运行
open desktop/dist/arm64/VideoDevour.app   # Apple Silicon
open desktop/dist/x64/VideoDevour.app     # Intel
```

产物分别在 `desktop/dist/arm64/` 与 `desktop/dist/x64/`。

内测被 Gatekeeper 拦截时：`xattr -cr '<app 路径>'`（**仅限内测**，正式分发需公证）。

> **不要用 `--universal2`**：torch 等依赖不做 universal2，且本包依赖的二进制 wheel
> 各有架构限制，`lipo` 合并不可行。

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
