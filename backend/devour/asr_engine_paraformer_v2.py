# -*- coding: utf-8 -*-
"""
VideoDevour ASR Engine - Paraformer V2
使用 FunASR Paraformer 模型进行语音识别，支持 VAD、标点、说话人分离
"""

import torch
from moviepy import VideoFileClip
import tempfile
import logging
import os
from pathlib import Path
import yaml
import json
from datetime import datetime
from funasr import AutoModel
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class VideoDevourASRParaformerV2:
    """
    VideoDevour ASR 引擎 - Paraformer V2 版本
    
    功能特性：
    - 使用本地 Paraformer 模型
    - 支持 VAD（语音活动检测）
    - 支持标点符号恢复
    - 支持说话人分离
    - 标准化输出格式
    """
    
    def __init__(self):
        """
        初始化 ASR 引擎
        
        加载配置文件并设置设备
        """
        # 加载配置文件
        config_file = Path(__file__).parent.parent.parent / 'config.yaml'
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件未找到: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 设置设备
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logging.info(f"使用设备: {self.device}")
        
        # 延迟加载模型
        self._asr_model = None
        
        # 获取项目根目录
        self.project_root = Path(__file__).resolve().parent.parent.parent
    
    @property
    def asr_model(self) -> AutoModel:
        """
        加载 Paraformer 模型（含 VAD、标点、说话人分离）
        
        Returns:
            AutoModel: 已加载的 FunASR 模型实例
        """
        if self._asr_model is None:
            logging.info("正在加载 Paraformer 模型（含 VAD / 标点 / 说话人分离）...")
            
            # 构建本地模型路径
            paraformer_path = self.project_root / "models/models/iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn"
            vad_path = self.project_root / "models/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
            punc_path = self.project_root / "models/models/iic/punc_ct-transformer_cn-en-common-vocab471067-large"
            cam_path = self.project_root / "models/models/iic/speech_campplus_sv_zh-cn_16k-common"
            
            # 检查模型是否存在
            if not paraformer_path.exists():
                logging.warning(f"本地 Paraformer 模型不存在: {paraformer_path}")
                logging.info("将使用远程模型 'paraformer-zh'")
                paraformer_model = "paraformer-zh"
            else:
                paraformer_model = str(paraformer_path)
                logging.info(f"使用本地 Paraformer 模型: {paraformer_path}")
            
            if not vad_path.exists():
                logging.warning(f"本地 VAD 模型不存在: {vad_path}")
                vad_model = "fsmn-vad"
            else:
                vad_model = str(vad_path)
                logging.info(f"使用本地 VAD 模型: {vad_path}")
            
            if not punc_path.exists():
                logging.warning(f"本地标点模型不存在: {punc_path}")
                punc_model = "ct-punc-c"
            else:
                punc_model = str(punc_path)
                logging.info(f"使用本地标点模型: {punc_path}")
            
            if not cam_path.exists():
                logging.warning(f"本地说话人模型不存在: {cam_path}")
                spk_model = "cam++"
            else:
                spk_model = str(cam_path)
                logging.info(f"使用本地说话人模型: {cam_path}")
            
            try:
                # 加载 Paraformer 模型
                self._asr_model = AutoModel(
                    model=paraformer_model,
                    model_revision="v2.0.4",
                    vad_model=vad_model,
                    vad_model_revision="v2.0.4",
                    punc_model=punc_model,
                    punc_model_revision="v2.0.4",
                    spk_model=spk_model,
                    device=self.device,
                    disable_update=True,
                )
                logging.info(f"Paraformer 模型加载完成（设备: {self.device}）")
            except Exception as e:
                logging.error(f"Paraformer 模型加载失败: {str(e)}")
                raise
        
        return self._asr_model
    
    def extract_audio(self, video_path: str) -> str:
        """
        从视频文件中提取音频
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            str: 临时音频文件路径（WAV 格式，16kHz）
        """
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
    
    def normalize_result(self, res: List[Dict]) -> List[Dict]:
        """
        将 FunASR 的推理结果规范化为标准格式
        
        Args:
            res: FunASR 模型的原始输出结果
            
        Returns:
            List[Dict]: 标准化后的结果列表
                [
                    {
                        "index": 1,
                        "spk_id": "spk0",
                        "sentence": "你好，世界！",
                        "start_time": 0.0,  # 单位：秒
                        "end_time": 1500.0   # 单位：秒
                    },
                    ...
                ]
        """
        if not res:
            logging.warning("ASR 结果为空")
            return []
        
        item = res[0]
        
        # 优先读取逐句字段 sentence_info
        sentence_info = item.get("sentence_info")
        if sentence_info is None:
            logging.error("ASR 结果缺少 sentence_info 字段")
            raise ValueError("无法处理的 ASR 结果格式，缺少 sentence_info 字段")
        
        # 获取默认说话人 ID（如果句级没有 spk 字段）
        spk_default: Optional[str] = None
        if "spk_id" in item and item["spk_id"] is not None:
            spk_default = str(item["spk_id"])
        elif "spk" in item and item["spk"] is not None:
            spk_default = str(item["spk"])
        
        results: List[Dict] = []
        for idx, s in enumerate(sentence_info, start=1):
            sent_text = (s.get("text") or "").strip()
            
            # 提取时间戳（单位：秒）
            try:
                st = float(s.get("start", 0.0))
            except Exception:
                st = 0.0
            
            try:
                ed = float(s.get("end", st))
            except Exception:
                ed = st
            
            # 提取说话人 ID
            spk_local = s.get("spk_id", s.get("spk", None))
            spk_val = str(spk_local) if spk_local is not None else spk_default
            
            results.append({
                "index": idx,
                "spk_id": spk_val,
                "sentence": sent_text,
                "start_time": float(st)/1000,
                "end_time": float(ed)/1000,
            })
        
        logging.info(f"规范化完成，共 {len(results)} 个句子")
        return results
    
    def devour_video(self, video_path: str) -> Dict:
        """
        核心处理方法 - 对视频进行语音识别
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Dict: 包含识别结果的字典
                {
                    "transcript": [...],  # 标准化的转录结果
                    "video_path": str,
                    "processed_at": str,
                    "text_stats": {...}   # 统计信息
                }
        """
        logging.info(f"开始处理视频: {video_path}")
        
        try:
            # 提取音频
            wav_path = self.extract_audio(video_path)
            
            # 使用 Paraformer 进行识别
            logging.info("正在进行语音识别...")
            res = self.asr_model.generate(
                input=wav_path,
                batch_size_s=300,  # 批处理大小（秒）
                hotword="魔搭",     # 热词（可选）
            )
            
            # 规范化结果
            transcript = self.normalize_result(res)
            
            # 清理临时文件
            try:
                os.unlink(wav_path)
            except:
                pass
            
            # 计算统计信息
            text_stats = {}
            if transcript:
                total_text = " ".join([seg.get('sentence', '') for seg in transcript])
                text_stats = {
                    "total_segments": len(transcript),
                    "total_words": len(total_text.split()),
                    "total_chars": len(total_text),
                    "avg_segment_duration": sum([
                        seg.get('end_time', 0) - seg.get('start_time', 0) 
                        for seg in transcript
                    ]) / len(transcript),
                }
            
            return {
                "transcript": transcript,
                "video_path": video_path,
                "processed_at": datetime.now().isoformat(),
                "text_stats": text_stats,
            }
            
        except Exception as e:
            logging.error(f"ASR 处理失败: {str(e)}")
            # 尝试清理临时文件
            try:
                if 'wav_path' in locals():
                    os.unlink(wav_path)
            except:
                pass
            raise
    
    def process_videos(self, video_dir: str) -> List[Dict]:
        """
        批量处理视频目录
        
        Args:
            video_dir: 视频目录路径
            
        Returns:
            List[Dict]: 所有视频的处理结果列表
        """
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
    
    def save_results(self, results: List[Dict], output_file: str):
        """
        保存处理结果到 JSON 文件
        
        Args:
            results: 处理结果列表
            output_file: 输出文件路径
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logging.info(f"结果已保存到: {output_file}")


def main():
    """
    主函数 - 测试 ASR 引擎
    """
    logging.info("🍽️ VideoDevour ASR Paraformer V2 引擎测试开始")
    
    try:
        # 初始化 ASR 引擎
        asr = VideoDevourASRParaformerV2()
        
        # 处理视频目录
        project_root = Path(__file__).resolve().parent.parent.parent
        video_dir = project_root / "input_video"
        results = asr.process_videos(str(video_dir))
        
        # 保存结果
        output_file = project_root / "output" / "asr_results_paraformer_v2.json"
        asr.save_results(results, str(output_file))
        
        # 打印摘要
        logging.info(f"\n📊 处理摘要:")
        logging.info(f"✅ 成功处理: {len(results)} 个视频")
        
        total_segments = 0
        total_words = 0
        total_chars = 0
        
        for i, result in enumerate(results, 1):
            logging.info(f"\n  {i}. {Path(result['video_path']).name}")
            
            # 统计文本信息
            if 'text_stats' in result:
                stats = result['text_stats']
                total_segments += stats['total_segments']
                total_words += stats['total_words']
                total_chars += stats['total_chars']
                
                logging.info(f"     段落数: {stats['total_segments']}")
                logging.info(f"     字数: {stats['total_words']}")
                logging.info(f"     字符数: {stats['total_chars']}")
                logging.info(f"     平均段落时长: {stats['avg_segment_duration']:.2f} ms")
            
            # 统计说话人信息
            if result.get('transcript'):
                speakers = set(seg.get('spk_id') for seg in result['transcript'] if seg.get('spk_id'))
                if speakers:
                    logging.info(f"     说话人数: {len(speakers)}")
                    logging.info(f"     说话人 ID: {', '.join(sorted(speakers))}")
        
        # 总体统计
        if total_segments > 0:
            logging.info(f"\n📈 总体统计:")
            logging.info(f"     总段落数: {total_segments}")
            logging.info(f"     总字数: {total_words}")
            logging.info(f"     总字符数: {total_chars}")
            logging.info(f"     平均段落长度: {total_chars/total_segments:.1f} 字符")
        
        logging.info(f"\n🎉 测试完成！结果已保存到: {output_file}")
        
    except Exception as e:
        logging.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

