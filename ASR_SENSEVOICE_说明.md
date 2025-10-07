# SenseVoice 两阶段识别方案说明

## 📌 方案概述

采用两阶段识别方案，精确获取语音识别的时间戳：

1. **第一阶段**：使用 VAD（Voice Activity Detection）模型对音频进行分段
2. **第二阶段**：对每个 VAD 分段使用 SenseVoice 模型进行语音识别

## 🔄 工作流程

```
视频文件 
  ↓
提取音频 (16kHz WAV)
  ↓
VAD 模型分段
  ↓
逐个分段识别
  ├─ 裁剪音频片段
  ├─ SenseVoice 识别
  └─ 添加时间戳
  ↓
合并结果
```

## ✨ 主要改进

### 1. **新增依赖**
```python
import soundfile as sf  # 用于音频裁剪
```

### 2. **独立的模型加载**
- **VAD 模型**：`self.vad_model` - 负责音频分段
- **SenseVoice 模型**：`self.asr_model` - 负责语音识别

### 3. **新增方法**
```python
def crop_audio(self, audio_data, start_time, end_time, sample_rate):
    """裁剪音频片段（毫秒级精度）"""
```

### 4. **重写核心识别方法**
```python
def devour_video(self, video_path: str) -> dict:
    """使用两阶段识别（VAD分段 + SenseVoice识别）"""
```

## 📊 输出格式

```json
{
  "transcript": [
    {
      "id": 0,
      "start": 0.5,      // 秒
      "end": 3.2,        // 秒
      "text": "识别的文本内容"
    },
    {
      "id": 1,
      "start": 3.5,
      "end": 8.1,
      "text": "下一段文本"
    }
  ],
  "speakers": null,
  "language": "auto",
  "video_path": "/path/to/video.mp4",
  "processed_at": "2025-09-30T..."
}
```

## 🚀 使用方法

### 安装依赖
```bash
pip install soundfile
```

### 运行测试
```bash
cd backend/devour
python asr_engine_paraformer.py
```

### 查看结果
```bash
# 结果保存在
output/asr_results_sensevoice.json
```

## ⚙️ 配置参数

### VAD 模型参数
```python
max_single_segment_time=30000  # 最大单个片段时长（毫秒）
```

### SenseVoice 参数
```python
language="auto"     # 自动检测语言 (zh/en/yue/ja/ko)
use_itn=True       # 使用逆文本规范化
batch_size_s=60    # 批处理大小（秒）
```

## 📈 优势

1. ✅ **精确的时间戳**：每个片段都有准确的开始和结束时间
2. ✅ **更好的分段**：VAD 模型专门用于语音活动检测
3. ✅ **灵活可控**：可以单独调整 VAD 和识别的参数
4. ✅ **错误隔离**：单个片段识别失败不影响其他片段
5. ✅ **多语言支持**：自动检测中文、英文、粤语、日语、韩语

## 🔍 调试信息

运行时会输出详细的处理信息：
```
INFO - 第一阶段：使用 VAD 模型进行音频分段...
INFO - VAD 检测到 XX 个语音片段
INFO - 第二阶段：使用 SenseVoice 对每个片段进行识别...
INFO -   片段 1/XX: 0.5s - 3.2s, 文本长度: 50
INFO -   片段 2/XX: 3.5s - 8.1s, 文本长度: 120
...
INFO - 转写完成，共识别 XX 个有效片段
```

## 📝 注意事项

1. **内存使用**：处理长视频时，VAD 会将整个音频加载到内存
2. **处理时间**：两阶段处理会比单阶段稍慢，但精度更高
3. **临时文件**：每个片段都会创建临时文件，处理完会自动清理
4. **设备配置**：建议使用 GPU（`cuda:0`）以加快处理速度

## 🐛 故障排除

### 问题1：soundfile 导入失败
```bash
pip install soundfile
# 或者
pip install pysoundfile
```

### 问题2：VAD 模型加载失败
- 检查网络连接（首次使用会自动下载模型）
- 确认 FunASR 库版本正确

### 问题3：处理速度慢
- 确认使用了 GPU：`cuda:0`
- 减少 `max_single_segment_time` 参数值
- 增加 `batch_size_s` 参数值

## 📚 参考代码

完整实现请查看：`backend/devour/asr_engine_paraformer.py`
