# 帧提取文件结构说明

## 📋 概述

`video_handler.py` 中的 `extract_frames_from_videos()` 函数已更新，现在提取的帧文件会保存在包含时间戳的母文件夹中。

## 📁 新的文件结构

### 目录命名规则

母文件夹命名格式：`frames_视频名_时间戳`

- `frames`: 固定前缀
- `视频名`: 原视频片段的名称（不含扩展名）
- `时间戳`: 提取时的时间戳（格式：`YYYYMMDD_HHMMSS`）

### 示例结构

假设我们有以下视频片段：
- `01_项目架构图.mp4`
- `02_微调模块与Prompt优化模块.mp4`
- `03_知识库问答流程.mp4`

提取帧后的文件结构：

```
output/
├── frames_01_项目架构图_20251006_103000/
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   ├── frame_0003.jpg
│   └── ...
│
├── frames_02_微调模块与Prompt优化模块_20251006_103000/
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   ├── frame_0003.jpg
│   └── ...
│
└── frames_03_知识库问答流程_20251006_103000/
    ├── frame_0001.jpg
    ├── frame_0002.jpg
    ├── frame_0003.jpg
    └── ...
```

## 🔄 与旧结构的对比

### 旧结构（之前）

```
output/frames/
├── 01_项目架构图/
│   ├── frame_0001.jpg
│   └── ...
├── 02_微调模块与Prompt优化模块/
│   ├── frame_0001.jpg
│   └── ...
└── 03_知识库问答流程/
    ├── frame_0001.jpg
    └── ...
```

### 新结构（现在）

```
output/
├── frames_01_项目架构图_20251006_103000/
│   ├── frame_0001.jpg
│   └── ...
├── frames_02_微调模块与Prompt优化模块_20251006_103000/
│   ├── frame_0001.jpg
│   └── ...
└── frames_03_知识库问答流程_20251006_103000/
    ├── frame_0001.jpg
    └── ...
```

## ✨ 新结构的优势

### 1. **时间可追溯**
- ✅ 每个提取批次都有唯一的时间戳
- ✅ 便于区分不同时间的提取结果
- ✅ 方便版本对比和历史追踪

### 2. **避免覆盖**
- ✅ 多次提取不会覆盖之前的结果
- ✅ 可以保留历史提取记录
- ✅ 便于比较不同参数的提取效果

### 3. **更清晰的组织**
- ✅ 每个视频的帧文件独立存储
- ✅ 文件夹名称自包含所有必要信息
- ✅ 便于批量处理和管理

### 4. **便于自动化**
- ✅ 脚本可以根据时间戳自动选择最新批次
- ✅ 便于实现清理旧文件的策略
- ✅ 支持并行提取（不同批次互不干扰）

## 🔧 代码实现

### 关键代码片段

```python
from datetime import datetime

def extract_frames_from_videos():
    # 生成时间戳（格式：YYYYMMDD_HHMMSS）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for video_file in video_files:
        video_name = os.path.splitext(video_file)[0]
        
        # 构建母文件夹名称：frames_视频名_时间戳
        parent_folder_name = f"frames_{video_name}_{timestamp}"
        frame_output_dir = os.path.join(
            os.path.dirname(config.IMAGE_OUTPUT_DIR), 
            parent_folder_name
        )
        
        # 创建目录并提取帧
        os.makedirs(frame_output_dir, exist_ok=True)
        # ... ffmpeg 提取逻辑
```

### 时间戳格式

- 格式：`YYYYMMDD_HHMMSS`
- 示例：`20251006_103000`（2025年10月6日 10:30:00）
- 优点：
  - 易于阅读
  - 文件系统友好（无特殊字符）
  - 可排序（按字母顺序即时间顺序）

## 📊 使用场景

### 场景 1：日常使用
```bash
# 运行主流程
python backend/algorithm/main.py

# 结果自动保存到带时间戳的文件夹
output/frames_01_视频名_20251006_103000/
```

### 场景 2：参数对比
```bash
# 第一次提取（fps=1）
# 输出：output/frames_01_视频名_20251006_103000/

# 修改参数后再次提取（fps=2）
# 输出：output/frames_01_视频名_20251006_103530/

# 两个版本的结果都保留，便于对比
```

### 场景 3：批量处理
```python
# 查找最新的帧文件夹
import glob
from pathlib import Path

output_dir = Path("output")
frame_folders = sorted(output_dir.glob("frames_01_*"))
latest_folder = frame_folders[-1]  # 按时间戳排序后的最后一个

print(f"使用最新的帧文件夹: {latest_folder}")
```

## 🛠️ 配置说明

### 相关配置项

在 `config.py` 中：

```python
# 输出目录配置
OUTPUT_DIR = "output"
IMAGE_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "frames")  # 仅用于参考

# 实际的帧文件保存在：
# output/frames_视频名_时间戳/
```

### 注意事项

1. **时间戳一致性**
   - 同一批次的所有视频使用相同的时间戳
   - 时间戳在函数开始时生成一次

2. **路径构建**
   - 使用 `os.path.dirname(config.IMAGE_OUTPUT_DIR)` 获取 output 目录
   - 确保在正确的父目录下创建文件夹

3. **文件名规范**
   - 视频名中的特殊字符已在切分时清理
   - 帧文件名保持 `frame_0001.jpg` 格式

## 📝 日志输出

提取过程中的日志示例：

```
2025-10-06 10:30:00 - INFO - --- 步骤 7: 开始从视频片段中提取帧 ---
2025-10-06 10:30:00 - INFO - 正在从 '01_项目架构图.mp4' 提取帧到 'output/frames_01_项目架构图_20251006_103000'...
2025-10-06 10:30:05 - INFO - 成功从 '01_项目架构图.mp4' 提取了 120 帧。
2025-10-06 10:30:05 - INFO - 帧已保存到: output/frames_01_项目架构图_20251006_103000
2025-10-06 10:30:05 - INFO - 正在从 '02_微调模块与Prompt优化模块.mp4' 提取帧到 'output/frames_02_微调模块与Prompt优化模块_20251006_103000'...
2025-10-06 10:30:12 - INFO - 成功从 '02_微调模块与Prompt优化模块.mp4' 提取了 85 帧。
2025-10-06 10:30:12 - INFO - 帧已保存到: output/frames_02_微调模块与Prompt优化模块_20251006_103000
2025-10-06 10:30:12 - INFO - --- 帧提取完成，总共提取了 205 帧 ---
```

## 🔍 后续处理

### 如何使用提取的帧

如果需要在 `image_processor.py` 中处理帧文件，可以使用以下方式：

```python
import glob
from pathlib import Path

def find_latest_frames():
    """查找最新的帧文件夹"""
    output_dir = Path("output")
    frame_folders = sorted(output_dir.glob("frames_*"))
    
    if not frame_folders:
        return []
    
    # 按时间戳排序（文件夹名已包含时间戳）
    return frame_folders

def process_frames_by_video(video_name):
    """处理特定视频的帧"""
    output_dir = Path("output")
    # 查找该视频的所有批次
    pattern = f"frames_{video_name}_*"
    matching_folders = sorted(output_dir.glob(pattern))
    
    if matching_folders:
        # 使用最新的批次
        latest_folder = matching_folders[-1]
        print(f"处理帧文件夹: {latest_folder}")
        
        # 获取所有帧文件
        frames = sorted(latest_folder.glob("frame_*.jpg"))
        return frames
    
    return []
```

## 🧹 清理策略

### 建议的清理脚本

```python
from pathlib import Path
import shutil
from datetime import datetime, timedelta

def cleanup_old_frames(days=7):
    """
    删除超过指定天数的帧文件夹
    
    Args:
        days: 保留最近多少天的数据
    """
    output_dir = Path("output")
    frame_folders = output_dir.glob("frames_*")
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for folder in frame_folders:
        # 从文件夹名提取时间戳
        parts = folder.name.split('_')
        if len(parts) >= 3:
            try:
                timestamp_str = f"{parts[-2]}_{parts[-1]}"
                folder_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if folder_date < cutoff_date:
                    print(f"删除旧文件夹: {folder}")
                    shutil.rmtree(folder)
            except ValueError:
                print(f"无法解析时间戳: {folder.name}")

# 使用示例
cleanup_old_frames(days=7)  # 只保留最近7天的数据
```

## 📮 技术支持

如有问题或建议，请提交 Issue。

