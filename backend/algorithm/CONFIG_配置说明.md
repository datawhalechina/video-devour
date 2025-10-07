# Config 配置说明

## 📋 概述

`config.py` 是项目的中心配置文件，包含所有路径、API 密钥和 LLM 参数设置。

## 📁 路径配置

### 项目结构

```python
PROJECT_ROOT           # 项目根目录 (VideoDevour/)
├── OUTPUT_DIR         # 输出目录 (output/)
├── input_video/       # 输入视频目录
└── backend/
    └── algorithm/     # _ALGORITHM_DIR
```

### 输入文件配置

#### ASR 结果文件

```python
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_paraformer_v2.json')
```

**支持的格式**：

| 文件名 | 格式 | 说话人信息 | 推荐 |
|--------|------|-----------|------|
| `asr_results_paraformer_v2.json` | Paraformer V2 | ✅ 已包含 | ⭐ 推荐 |
| `asr_results_paraformer.json` | Paraformer V1 | ❌ 需匹配 | - |
| `asr_results_whisper.json` | Whisper | ❌ 无 | - |

**修改方式**：

```python
# 使用 Paraformer V2（推荐）
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_paraformer_v2.json')

# 使用旧版 Paraformer
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_paraformer.json')

# 使用 Whisper
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_whisper.json')
```

#### 输入视频文件

```python
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, 'input_video', 'chat_huanhuan5min.mp4')
```

**修改方式**：

```python
# 使用不同的视频文件
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, 'input_video', '你的视频.mp4')
```

### 输出文件配置

#### ⚠️ 重要说明

配置文件中的路径**仅用于获取输出目录位置**，实际输出文件名会自动添加时间戳。

| 配置变量 | 配置值示例 | 实际输出格式 |
|---------|----------|-------------|
| `OUTLINE_MD_PATH` | `output/outline.md` | `output/outline_20251006_103000.md` |
| `DETAILED_OUTLINE_MD_PATH` | `output/detailed_outline.md` | `output/detailed_outline_20251006_103000.md` |
| `VIDEO_CUT_DIR` | `output/videocut` | `output/videocut_20251006_103000/` |
| `IMAGE_OUTPUT_DIR` | `output/frames` | `output/frames_视频名_20251006_103000/` |

#### 配置项详解

```python
# 大纲输出文件（实际：outline_时间戳.md）
OUTLINE_MD_PATH = os.path.join(OUTPUT_DIR, 'outline.md')

# 详细大纲输出文件（实际：detailed_outline_时间戳.md）
DETAILED_OUTLINE_MD_PATH = os.path.join(OUTPUT_DIR, 'detailed_outline.md')

# 视频切片目录（实际：videocut_时间戳/）
VIDEO_CUT_DIR = os.path.join(OUTPUT_DIR, 'videocut')

# 帧提取目录（实际：frames_视频名_时间戳/）
IMAGE_OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'frames')
```

**代码中的使用方式**：

```python
# 在 outline_handler.py 中
def save_outline(outline):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.dirname(config.OUTLINE_MD_PATH)  # 获取 output/ 目录
    outline_filename = f"outline_{timestamp}.md"
    outline_path = os.path.join(output_dir, outline_filename)
    # 实际保存到：output/outline_20251006_103000.md
```

## 🤖 LLM 配置

### 基本配置

```python
# LLM 模型类型
LLM_MODEL_TYPE = "deepseek-chat"

# API 端点 URL
LLM_API_URL = "https://api.deepseek.com"

# 温度参数（控制随机性）
LLM_TEMPERATURE = 0.4
```

### 常用模型配置

#### DeepSeek（当前配置）

```python
LLM_MODEL_TYPE = "deepseek-chat"
LLM_API_URL = "https://api.deepseek.com"
LLM_TEMPERATURE = 0.4
```

#### Qwen（通义千问）

```python
LLM_MODEL_TYPE = "qwen-plus"
LLM_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_TEMPERATURE = 0.4
```

#### OpenAI

```python
LLM_MODEL_TYPE = "gpt-4"
LLM_API_URL = "https://api.openai.com/v1"
LLM_TEMPERATURE = 0.7
```

### API 密钥管理

```python
def get_api_key():
    """
    获取 API 密钥
    
    优先级：
    1. 环境变量 DASHSCOPE_API_KEY
    2. 硬编码的示例密钥（不推荐）
    """
    api_key = os.getenv("DASHSCOPE_API_KEY", "sk-69152968e4bd493d99778613bacc5970")
    if api_key == "sk-69152968e4bd493d99778613bacc5970":
        print("Warning: Using a hardcoded example API key...")
    return api_key
```

**推荐做法 - 使用环境变量**：

Windows PowerShell:
```powershell
$env:DASHSCOPE_API_KEY = "你的实际API密钥"
python backend/algorithm/main.py
```

Linux/Mac:
```bash
export DASHSCOPE_API_KEY="你的实际API密钥"
python backend/algorithm/main.py
```

## 🔧 修改配置的最佳实践

### 1. 不要直接修改原配置

创建副本进行实验：

```bash
# 创建配置备份
cp backend/algorithm/config.py backend/algorithm/config.backup.py

# 或创建自定义配置
cp backend/algorithm/config.py backend/algorithm/config.custom.py
```

### 2. 使用环境变量

对于敏感信息（如 API 密钥），使用环境变量：

```python
# config.py
API_KEY = os.getenv("MY_API_KEY", "默认值")
INPUT_VIDEO = os.getenv("INPUT_VIDEO", "input_video/chat_huanhuan5min.mp4")
```

### 3. 版本控制排除

确保 `.gitignore` 包含：

```gitignore
# 自定义配置文件
backend/algorithm/config.custom.py
backend/algorithm/config.local.py

# 环境变量文件
.env
*.env
```

## 📊 配置示例

### 示例 1：处理不同的视频

```python
# config.py
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, 'input_video', 'presentation.mp4')
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_presentation.json')
```

### 示例 2：使用不同的 LLM

```python
# config.py
LLM_MODEL_TYPE = "gpt-4"
LLM_API_URL = "https://api.openai.com/v1"
LLM_TEMPERATURE = 0.7

def get_api_key():
    return os.getenv("OPENAI_API_KEY", "your-openai-key")
```

### 示例 3：自定义输出目录

```python
# config.py
# 自定义输出目录（例如，输出到项目外部）
OUTPUT_DIR = os.path.join('D:', 'VideoOutput')

# 其他配置保持不变
OUTLINE_MD_PATH = os.path.join(OUTPUT_DIR, 'outline.md')
# ...
```

## 🚀 快速配置向导

### 步骤 1：选择 ASR 格式

```python
# 推荐：使用 Paraformer V2
ASR_RESULT_PATH = os.path.join(OUTPUT_DIR, 'asr_results_paraformer_v2.json')
```

### 步骤 2：设置输入视频

```python
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, 'input_video', '你的视频.mp4')
```

### 步骤 3：配置 LLM

```python
LLM_MODEL_TYPE = "deepseek-chat"  # 或 "qwen-plus", "gpt-4" 等
LLM_API_URL = "https://api.deepseek.com"
```

### 步骤 4：设置 API 密钥

```bash
# 方式 1：环境变量（推荐）
export DASHSCOPE_API_KEY="你的密钥"

# 方式 2：修改 get_api_key() 函数
```

### 步骤 5：运行主程序

```bash
python backend/algorithm/main.py
```

## 📝 配置检查清单

运行前请确认：

- [ ] ASR 结果文件存在且格式正确
- [ ] 输入视频文件存在
- [ ] LLM API 密钥已设置
- [ ] LLM 配置正确（模型类型、URL）
- [ ] 输出目录有写入权限
- [ ] ffmpeg 已安装（用于视频处理）

## 🐛 常见问题

### 问题 1：FileNotFoundError: ASR 文件未找到

**原因**：ASR 结果文件不存在

**解决方案**：
```bash
# 先运行 ASR 引擎生成结果文件
python backend/devour/asr_engine_paraformer_v2.py
```

### 问题 2：API 密钥无效

**原因**：使用了示例密钥或密钥过期

**解决方案**：
```bash
# 设置正确的 API 密钥
export DASHSCOPE_API_KEY="你的实际密钥"
```

### 问题 3：输出文件没有时间戳

**原因**：使用了旧版本代码

**解决方案**：确保使用最新版本的 `outline_handler.py` 和 `video_handler.py`

### 问题 4：找不到 ffmpeg

**原因**：ffmpeg 未安装或不在 PATH 中

**解决方案**：
```bash
# Windows (使用 choco)
choco install ffmpeg

# Mac (使用 Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## 📚 相关文档

- [文件结构_时间戳命名说明.md](./文件结构_时间戳命名说明.md) - 时间戳命名详解
- [DATA_PROCESSOR_V2_说明.md](./DATA_PROCESSOR_V2_说明.md) - 数据处理说明
- [main.md](./main.md) - 主流程说明

## 📮 技术支持

如有问题或建议，请提交 Issue。

