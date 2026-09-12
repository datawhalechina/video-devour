# VideoDevour 桌面客户端 · 测试包

构建日期：2026-09-12　版本：0.1.0（轻量包）

## 交付文件

| 文件 | 平台 | 大小 | 说明 |
|------|------|------|------|
| `VideoDevour-0.1.0-setup.exe` | Windows x64 | 146MB | **推荐**：安装程序，含开始菜单/桌面快捷方式 |
| `VideoDevour-windows-x64.zip` | Windows x64 | 203MB | 绿色版，解压即用（免安装） |
| `VideoDevour-macos-arm64.zip` | macOS Apple Silicon | 195MB | M 系列芯片 |
| `VideoDevour-macos-x64.zip` | macOS Intel | 175MB | Intel 芯片 |

> **macOS 两个包按芯片选择**：M1/M2/M3/M4 用 `arm64`，Intel 用 `x64`。选错会打不开。
> **绿色版必须解压后运行**：含 onedir 结构，不能只单独拿出 `.exe`。

## Windows 测试步骤

### 方式一：安装包（推荐）

1. 双击 `VideoDevour-0.1.0-setup.exe`
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
- **Windows 包未在真机做过完整功能测试**：CI 只验证了启动与 health，业务链路请在真机确认

## 反馈时请附上

- 操作系统版本 + 芯片/CPU 型号
- 出问题时：`logs/backend.log`（数据目录下）
  - macOS：`~/Library/Application Support/VideoDevour/logs/backend.log`
  - Windows：`%LOCALAPPDATA%\VideoDevour\logs\backend.log`
- 复现步骤与截图
