# VideoDevour 桌面客户端 · 测试包

构建日期：2026-09-15　版本：0.1.5（轻量包）

## 交付文件

| 文件 | 平台 | 大小 | 说明 |
|------|------|------|------|
| `VideoDevour-0.1.5-setup.exe` | Windows x64 | 146MB | **推荐**：安装程序，含开始菜单/桌面快捷方式 |
| `VideoDevour-windows-x64.zip` | Windows x64 | 203MB | 绿色版，解压即用（免安装） |
| `VideoDevour-macos-arm64.zip` | macOS Apple Silicon | 168MB | M 系列芯片 |
| `VideoDevour-macos-x64.zip` | macOS Intel | 175MB | Intel 芯片 |

> **macOS 两个包按芯片选择**：M1/M2/M3/M4 用 `arm64`，Intel 用 `x64`。选错会打不开。
> **绿色版必须解压后运行**：含 onedir 结构，不能只单独拿出 `.exe`。

## 本版更新（0.1.5）

- **修复生成类功能失效（严重回归）**：v0.1.4 里报告页的量子速读 / 公众号文章 /
  小红书笔记点开即报「生成失败」，思维导图 / 知识图谱 / 学习卡片点了完全没反应。
  根因是配置引导的上下文绑定遗漏，本次已修复。
- **原文排版优化**：详细报告与图文大纲里的「视频原文」改为一句一行、各带时间戳，
  不再是一大段挤在一起的文字，便于逐句对照与按时间戳回看。
- 增加前端静态检查（lint）配置，防止「能打包、运行时才报错」的问题再次漏过。

## 历史版本更新（0.1.4）

- **未配置模型时会主动引导**：没填 LLM/VLM/ASR 就点生成，会弹出说明弹窗并可直接
  跳到「偏好设置」，不再是只报错让人不知所措。已生成过的内容不会被拦。
- **修复点「查看原视频」后回不来**：此前外链会在客户端内打开，而客户端没有后退
  按钮，只能强杀重开。现在所有站外链接（原视频、思维导图预览、字幕笔记等）
  一律交给系统浏览器打开；壳另有一层站点级护栏兜底。
- **新增学习测试（测试习题）**：报告页可依据报告出题（单选/多选/判断），服务端
  判题，含逐题解析、分章掌握度与学习建议，用于检验学习效果。
- 版本号统一由 `pyproject.toml` 提供（修复此前包内版本号与实际发布版本不一致）。

## 历史版本更新（0.1.3）

- 修复 macOS 点「下载 .md / PDF」导致界面白屏。
- 衍生文体（量子速读/公众号/小红书）改为并行生成。

## 历史版本更新（0.1.2）

- **修复 Windows 下浏览器 Cookie 读取**：Chrome/Edge 127+ 的 Cookie 受 App-Bound
  加密保护且被浏览器独占锁定，第三方库在非管理员权限下无法读取。
- **新增「应用内登录读取 Cookie」**：在设置页点对应平台按钮，弹出内嵌登录窗口，
  登录成功后自动读取并填入，绕开上述限制，是 Windows 上最可靠的方式。
- 修复腾讯元宝登录态读取（其 Cookie 写在 `.tencent.com` 父域）。
- 新增 [Windows 客户端使用指南](../../docs/Windows客户端使用指南.md)（分步配图）。

## Windows 测试步骤

### 方式一：安装包（推荐）

1. 双击 `VideoDevour-0.1.5-setup.exe`
2. 按向导安装（默认装到 `%LOCALAPPDATA%\Programs\VideoDevour`，免管理员权限）
3. 从开始菜单或桌面快捷方式启动

**卸载时用户数据会保留**（任务、报告、设置都在 `%LOCALAPPDATA%\VideoDevour`）。

### 方式二：绿色版

```powershell
Expand-Archive VideoDevour-windows-x64.zip -DestinationPath .
.\VideoDevour.exe
```

### SmartScreen 提示

两种方式首次运行都会弹"Windows 已保护你的电脑"——因为**安装包与可执行文件都未做代码签名**。
点「更多信息」→「仍要运行」即可。这是预期行为，正式发行前会加签名证书。

**系统要求**：Windows 10/11 x64 + WebView2 运行时（Win11 及较新版 Win10 已内置）。

## macOS 测试步骤

```bash
# 1. 解压
unzip VideoDevour-macos-arm64.zip

# 2. 解除 Gatekeeper 隔离（仅内测需要，正式版会做公证）
xattr -cr VideoDevour.app

# 3. 运行
open VideoDevour.app
```

若双击提示"已损坏"或"无法验证开发者"，就是第 2 步没做。

**适用机型**：Apple Silicon（M1/M2/M3/M4）。Intel Mac 不适用（本次未构建 x86_64）。

## 首次使用要配置的东西

轻量包默认**不包含本地语音识别**，默认使用**在线 ASR**。启动后需要：

1. 打开左侧「偏好设置」
2. 配置 **LLM**（必填，用于生成大纲与报告）
3. 配置 **VLM**（图文报告必填，用于挑选关键帧）
4. 配置 **在线 ASR 的 Key**（DashScope 或 StepFun；字幕速记不需要，上传本地视频需要）

> ⚠️ 不要选「离线」模式——轻量包不含本地引擎，会提示"本安装包不包含本地语音识别引擎"。

配置保存在：
- macOS：`~/Library/Application Support/VideoDevour/settings.json`
- Windows：`%LOCALAPPDATA%\VideoDevour\settings.json`

## 请重点测试这些场景

| 场景 | 预期 |
|------|------|
| 粘贴 B站/YouTube 链接 → 字幕速记 | 秒级出笔记，展示字幕来源与覆盖范围 |
| 上传本地短视频 → 图文报告 | 走 ASR → 大纲 → 关键帧 → 报告，产物含图片 |
| 关闭窗口后再打开 | 单实例：不会启动第二个窗口；历史记录仍在 |
| 任务运行中关闭窗口 | 应弹确认；确认后后端进程被回收 |
| 中文/空格路径的视频 | 能正常读取处理 |
| 拖入文件 / 原生选择文件 | 能打开系统文件选择器 |
| 中文输入（编辑报告时） | 输入法正常，无丢字 |
| 断网后打开已有报告 | 报告可阅读（图表库本地化尚未完成，可能受影响） |

## 已知限制（测试时不必报为 bug）

- **不含本地 ASR**：离线转写需后续增强包；本包只支持在线 ASR 与字幕速记
- **不是完全离线**：报告生成需联网调用 LLM/VLM；部分可视化依赖 CDN
- **未做代码签名**：macOS 需 `xattr -cr`，Windows 会有 SmartScreen 提示
- **无本地会话鉴权**：服务只监听 127.0.0.1，但尚未加 token 校验（阶段 B2 计划）
- **任务状态在内存 + JSON**：强制退出会显示 interrupted，需重试
- **Windows 包已在真机验证核心链路**：启动、Cookie 读取、链接解析、本地视频处理均通过；其余边界场景请继续回归

## 反馈时请附上

- 操作系统版本 + 芯片/CPU 型号
- 出问题时：`logs/backend.log`（数据目录下）
  - macOS：`~/Library/Application Support/VideoDevour/logs/backend.log`
  - Windows：`%LOCALAPPDATA%\VideoDevour\logs\backend.log`
- 复现步骤与截图
