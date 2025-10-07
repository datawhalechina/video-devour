# VideoDevour ASR Paraformer V2 引擎说明

## 📋 概述

`asr_engine_paraformer_v2.py` 是基于 FunASR Paraformer 模型的语音识别引擎，专为 VideoDevour 项目设计。相比原版，V2 版本采用了更标准化的输出格式，便于后续处理和分析。

## ✨ 主要特性

- ✅ **本地模型优先**：优先使用项目 `models` 目录下的本地模型
- ✅ **自动降级**：本地模型不存在时自动使用远程模型
- ✅ **VAD 支持**：语音活动检测，自动分段
- ✅ **标点恢复**：自动添加标点符号
- ✅ **说话人分离**：识别不同说话人（CAM++ 模型）
- ✅ **标准化输出**：统一的 JSON 格式输出
- ✅ **批量处理**：支持目录级批量视频处理
- ✅ **详细统计**：提供文本统计信息

## 📦 所需模型

所有模型应放置在项目根目录的 `models/models/iic/` 下：

```
models/
└── models/
    └── iic/
        ├── speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn/    # 主模型
        ├── speech_fsmn_vad_zh-cn-16k-common-pytorch/               # VAD 模型
        ├── punc_ct-transformer_cn-en-common-vocab471067-large/    # 标点模型
        └── speech_campplus_sv_zh-cn_16k-common/                   # 说话人模型
```

### 模型下载

如果本地模型不存在，程序会自动从 ModelScope 下载以下模型：
- `paraformer-zh` (v2.0.4)
- `fsmn-vad` (v2.0.4)
- `ct-punc-c` (v2.0.4)
- `cam++`

## 📤 输出格式

### 标准化输出结构

```json
[
  {
    "transcript": [
      {
        "index": 1,
        "spk_id": "spk0",
        "sentence": "大家好，欢迎来到今天的课程。",
        "start_time": 0.0,
        "end_time": 2500.0
      },
      {
        "index": 2,
        "spk_id": "spk1",
        "sentence": "今天我们要学习语音识别技术。",
        "start_time": 2500.0,
        "end_time": 5200.0
      }
    ],
    "video_path": "input_video/example.mp4",
    "processed_at": "2025-10-06T10:30:00.123456",
    "text_stats": {
      "total_segments": 150,
      "total_words": 1200,
      "total_chars": 3500,
      "avg_segment_duration": 2800.5
    }
  }
]
```

### 字段说明

#### transcript (转录结果数组)
- `index`: 句子序号（从 1 开始）
- `spk_id`: 说话人 ID（例如 "spk0", "spk1" 等）
- `sentence`: 识别的文本内容（已添加标点）
- `start_time`: 开始时间（单位：毫秒）
- `end_time`: 结束时间（单位：毫秒）

#### text_stats (统计信息)
- `total_segments`: 总句子数
- `total_words`: 总词数
- `total_chars`: 总字符数
- `avg_segment_duration`: 平均句子时长（毫秒）

## 🚀 使用方法

### 1. 单个视频处理

```python
from backend.devour.asr_engine_paraformer_v2 import VideoDevourASRParaformerV2

# 初始化引擎
asr = VideoDevourASRParaformerV2()

# 处理单个视频
result = asr.devour_video("path/to/video.mp4")

# 保存结果
asr.save_results([result], "output/result.json")
```

### 2. 批量处理

```python
from backend.devour.asr_engine_paraformer_v2 import VideoDevourASRParaformerV2

# 初始化引擎
asr = VideoDevourASRParaformerV2()

# 批量处理视频目录
results = asr.process_videos("input_video")

# 保存结果
asr.save_results(results, "output/asr_results_paraformer_v2.json")
```

### 3. 命令行测试

```bash
# 进入项目根目录
cd VideoDevour

# 运行测试（会处理 input_video 目录下的所有视频）
python backend/devour/asr_engine_paraformer_v2.py
```

## 📊 输出示例

运行后会在控制台输出详细的处理日志：

```
2025-10-06 10:30:00 - INFO - 🍽️ VideoDevour ASR Paraformer V2 引擎测试开始
2025-10-06 10:30:01 - INFO - 使用设备: cuda:0
2025-10-06 10:30:05 - INFO - 找到 1 个视频文件
2025-10-06 10:30:05 - INFO - 开始处理视频: input_video/example.mp4
2025-10-06 10:30:06 - INFO - 正在提取音频: input_video/example.mp4
2025-10-06 10:30:10 - INFO - 音频提取完成: /tmp/tmpxxxx.wav
2025-10-06 10:30:10 - INFO - 正在进行语音识别...
2025-10-06 10:32:15 - INFO - 规范化完成，共 150 个句子
2025-10-06 10:32:15 - INFO - ✅ 完成: example.mp4

📊 处理摘要:
✅ 成功处理: 1 个视频

  1. example.mp4
     段落数: 150
     字数: 1200
     字符数: 3500
     平均段落时长: 2800.50 ms
     说话人数: 2
     说话人 ID: spk0, spk1

📈 总体统计:
     总段落数: 150
     总字数: 1200
     总字符数: 3500
     平均段落长度: 23.3 字符

🎉 测试完成！结果已保存到: output/asr_results_paraformer_v2.json
```

## 🔧 配置说明

引擎会读取项目根目录下的 `config.yaml` 配置文件。确保配置文件存在且格式正确。

## ⚙️ 高级参数

### 热词设置

可以在 `devour_video` 方法中设置热词，提高特定词汇的识别准确率：

```python
res = self.asr_model.generate(
    input=wav_path,
    batch_size_s=300,
    hotword="魔搭 语音识别 深度学习",  # 多个热词用空格分隔
)
```

### 批处理大小

通过 `batch_size_s` 参数调整批处理大小（单位：秒）：
- 较小值（如 60）：内存占用少，但处理较慢
- 较大值（如 300）：处理更快，但需要更多内存

## 🆚 与其他引擎的对比

| 特性 | Paraformer V2 | SenseVoice | Whisper |
|------|---------------|------------|---------|
| 说话人分离 | ✅ | ❌ | ❌ |
| 标点恢复 | ✅ | ✅ | ❌ |
| VAD 分段 | ✅ | ✅ | ✅ |
| 中文优化 | ✅✅ | ✅✅ | ✅ |
| 多语言 | ❌ | ✅ | ✅✅ |
| 输出格式 | 标准化 | 片段化 | 片段化 |
| 处理速度 | 快 | 快 | 中等 |

## 📝 注意事项

1. **GPU 推荐**：模型推理建议使用 GPU，CPU 模式会明显变慢
2. **内存占用**：长视频可能需要较大内存，建议至少 8GB RAM
3. **音频格式**：自动转换为 16kHz WAV 格式
4. **临时文件**：处理过程中会创建临时音频文件，完成后自动清理
5. **说话人 ID**：说话人 ID 格式为 "spk0", "spk1" 等，不包含实际姓名

## 🐛 故障排除

### 问题：模型加载失败
```
解决方案：
1. 检查 models 目录结构是否正确
2. 确保网络连接正常（首次使用需要下载模型）
3. 检查 CUDA 版本是否兼容（如使用 GPU）
```

### 问题：音频提取失败
```
解决方案：
1. 确保 ffmpeg 已正确安装
2. 检查视频文件是否损坏
3. 确保有足够的磁盘空间存储临时文件
```

### 问题：说话人识别不准确
```
解决方案：
1. 确保音频质量良好
2. 说话人之间需要有明显的声音差异
3. 背景噪音会影响识别准确率
```

## 📄 许可证

本项目遵循 MIT 许可证。

## 🔗 相关链接

- [FunASR GitHub](https://github.com/alibaba-damo-academy/FunASR)
- [ModelScope](https://www.modelscope.cn/)
- [Paraformer 模型介绍](https://www.modelscope.cn/models/iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn)

## 📮 技术支持

如有问题或建议，请提交 Issue。

