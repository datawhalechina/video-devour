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

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoDevourASRFunasr:
    def __init__(self):
        config_file = Path(__file__).parent.parent.parent / 'config.yaml'
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件未找到: {config_file}")
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"使用设备: {self.device}")
        self._diarization_pipeline = None 
        self._asr_model = None
        
    @property
    def asr_model(self):
        if self._asr_model is None:
            logging.info("正在加载本地Paraformer模型...")
            # 动态构建模型的本地路径，增强代码可移植性
            project_root = Path(__file__).resolve().parent.parent.parent
            model_path = project_root / "models/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
            vad_model_path = project_root / "models/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
            punc_model_path = project_root / "models/models/iic/punc_ct-transformer_cn-en-common-vocab471067-large"
            paraformer_model_path = project_root / "models/models/iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn"
            if not model_path.exists():
                logging.error(f"ASR模型路径不存在: {model_path}")
                raise FileNotFoundError(f"指定的ASR模型路径不存在: {model_path}")
            if not vad_model_path.exists():
                logging.error(f"VAD模型路径不存在: {vad_model_path}")
                raise FileNotFoundError(f"指定的VAD模型路径不存在: {vad_model_path}")
            if not punc_model_path.exists():
                logging.error(f"PUNC模型路径不存在: {punc_model_path}")
                raise FileNotFoundError(f"指定的PUNC模型路径不存在: {punc_model_path}")

            # 加载Paraformer模型
            self._asr_model = AutoModel(
                model=str(model_path),
                vad_model=str(vad_model_path),
                vad_kwargs={"max_single_segment_time": 30000},
                punc_model=str(punc_model_path),
                device=self.device,
                disable_update=True,
            )
            logging.info(f"Paraformer模型加载完成（设备: {self.device}）")
        return self._asr_model
        
    @property
    def diarization_pipeline(self):
        vad_model_path = project_root / "models/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
        paraformer_model_path = project_root / "models/models/iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn"
        punc_model_path = project_root / "models/models/iic/punc_ct-transformer_cn-en-common-vocab471067-large"
        if self._diarization_pipeline is None:
            # 优先从配置文件读取HF_TOKEN，其次从环境变量读取
            hf_token = self.config.get('HF_TOKEN') or os.environ.get('HF_TOKEN')
            if not hf_token:
                logging.warning("HF_TOKEN未设置，跳过说话人识别")
                return None
                
            try:
                logging.info("正在加载说话人识别模型...")
                # 配置说话人识别参数以优化性能
                self._diarization_pipeline = AutoModel(
                    model=str(paraformer_model_path),
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

    def devour_video(self, video_path: str) -> dict:
        """核心吞噬方法 - 处理单个视频"""
        logging.info(f"开始处理视频: {video_path}")
        
        try:
            # 音频提取
            wav_path = self.extract_audio(video_path)
            
            # 语音转写
            logging.info("开始语音转写...")
            
            # 使用Paraformer进行语音识别
            res = self.asr_model.generate(
                input=wav_path,
                batch_size_s=60,
                batch_size_threshold_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
            
            # 处理结果
            if isinstance(res, list) and len(res) > 0:
                text = rich_transcription_postprocess(res[0]["text"])
                segments = []
                # 如果结果包含时间戳信息
                if "timestamp" in res[0]:
                    for i, (start, end) in enumerate(res[0]["timestamp"]):
                        segments.append({
                            "id": i,
                            "start": start / 1000.0,  # 转换为秒
                            "end": end / 1000.0,      # 转换为秒
                            "text": res[0]["text"].split()[i] if i < len(res[0]["text"].split()) else ""
                        })
                else:
                    # 如果没有时间戳信息，创建一个简单的段落
                    segments.append({
                        "id": 0,
                        "start": 0.0,
                        "end": 0.0,
                        "text": text
                    })
            else:
                text = ""
                segments = []
            
            language = "zh"  # Paraformer-zh是中文模型
            logging.info(f"转写完成，检测到语言: {language}")
            logging.info(f"转录段落数: {len(segments)}")
            
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
        output_file = project_root / "output" / "asr_results_paraformer.json"
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