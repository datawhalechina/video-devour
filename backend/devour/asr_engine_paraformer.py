import torch
from pyannote.audio import Pipeline
from moviepy import VideoFileClip
import tempfile
import logging
import os
from pathlib import Path
import yaml
import json
from datetime import datetime
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import soundfile as sf  # 用于读取和裁剪音频文件
import sys

# 添加算法模块路径
sys.path.append(str(Path(__file__).parent.parent / "algorithm"))
from modelscope_manager import ModelScopeManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoDevourASRFunasr:
    def __init__(self):
        config_file = Path(__file__).parent.parent.parent / 'config.yaml'
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件未找到: {config_file}")
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        # SenseVoice 推荐使用 "cuda:0" 格式
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logging.info(f"使用设备: {self.device}")
        self._diarization_pipeline = None 
        self._asr_model = None
        self._vad_model = None  # VAD 模型单独加载
        
        # 获取项目根目录
        self.project_root = Path(__file__).resolve().parent.parent.parent
        
        # 初始化 ModelScope 管理器
        self.model_manager = ModelScopeManager(str(self.project_root))
        
        # 自动检查和下载缺失的模型
        self._ensure_models_available()
    
    def _ensure_models_available(self):
        """
        确保所需的模型都可用，如果缺失则自动下载
        """
        try:
            missing_models = self.model_manager.get_missing_models()
            
            if missing_models:
                logging.info(f"检测到缺失模型: {missing_models}")
                logging.info("正在自动下载缺失的模型...")
                
                # 下载缺失的模型
                results = self.model_manager.download_all_missing_models()
                
                # 检查下载结果
                failed_models = [model for model, success in results.items() if not success]
                if failed_models:
                    logging.warning(f"以下模型下载失败: {failed_models}")
                    logging.warning("将使用远程模型作为备选方案")
                else:
                    logging.info("所有缺失模型下载完成")
            else:
                logging.info("所有必需模型都已存在")
                
        except Exception as e:
            logging.warning(f"模型检查过程中出现错误: {str(e)}")
            logging.warning("将使用远程模型作为备选方案")
        
    @property
    def vad_model(self):
        """加载 VAD 模型（用于音频分段）"""
        if self._vad_model is None:
            logging.info("正在加载 VAD 模型...")
            try:
                self._vad_model = AutoModel(
                    model="fsmn-vad",
                    trust_remote_code=True,
                    device=self.device,
                    disable_update=True,
                )
                logging.info(f"VAD 模型加载完成（设备: {self.device}）")
            except Exception as e:
                logging.error(f"VAD 模型加载失败: {str(e)}")
                raise
        return self._vad_model
    
    @property
    def asr_model(self):
        """加载 SenseVoice 模型（不包含 VAD）"""
        if self._asr_model is None:
            logging.info("正在加载本地 SenseVoice 模型...")
            # 动态构建模型的本地路径，增强代码可移植性
            project_root = Path(__file__).resolve().parent.parent.parent
            model_path = project_root / "models/models/iic/SenseVoiceSmall"
            
            if not model_path.exists():
                logging.warning(f"本地SenseVoice模型路径不存在: {model_path}，将从远程加载")
                # 如果本地模型不存在，使用远程模型
                model_dir = "iic/SenseVoiceSmall"
            else:
                model_dir = str(model_path)

            # 加载SenseVoice模型（不包含 VAD，因为 VAD 单独处理）
            self._asr_model = AutoModel(
                model=model_dir,
                trust_remote_code=True,
                device=self.device,
                disable_update=True,
                # spk_model="cam++",
            )
            logging.info(f"SenseVoice 模型加载完成（设备: {self.device}）")
        return self._asr_model
        
    @property
    def diarization_pipeline(self):
        """说话人识别管道（可选）"""
        project_root = Path(__file__).resolve().parent.parent.parent
        vad_model_path = project_root / "models/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
        paraformer_model_path = project_root / "models/models/iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn"
        punc_model_path = project_root / "models/models/iic/punc_ct-transformer_cn-en-common-vocab471067-large"
        if self._diarization_pipeline is None:
            try:
                logging.info("正在加载说话人识别模型...")
                # 配置说话人识别参数以优化性能
                self._diarization_pipeline = AutoModel(
                    model="cam++",
                    vad_model=str(vad_model_path),
                    vad_kwargs={"max_single_segment_time": 30000},
                    punc_model=str(punc_model_path),
                    device=self.device,
                )
    
                logging.info(f"说话人识别模型加载完成（设备: {self.device}）")
            except Exception as e:
                logging.error(f"说话人识别模型加载失败: {str(e)}")
                logging.warning("跳过说话人识别，继续处理")
                self._diarization_pipeline = None
                
        return self._diarization_pipeline
        
    def extract_audio(self, video_path: str) -> str:
        """提取视频音频到临时wav文件"""
        logging.info(f"正在提取音频: {video_path}")
        try:
            with VideoFileClip(video_path) as video:
                audio = video.audio
                temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                audio.write_audiofile(temp_wav.name, codec="pcm_s16le", fps=16000)
                logging.info(f"音频提取完成: {temp_wav.name}")
                return temp_wav.name
        except Exception as e:
            logging.error(f"音频提取失败: {str(e)}")
            raise
    
    def crop_audio(self, audio_data, start_time, end_time, sample_rate):
        """
        裁剪音频片段
        
        Args:
            audio_data: 音频数据数组
            start_time: 开始时间（毫秒）
            end_time: 结束时间（毫秒）
            sample_rate: 采样率
            
        Returns:
            裁剪后的音频数据
        """
        start_sample = int(start_time * sample_rate / 1000)  # 转换为样本数
        end_sample = int(end_time * sample_rate / 1000)  # 转换为样本数
        return audio_data[start_sample:end_sample]

    def devour_video(self, video_path: str) -> dict:
        """核心吞噬方法 - 使用两阶段识别（VAD分段 + SenseVoice识别）"""
        logging.info(f"开始处理视频: {video_path}")
        
        try:
            # 音频提取
            wav_path = self.extract_audio(video_path)
            
            # 第一阶段：使用 VAD 模型进行音频分段
            logging.info("第一阶段：使用 VAD 模型进行音频分段...")
            vad_res = self.vad_model.generate(
                input=wav_path,
                cache={},
                max_single_segment_time=30000,  # 最大单个片段时长（毫秒）
            )
            
            # 从 VAD 模型的输出中提取每个语音片段的开始和结束时间
            if not vad_res or len(vad_res) == 0:
                logging.error("VAD 模型未返回有效结果")
                raise ValueError("VAD 分段失败")
            
            segments_vad = vad_res[0].get('value', [])
            logging.info(f"VAD 检测到 {len(segments_vad)} 个语音片段")
            
            # 加载原始音频数据
            audio_data, sample_rate = sf.read(wav_path)
            logging.info(f"音频采样率: {sample_rate} Hz")
            
            # 第二阶段：对每个 VAD 片段使用 SenseVoice 进行识别
            logging.info("第二阶段：使用 SenseVoice 对每个片段进行识别...")
            segments = []
            temp_audio_file = None
            
            for i, segment in enumerate(segments_vad):
                start_time, end_time = segment  # 获取开始和结束时间（毫秒）
                
                # 裁剪音频
                cropped_audio = self.crop_audio(audio_data, start_time, end_time, sample_rate)
                
                # 将裁剪后的音频保存为临时文件
                temp_audio_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                sf.write(temp_audio_file, cropped_audio, sample_rate)
                
                try:
                    # 使用 SenseVoice 进行语音识别
                    res = self.asr_model.generate(
                        input=temp_audio_file,
                        cache={},
                        language="auto",  # "zh", "en", "yue", "ja", "ko", "nospeech"
                        use_itn=True,  # 使用逆文本规范化
                        batch_size_s=60,
                    )
                    
                    # 处理识别结果
                    if isinstance(res, list) and len(res) > 0 and "text" in res[0]:
                        text = rich_transcription_postprocess(res[0]["text"])
                        print(res)
                        # 添加时间戳（转换为秒）
                        segments.append({
                            "id": i,
                            "start": start_time / 1000.0,  # 毫秒转秒
                            "end": end_time / 1000.0,      # 毫秒转秒
                            "text": text.strip()
                        })
                        
                        logging.info(f"  片段 {i+1}/{len(segments_vad)}: {start_time/1000:.1f}s - {end_time/1000:.1f}s, 文本长度: {len(text)}")
                    else:
                        logging.warning(f"  片段 {i+1} 识别结果为空")
                        
                except Exception as e:
                    logging.warning(f"  片段 {i+1} 识别失败: {str(e)}")
                    continue
                finally:
                    # 清理临时文件
                    if temp_audio_file and os.path.exists(temp_audio_file):
                        try:
                            os.unlink(temp_audio_file)
                        except:
                            pass
            
            # 检测语言（从第一个有效结果中获取）
            language = "auto"
            if segments:
                logging.info(f"转写完成，共识别 {len(segments)} 个有效片段")
            else:
                logging.warning("未识别到任何有效片段")
            
            # 说话人识别（可选）
            diarization = None
            if self.diarization_pipeline is not None:
                logging.info("开始说话人识别...")
                try:
                    # 使用新的Paraformer模型进行说话人识别
                    diarization_result = self.diarization_pipeline.generate(input=wav_path, batch_size_s=60, batch_size_threshold_s=60)
                    
                    # 处理识别结果
                    if diarization_result and len(diarization_result) > 0:
                        diarization = diarization_result[0] if "spk_segment" in diarization_result[0] else None
                        if diarization:
                            logging.info("说话人识别完成")
                        else:
                            logging.info("说话人识别完成 - 未检测到说话人")
                    else:
                        logging.info("说话人识别完成 - 未检测到说话人")
                        
                except Exception as e:
                    logging.warning(f"说话人识别失败: {str(e)}")
                    logging.warning("继续处理，跳过说话人识别")
            else:
                logging.info("跳过说话人识别（模型未加载）")
            
            # 清理临时文件
            try:
                os.unlink(wav_path)
            except:
                pass
                
            return {
                "transcript": segments,
                "speakers": diarization,
                "language": language,
                "video_path": video_path,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"ASR处理失败: {str(e)}")
            # 尝试清理临时文件
            try:
                if 'wav_path' in locals():
                    os.unlink(wav_path)
            except:
                pass
            raise

    def process_videos(self, video_dir: str) -> list:
        """批量处理视频目录"""
        video_dir = Path(video_dir)
        if not video_dir.exists():
            raise FileNotFoundError(f"视频目录不存在: {video_dir}")
            
        # 查找视频文件
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm']
        video_files = []
        for ext in video_extensions:
            video_files.extend(video_dir.glob(f"*{ext}"))
            
        if not video_files:
            raise FileNotFoundError(f"未找到视频文件: {video_dir}")
            
        logging.info(f"找到 {len(video_files)} 个视频文件")
        
        results = []
        for video_file in video_files:
            try:
                result = self.devour_video(str(video_file))
                results.append(result)
                logging.info(f"✅ 完成: {video_file.name}")
            except Exception as e:
                logging.error(f"❌ 失败: {video_file.name} - {str(e)}")
                continue
                
        return results
        
    def save_results(self, results: list, output_file: str):
        """保存处理结果到JSON文件"""
        # 转换speakers对象为可序列化格式
        for result in results:
            if 'speakers' in result and result['speakers'] is not None:
                # 处理新的Paraformer模型的说话人识别结果
                if isinstance(result['speakers'], dict) and 'spk_segment' in result['speakers']:
                    speakers_data = []
                    try:
                        # 处理说话人分段信息
                        for segment in result['speakers']['spk_segment']:
                            speakers_data.append({
                                "speaker": segment.get('spk', 'UNKNOWN'),
                                "start": float(segment.get('start', 0)),
                                "end": float(segment.get('end', 0)),
                                "duration": float(segment.get('end', 0) - segment.get('start', 0))
                            })
                        result['speakers'] = speakers_data
                    except Exception as e:
                        logging.warning(f"说话人数据转换失败: {str(e)}")
                        result['speakers'] = str(result['speakers'])
                # 保持对旧格式的兼容性
                elif hasattr(result['speakers'], 'itertracks'):
                    # 提取说话人时间轴信息为结构化数据
                    speakers_data = []
                    try:
                        for turn, _, speaker in result['speakers'].itertracks(yield_label=True):
                            speakers_data.append({
                                "speaker": speaker,
                                "start": float(turn.start),
                                "end": float(turn.end),
                                "duration": float(turn.end - turn.start)
                            })
                        result['speakers'] = speakers_data
                    except Exception as e:
                        logging.warning(f"说话人数据转换失败: {str(e)}")
                        result['speakers'] = str(result['speakers'])
                else:
                    # 如果是其他格式，直接转换为字符串
                    result['speakers'] = str(result['speakers'])
            
            # 统计转录文本质量指标
            if 'transcript' in result and result['transcript']:
                total_text = " ".join([segment.get('text', '') for segment in result['transcript']])
                result['text_stats'] = {
                    "total_segments": len(result['transcript']),
                    "total_words": len(total_text.split()),
                    "total_chars": len(total_text),
                    "avg_segment_duration": sum([seg.get('end', 0) - seg.get('start', 0) for seg in result['transcript']]) / len(result['transcript']) if result['transcript'] else 0
                }
                
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logging.info(f"结果已保存到: {output_file}")


if __name__ == "__main__":
    # 测试ASR引擎
    logging.info("🍽️ VideoDevour ASR Funasr引擎测试开始")
    
    try:
        # 初始化ASR引擎
        asr = VideoDevourASRFunasr()
        
        # 处理视频目录
        # Get the project root directory (assuming this file is in backend/devour)
        project_root = Path(__file__).resolve().parent.parent.parent
        video_dir = project_root / "input_video"
        results = asr.process_videos(str(video_dir))
        
        # 保存结果
        output_file = project_root / "output" / "asr_results_sensevoice.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        asr.save_results(results, str(output_file))
        
        # 打印摘要
        logging.info(f"\n📊 处理摘要:")
        logging.info(f"✅ 成功处理: {len(results)} 个视频")
        
        total_segments = 0
        total_words = 0
        total_chars = 0
        
        for i, result in enumerate(results, 1):
            logging.info(f"  {i}. {Path(result['video_path']).name}")
            logging.info(f"     语言: {result['language']}")
            logging.info(f"     段落数: {len(result['transcript'])}")
            
            # 统计文本信息
            if 'text_stats' in result:
                stats = result['text_stats']
                total_segments += stats['total_segments']
                total_words += stats['total_words'] 
                total_chars += stats['total_chars']
                logging.info(f"     字数: {stats['total_words']}, 字符数: {stats['total_chars']}")
            
            # 说话人信息
            if result.get('speakers'):
                if isinstance(result['speakers'], list):
                    unique_speakers = len(set(s['speaker'] for s in result['speakers']))
                    logging.info(f"     说话人: {unique_speakers} 位")
                else:
                    logging.info(f"     说话人: 数据可用")
        
        # 总体统计
        if total_segments > 0:
            logging.info(f"\n📈 总体统计:")
            logging.info(f"     总段落数: {total_segments}")
            logging.info(f"     总字数: {total_words}")
            logging.info(f"     总字符数: {total_chars}")
            logging.info(f"     平均段落长度: {total_chars/total_segments:.1f} 字符")
            
    except Exception as e:
        logging.error(f"测试失败: {str(e)}")
        exit(1)