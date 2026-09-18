---
name: videodevour-desktop
description: VideoDevour 桌面客户端（macOS .app / Windows 安装包）的打包、签名、发版与热更新。当用户要求"打包客户端"、"构建/出安装包"、"发版/发布 release"、"实现热更新或自动更新"、"客户端装不上/打开报错/签名问题"时使用；也用于排查打包特有的故障——应用被判"已损坏"、功能在开发模式正常但客户端里失效、模块缺失（No module named ...）、下载没反应或白屏、进程残留、架构不匹配。
license: Apache-2.0
compatibility: 需要 macOS 构建机（macOS 版必须）；轻量依赖环境 .venv-lite(arm64) / .venv-x64(Intel)；Windows 包由 CI 构建，不能跨平台本地构建
---

# VideoDevour 桌面客户端：打包 · 发版 · 热更新

## Goal

维护 VideoDevour 的桌面客户端分发：本地/CI 构建 → 签名与校验 → 发布 Release → 组件热更新。

**核心事实**：客户端是 PyInstaller onedir 冻结包 + pywebview 壳，**与开发模式的行为差异极大**——
大量 bug 只在冻结环境出现。任何"开发模式正常"都不能作为客户端可用的证据。

## 硬约束（踩过坑，务必先读）

| # | 约束 | 违反的后果 |
|---|------|-----------|
| 1 | macOS 产物**禁止**在签名后修改 bundle 内任何文件 | 签名 seal 失效 → 用户看到 **"已损坏，无法打开"**，`xattr -cr` 也救不了 |
| 2 | 分发的 macOS 产物**必须**用 `ditto -c -k` 打 zip | `upload-artifact` / 普通 zip 会丢 symlink（~109 个）→ 同样"已损坏" |
| 3 | spec 收集项目模块**不能**用 `collect_submodules("backend")` | `backend/` 无 `__init__.py`（命名空间包），该调用只收到 5 个模块 → 功能静默缺失 |
| 4 | 项目内导入**一律用绝对路径** `backend.algorithm.x` | 裸导入（`from vlm_handler import`）在冻结包中失效（代码在 PYZ 内，`sys.path` 插入无效） |
| 5 | 传给 `js_api` 的对象，其**公开**属性会被 pywebview 递归内省 | 把 window 等原生对象存成公开属性 → 无限递归 → 窗口卡死（Windows 实测） |
| 6 | 签名/校验失败**绝不能**被 `\|\| true`、`2>/dev/null` 吞掉 | 坏包静默流出，用户端才发现 |

> 详细现象与修法见 [references/pitfalls.md](references/pitfalls.md)（20 项，按现象索引）。

## 构建环境

```bash
# arm64（Apple Silicon 本机）
uv venv .venv-lite --python 3.12
uv pip install --python .venv-lite/bin/python -r requirements-lite.txt pyinstaller pywebview

# x86_64（在 Apple Silicon 上经 uv 安装 Intel Python，Rosetta 构建）
uv python install cpython-3.12.13-macos-x86_64-none
uv venv .venv-x64 --python cpython-3.12.13-macos-x86_64-none
uv pip install --python .venv-x64/bin/python -r requirements-lite.txt pyinstaller pywebview

# 各架构静态 ffmpeg（按 <target>/ 分目录，双架构可共存）
./desktop/fetch_binaries.sh --all-macos
```

> **版本号单一来源**：`pyproject.toml`。`build_mac.sh` 与 `installer.iss` 的 `AppVersion` 需同步手改。

## 常用操作

### 打包（macOS）

```bash
PYTHON_ARM64=$PWD/.venv-lite/bin/python \
PYTHON_X64=$PWD/.venv-x64/bin/python \
  ./desktop/build_mac.sh --both --sign     # 或 --arm64 / --x64

# 打分发 zip（保留 symlink，等价 CI 流程）
cd desktop/dist/arm64 && ditto -c -k --keepParent --sequesterRsrc VideoDevour.app VideoDevour-macos-arm64.zip
```

脚本内置签名与 `codesign --verify` 校验，失败即退出。

### 校验产物（发版前必做）

```bash
bash .agents/skills/videodevour-desktop/scripts/verify_bundle.sh desktop/dist/arm64/VideoDevour.app
```

检查项：签名 seal、symlink 数量、架构一致性、捆绑二进制、关键模块是否收录。

### 发版

见 [references/release-checklist.md](references/release-checklist.md)。要点：

1. 升版本号（`pyproject.toml` + `desktop/installer.iss`）→ PR → 合并触发 CI
2. 从 CI artifacts 取产物（macOS artifact 是**内层 zip**，需解开一层）
3. 打 annotated tag → `gh release create` 上传 4 个资产
4. 验证公开下载链接返回 200

### 热更新设计

见 [references/update-design.md](references/update-design.md)。结论速览：

- **禁止**拉取仓库源码运行（需构建、无原子性、公共仓库 HEAD = 全量 RCE 风险）
- 三层可行性：前端 ✅ / 纯 Python ⚠️ / 依赖与原生 ❌（只能整包）
- **整包自动更新在代码签名落地前不要做**——用户点更新会再吃一次"已损坏"
- 优先做 **yt-dlp 组件热更**（平台反爬一改，旧客户端全废；纯 Python、体积小）
- 弹窗：前端渲染 + 壳执行（只有壳能重启进程、写 bundle 外文件），两段式（静默下载 → 就绪后提示）

## 排错索引

按**现象**查 [references/pitfalls.md](references/pitfalls.md)：

| 现象 | 先查 |
|------|------|
| macOS 报"已损坏，无法打开" | 约束 1/2；pitfalls「分发」组 |
| Windows 一点击就卡死、终端刷满 recursion | js_api 公开属性（约束 5） |
| 报告没有配图 / 功能静默降级 | 模块未收录（约束 3/4） |
| 客户端报 `No module named X` | 函数内导入的依赖未收集 |
| 下载 .md 白屏 / 点了没反应 | `ALLOW_DOWNLOADS` 默认 False |
| 应用启动后无窗口、无日志即退出 | `console=False`（必须 `console=True`） |
| 关闭应用后进程残留 | 父进程监测 / 信号处理 |
| 换了架构后功能失效（如在线 ASR） | 二进制 wheel 链接方式差异（cryptography 案例） |
| CI 打包步骤失败 | 编码（PowerShell/Python 写文件需注意 BOM） |

## 关键设计（改代码前必读）

| 设计 | 原因 |
|------|------|
| **单可执行双角色**：`VideoDevour`（壳） / `VideoDevour --backend-only`（后端） | 避免 .app 内查找第二个 EXE 的路径与签名复杂度 |
| **端口握手用文件**，不用 stdout | macOS 窗口模式（`console=False` 时）stdout 不可用 |
| **`console=True`**（后端 EXE） | 窗口模式的 `runw` 引导器不保留标准文件描述符，uvicorn 会静默退出 |
| **绑定 socket 后交给 uvicorn** | 禁止"探测端口→关闭→再绑定"（存在竞争窗口） |
| **`data_root` 四级优先级** | `--data-dir` → `VIDEO_DEVOUR_DATA_DIR` → 平台默认 → 源码根（开发模式行为不变） |
| 后端监测父进程需 `--parent-pid` **显式传入** | 按 `os.getppid()` 推断会误杀独立启动/CI 场景 |

## 边界

- Windows 包**只能由 CI 构建**（PyInstaller 不支持交叉编译）
- 当前为 **ad-hoc 签名**（未公证）：用户需 `xattr -cr`，且不能做整包自动更新
- 轻量包不含本地 ML 依赖（torch/funasr/sentence-transformers），离线 ASR 是增强版能力
