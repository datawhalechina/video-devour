# 打包坑清单（20 项，按现象索引）

> 全部为实测发现，不是推测。编号与 `planning/A3-A4-构建验证报告.md` 对应，便于追溯。
> **排错方法**：先按现象定位条目 → 看根因判断是否同类 → 用"修法"验证。
> 通用判据：**开发模式正常 ≠ 客户端正常**；`No module named X` 几乎总是"冻结环境模块收集/导入"问题。

---

## A. 启动与生命周期

### A1. 应用启动后无窗口、无任何日志即退出（#1）

- **现象**：双击/命令行启动，进程瞬间消失，stderr 无输出
- **根因**：spec 里 `console=False` 时 macOS 用 `runw` 引导器，**不保留标准文件描述符**；uvicorn 拿不到 stdin/stdout 会静默退出
- **修法**：spec 的 `EXE(console=True)`；Windows 侧由壳传 `CREATE_NO_WINDOW` 隐藏控制台
- **验证**：`./VideoDevour --backend-only --help` 有输出即说明描述符正常

### A2. 壳读不到后端端口（#2）

- **根因**：窗口模式下 stdout 不可用，逐行解析握手信息失败
- **修法**：改为**握手文件**（`--handshake-file`，写临时文件后 `os.replace` 原子替换）+ stdout 双通道；壳轮询文件
- **涉及**：`desktop/backend_server.py::_emit`、`desktop/shell.py::BackendProcess.start`

### A3. 关闭/强杀应用后后端进程残留（#5、#8）

- **现象**：退出应用后端口仍被占用；`ps` 能看到 `--backend-only` 进程
- **根因**：① 壳被 SIGKILL 时 `finally` 不执行；② 信号处理器在 Cocoa 主循环里不生效
- **修法**：
  - 壳安装 SIGTERM/SIGINT 处理器 → 清理后退出
  - **后端监测父进程**（壳传 `--parent-pid <pid>`），父进程消失即自退
  - ⚠️ **必须显式传入 PID**：按 `os.getppid()` 推断会在"后台启动、shell 立刻退出"的正常场景误杀服务
- **验证**：`kill -9 <壳 PID>` 后 8 秒内后端应自行退出

### A4. Windows 一点击就卡死，终端刷满 recursion（#13）

- **现象**：`window.native.AccessibilityObject.Bounds.Empty.Empty.Empty...: maximum recursion depth exceeded`（数百行）
- **根因**：`js_api` 对象的**公开属性**会被 pywebview 递归内省（`webview/util.py::get_functions`，只跳过 `_` 开头）；`self.window` 指向原生窗口对象 → 走进 WinForms 对象图；`Rectangle.Empty` 每次返回新实例 → `id()` 去重失效 → 无限递归；注入线程卡死使 `_pywebviewready` 永不触发
- **修法**：窗口引用改私有 `_window`。**规则：传给 `js_api` 的对象，任何指向原生/外部框架的引用都必须下划线私有**
- **验证**：用 pywebview 真实 `get_functions` 逻辑 + 模拟 `Rectangle.Empty` 行为做对照测试

### A5. 端口被抢占（#6）

- **根因**："探测空闲端口 → 关闭 → 再启动 uvicorn"存在竞争窗口
- **修法**：`socket.bind()` + `listen()` 后**保持打开**，直接 `uvicorn.Server.run(sockets=[sock])`
- **涉及**：`desktop/backend_server.py::_bind_socket`

---

## B. 运行期功能异常（能跑但不对）

### B1. 下载/合并音视频报 "ffmpeg is not installed"（#7）

- **现象**：`You have requested merging of multiple formats but ffmpeg is not installed. Aborting due to --abort-on-error`
- **根因**：yt-dlp 只查系统 PATH，**忽略捆绑的 ffmpeg**——`_get_ydl()` 没设 `ffmpeg_location`
- **修法**：`_get_ydl` 传 `ffmpeg_location=ffmpeg_path()`（yt-dlp 会据此自动推导 ffprobe，含 Windows `.exe`）
- **验证**：`PATH=/usr/bin:/bin`（无 ffmpeg）下跑通一次真实下载合并

### B2. macOS 点「下载 .md」白屏，PDF/ZIP 点了没反应（#19）

- **根因**：pywebview `ALLOW_DOWNLOADS` 默认 **False**。mac 的响应策略里 `canShowMIMEType()` 优先 → `text/markdown` 这类可显示响应被**当作导航**（SPA 被替换 = 白屏）；`application/zip` 不可显示但下载被禁 = 静默失败
- **修法**：
  1. 壳启动前 `webview.settings['ALLOW_DOWNLOADS'] = True`
  2. 所有下载锚点加 `download` 属性（在 action 层即识别为下载，**与 MIME 无关**，是防白屏第一道防线）
  3. `window.open` 改 `<a download>`（其导航类型为 `Other`，不会被"新窗口交系统浏览器"逻辑接管，客户端内静默无反应）
- **涉及**：`desktop/shell.py`、`frontend/src/utils/helpers.js::triggerDownload`
- **验证**：最小复现——本地 HTTP 返回 `Content-Disposition: attachment`，点击后检查 SPA 标记元素是否还在（`ALLOW_DOWNLOADS=False` → 标记消失；`=True` → 存活）

### B3. 新装用户首次上传视频必然失败（#9、#10）

- **根因**：`DEFAULT_SETTINGS.asr_mode` 默认 `offline`，但轻量包**没有 torch/funasr**；报错是裸的 `No module named 'torch'`，用户无法据此操作
- **修法**：默认改 `online`（已有配置不被静默改写）；`asr_factory` 捕获 ImportError 并提示"切换在线 ASR 或安装增强版"

### B4. 切换 ASR 提供商后报 Model not found（#11）

- **根因**：两家模型名不通用（`fun-asr-realtime` vs `stepaudio-2.5-asr`），切 provider 时残留旧名
- **修法**：`PROVIDER_DEFAULT_ASR_MODEL` 常量；切 provider 且未显式指定模型名时自动跟随

### B5. 报告没有配图，但流程显示"处理成功"（#16）

- **根因**：VLM 不可用时 `except` 返回 `{}` 静默跳过，用户只看到成功
- **修法**：错误信息改为可操作提示（明确告知"报告将不含配图" + 检查 VLM 配置）
- **通用原则**：**任何降级路径都要让用户看得见**，不能静默

---

## C. 模块收集（冻结环境特有，最高发）

> 通用背景：PyInstaller 按**静态导入图**收集模块。函数内 `import`、动态导入、命名空间包都可能漏。

### C1. `No module named 'vlm_handler'` / 功能模块静默缺失（#14、#15）

- **根因（两层，常同时存在）**：
  1. **命名空间包**：`backend/`、`backend/algorithm/`、`backend/devour/` 都**没有 `__init__.py`**，`collect_submodules("backend")` 只返回 `backend.api`/`backend.runtime` 下的 5 个模块（实测），algorithm/devour 一个都收不到。此前能跑只是碰巧靠静态 import 链
  2. **裸导入**：`from vlm_handler import ...` 依赖 `sys.path` 插入 `backend/algorithm`，而冻结后代码在 PYZ 归档内、该目录在磁盘上不存在
- **修法**：
  - spec 改为**文件系统枚举** `backend/**/*.py`（排除 `test_*`、`config.template`）
  - 项目内导入统一改绝对路径 `backend.algorithm.*`
- **涉及**：`desktop/videodevour.spec::_iter_backend_modules`、`image_processor.py`、`outline_handler.py`、`semantic_matcher.py`
- **验证**：`grep -c "'backend\.algorithm\." PYZ-00.toc`，应从 16 增至 20+

### C2. `Unknown encoding o200k_base`（tiktoken，#3）

- **根因**：`tiktoken` 的编码表通过 `tiktoken_ext` **动态发现**，未收集则运行期缺编码表
- **修法**：`tiktoken_ext` 是**命名空间包**（`__file__` 为 None），`collect_data_files` 无效，必须用 `importlib.util.find_spec` 定位 `submodule_search_locations` 后作为 datas 收集
- **涉及**：`desktop/videodevour.spec`

### C3. 函数内导入的第三方库未打包（reportlab 案例，#12）

- **现象**：`ModuleNotFoundError: No module named 'reportlab'`（导出 PDF 时）
- **根因**：`pdf_export` 在 API 里是**函数内导入**，静态分析看不到其依赖
- **修法**：spec 中显式 `collect_submodules("reportlab")` + `collect_data_files("reportlab")`
- **通用规则**：**新增任何"函数内 import"的第三方包，同步更新 spec 的 hiddenimports**

### C4. 收集告警但不影响功能（#4）

- **现象**：`Failed to collect submodules for 'camel.runtimes' ... No module named 'tqdm'`
- **根因**：tqdm 仅被 camel 的 Docker runtime 使用（本项目不用）
- **修法**：加入 `requirements-lite.txt` 消除告警（避免误判）
- **判断**：`Failed to collect submodules for 'webview.platforms.android'`（缺 `android`）、`urllib3.contrib.emscripten`（缺 `js`）属同类，可忽略

---

## D. 构建期失败

### D1. 某架构功能失效、另一架构正常（#17）

- **案例**：x86_64 包在线 ASR 全失败 —— `symbol not found in flat namespace '_BIO_ADDR_free'`
- **根因**：`cryptography` 的 **macOS x86_64 wheel（50.x）** 把 OpenSSL 符号留作**未定义**（期望运行时动态解析），而 uv 的 x86_64 CPython **静态链接 OpenSSL 且不导出符号**；arm64 wheel 则静态解析进自身，故不受影响
- **修法**：锁定 `cryptography==46.0.4`（实测两架构 wheel 均无未定义 OpenSSL 符号）
- **通用教训**：**"arm64 能跑"不能推出"x86_64 能跑"**——同一份代码的两个架构 wheel 链接方式可能不同，每个架构都要实际跑通链路
- **排查手法**：`nm -u <xxx.so> | grep -iE "OPENSSL|BIO_"` 看未定义符号；对比两架构

### D2. 打包脚本语法/编码错误（CI 日志）

- **案例**：`build_win.ps1` 无 BOM 的 UTF-8 被 PowerShell 5.1 按 ANSI 读取，中文注释变乱码 → 语法错误
- **修法**：`.ps1`、`.iss` 等 Windows 侧脚本**加 UTF-8 BOM**
- **通用规则**：写给 Windows 工具链的非 ASCII 文本文件，一律带 BOM

### D3. 架构校验误报

- **案例**：脚本用 `platform.machine()` 返回值（`x86_64`）与参数名（`x64`）直接比较 → 永远不匹配
- **修法**：显式映射 `x64 ↔ x86_64`；`build_mac.sh` 内置该映射并**在构建前校验解释器架构**（PyInstaller 输出架构由解释器决定，错了整包白做）

---

## E. 分发与安装

### E1. macOS 报"已损坏，无法打开。你应该将它移到废纸篓"（#18）

- **最严重的一类**：`xattr -cr` **无效**，因为卡在签名校验之前
- **根因**：`actions/upload-artifact@v4` **不保留符号链接**。`.app` 内 PyInstaller 产物含 **~109 个 symlink**（`Python.framework/Versions/Current`、opencv 的 `.dylibs` 等），artifact 化时被物化成实体 → 文件树与签名 seal 不符 → Gatekeeper 判损坏
- **判别**：
  ```bash
  find VideoDevour.app -type l | wc -l        # 正常应 >0（arm64 约 109）；为 0 即中招
  codesign --verify --deep --strict VideoDevour.app
  # 报 "a sealed resource is missing or invalid" + 大量 file added/modified
  ```
- **修法**：
  1. CI 产物**先 `ditto -c -k --keepParent --sequesterRsrc` 打 zip 再上传**，release 直接用该 zip
  2. 构建流程新增「**解压回验签名**」步骤（解压后 `codesign --verify`），损坏在构建期即失败
- **涉及**：`.github/workflows/desktop-build.yml`、`desktop/build_mac.sh`
- **本机验证**：`ditto -x -k <zip>` → `codesign --verify --deep --strict` → 应通过且 symlink 数 >0

### E2. 签名失败被静默吞掉（#20）

- **现象**：构建显示成功，但产物 `code object is not signed at all`
- **根因**：脚本里 `codesign ... 2>/dev/null || true`
- **修法**：签名失败**立即退出**；签名后**必须** `codesign --verify --deep --strict` 通过才允许分发
- **通用原则**：签名/校验是分发的最后一道闸门，任何"跳过以便跑通"的写法都会让坏包流出

### E3. 用户反馈"首次启动很慢"（非缺陷）

- **现象**：首次启动等待 1-2 分钟（尤其 `/tmp` 等目录），之后约 3 秒
- **根因**：macOS XProtect 对**首次运行**的应用做全量安全扫描（370MB）
- **处理**：属一次性行为，在 release notes 说明即可，不要"修复"
- **测试注意**：在 `/tmp` 下测试会放大该现象，用户真实路径（下载/应用程序）表现更好

---

## 附：环境相关（非缺陷）

| 现象 | 说明 |
|------|------|
| `xattr -cr` 报 `Operation not permitted` | `com.apple.provenance` 是系统保护属性，删不掉也无害；应用已能启动 |
| CI Intel job（`macos-15-intel`）启动慢 | 该 runner 排队/启动较慢（约 6-8 分钟），正常 |
| `macos-13` 永久 queued | 该 runner 已被 GitHub 弃用，用 `macos-15-intel` |
