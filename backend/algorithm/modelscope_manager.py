# -*- coding: utf-8 -*-
"""
ModelScope 模型下载管理器

自动检测和下载项目所需的 ModelScope 模型，确保本地模型可用性。
支持断点续传、进度显示和错误重试。
"""

import os
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ModelScopeManager:
    """
    ModelScope 模型下载管理器
    
    功能特性：
    - 自动检测本地模型是否存在
    - 从 ModelScope 下载缺失的模型
    - 支持断点续传和进度显示
    - 错误重试机制
    - 模型版本管理
    """
    
    # 项目所需的模型配置
    REQUIRED_MODELS = {
        "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch": {
            "model_id": "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            "revision": "v2.0.4",
            "local_path": "models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            "description": "Paraformer 大模型语音识别",
            "size_gb": 1.2
        },
        "speech_fsmn_vad_zh-cn-16k-common-pytorch": {
            "model_id": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            "revision": "v2.0.4", 
            "local_path": "models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            "description": "FSMN VAD 语音活动检测",
            "size_gb": 0.1
        },
        "punc_ct-transformer_cn-en-common-vocab471067-large": {
            "model_id": "iic/punc_ct-transformer_cn-en-common-vocab471067-large",
            "revision": "v2.0.4",
            "local_path": "models/iic/punc_ct-transformer_cn-en-common-vocab471067-large", 
            "description": "CT-Transformer 标点符号恢复",
            "size_gb": 0.5
        },
        "speech_campplus_sv_zh-cn_16k-common": {
            "model_id": "iic/speech_campplus_sv_zh-cn_16k-common",
            "revision": "v2.0.2",  # 修改为可用版本
            "local_path": "models/iic/speech_campplus_sv_zh-cn_16k-common",
            "description": "CAM++ 说话人分离",
            "size_gb": 0.3
        },
        "SenseVoiceSmall": {
            "model_id": "iic/SenseVoiceSmall",
            "revision": "master",
            "local_path": "models/iic/SenseVoiceSmall",
            "description": "SenseVoice 小模型语音识别",
            "size_gb": 0.8
        }
    }
    
    def __init__(self, project_root: Optional[str] = None):
        """
        初始化模型管理器
        
        Args:
            project_root: 项目根目录路径，如果为 None 则自动检测
        """
        if project_root is None:
            # 自动检测项目根目录
            self.project_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.project_root = Path(project_root)
            
        self.models_dir = self.project_root / "models"
        
        logging.info(f"ModelScope 管理器初始化完成")
        logging.info(f"项目根目录: {self.project_root}")
        logging.info(f"模型存储目录: {self.models_dir}")
    
    def check_model_exists(self, model_name: str) -> bool:
        """
        检查指定模型是否存在于本地
        
        Args:
            model_name: 模型名称（在 REQUIRED_MODELS 中定义）
            
        Returns:
            bool: 模型是否存在
        """
        if model_name not in self.REQUIRED_MODELS:
            logging.error(f"未知模型: {model_name}")
            return False
            
        model_config = self.REQUIRED_MODELS[model_name]
        local_path = self.project_root / model_config["local_path"]
        
        # 检查模型目录是否存在且包含必要文件
        if not local_path.exists():
            return False
            
        # 根据不同模型定义不同的关键文件
        if model_name == "speech_campplus_sv_zh-cn_16k-common":
            key_files = ["config.yaml", "campplus_cn_common.bin"]
        else:
            key_files = ["config.yaml", "model.pt"]
            
        for key_file in key_files:
            if not (local_path / key_file).exists():
                # 如果关键文件不存在，但目录存在，可能是部分下载
                logging.warning(f"模型 {model_name} 目录存在但缺少关键文件: {key_file}")
                return False
                
        return True
    
    def get_missing_models(self) -> List[str]:
        """
        获取缺失的模型列表
        
        Returns:
            List[str]: 缺失的模型名称列表
        """
        missing_models = []
        
        for model_name in self.REQUIRED_MODELS:
            if not self.check_model_exists(model_name):
                missing_models.append(model_name)
                
        return missing_models
    
    def install_modelscope_if_needed(self) -> bool:
        """
        检查并安装 modelscope 库（如果需要）
        
        Returns:
            bool: 安装是否成功
        """
        try:
            import modelscope
            logging.info(f"modelscope 已安装，版本: {modelscope.__version__}")
            return True
        except ImportError:
            logging.info("modelscope 未安装，正在安装...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", 
                    "modelscope[audio]", "--upgrade"
                ])
                logging.info("modelscope 安装成功")
                return True
            except subprocess.CalledProcessError as e:
                logging.error(f"modelscope 安装失败: {e}")
                return False
    
    def download_model(self, model_name: str, force_download: bool = False) -> bool:
        """
        下载指定模型
        
        Args:
            model_name: 模型名称
            force_download: 是否强制重新下载
            
        Returns:
            bool: 下载是否成功
        """
        if model_name not in self.REQUIRED_MODELS:
            logging.error(f"未知模型: {model_name}")
            return False
            
        model_config = self.REQUIRED_MODELS[model_name]
        local_path = self.project_root / model_config["local_path"]
        
        # 如果模型已存在且不强制下载，跳过
        if not force_download and self.check_model_exists(model_name):
            logging.info(f"模型 {model_name} 已存在，跳过下载")
            return True
            
        # 确保 modelscope 已安装
        if not self.install_modelscope_if_needed():
            return False
            
        logging.info(f"开始下载模型: {model_name}")
        logging.info(f"模型ID: {model_config['model_id']}")
        logging.info(f"版本: {model_config['revision']}")
        logging.info(f"预计大小: {model_config['size_gb']} GB")
        logging.info(f"本地路径: {local_path}")
        
        try:
            # 使用 modelscope 的 snapshot_download 下载模型
            from modelscope import snapshot_download

            # 下载模型
            cache_dir = snapshot_download(
                model_config["model_id"],
                revision=model_config["revision"],
                cache_dir=str(self.models_dir),
                local_files_only=False
            )
            
            logging.info(f"模型 {model_name} 下载成功")
            logging.info(f"缓存路径: {cache_dir}")
            
            # 验证下载是否成功
            if self.check_model_exists(model_name):
                logging.info(f"模型 {model_name} 验证成功")
                return True
            else:
                logging.error(f"模型 {model_name} 下载后验证失败")
                return False
                
        except Exception as e:
            logging.error(f"模型 {model_name} 下载失败: {str(e)}")
            return False
    
    def download_all_missing_models(self, max_retries: int = 3) -> Dict[str, bool]:
        """
        下载所有缺失的模型
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            Dict[str, bool]: 每个模型的下载结果
        """
        missing_models = self.get_missing_models()
        
        if not missing_models:
            logging.info("所有模型都已存在，无需下载")
            return {}
            
        logging.info(f"发现 {len(missing_models)} 个缺失模型: {missing_models}")
        
        # 计算总下载大小
        total_size = sum(self.REQUIRED_MODELS[model]["size_gb"] for model in missing_models)
        logging.info(f"预计总下载大小: {total_size:.1f} GB")
        
        results = {}
        
        for model_name in missing_models:
            logging.info(f"\n{'='*50}")
            logging.info(f"正在处理模型: {model_name}")
            logging.info(f"描述: {self.REQUIRED_MODELS[model_name]['description']}")
            
            success = False
            for attempt in range(max_retries):
                if attempt > 0:
                    logging.info(f"重试下载 {model_name} (第 {attempt + 1} 次)")
                    time.sleep(5)  # 等待 5 秒后重试
                    
                success = self.download_model(model_name)
                if success:
                    break
                    
            results[model_name] = success
            
            if success:
                logging.info(f"✅ 模型 {model_name} 下载成功")
            else:
                logging.error(f"❌ 模型 {model_name} 下载失败（已重试 {max_retries} 次）")
        
        # 输出总结
        logging.info(f"\n{'='*50}")
        logging.info("下载总结:")
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logging.info(f"成功: {successful}/{total}")
        
        for model_name, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            logging.info(f"  {model_name}: {status}")
            
        return results
    
    def get_model_status(self) -> Dict[str, Dict]:
        """
        获取所有模型的状态信息
        
        Returns:
            Dict[str, Dict]: 每个模型的状态信息
        """
        status = {}
        
        for model_name, model_config in self.REQUIRED_MODELS.items():
            local_path = self.project_root / model_config["local_path"]
            exists = self.check_model_exists(model_name)
            
            status[model_name] = {
                "exists": exists,
                "description": model_config["description"],
                "model_id": model_config["model_id"],
                "revision": model_config["revision"],
                "local_path": str(local_path),
                "size_gb": model_config["size_gb"]
            }
            
        return status
    
    def print_model_status(self):
        """打印所有模型的状态"""
        status = self.get_model_status()
        
        logging.info("\n" + "="*60)
        logging.info("ModelScope 模型状态")
        logging.info("="*60)
        
        for model_name, info in status.items():
            status_icon = "✅" if info["exists"] else "❌"
            logging.info(f"{status_icon} {model_name}")
            logging.info(f"   描述: {info['description']}")
            logging.info(f"   模型ID: {info['model_id']}")
            logging.info(f"   大小: {info['size_gb']} GB")
            logging.info(f"   本地路径: {info['local_path']}")
            logging.info("")


def main():
    """主函数 - 用于测试和手动下载模型"""
    manager = ModelScopeManager()
    
    # 打印当前状态
    manager.print_model_status()
    
    # 下载缺失的模型
    results = manager.download_all_missing_models()
    
    if results:
        # 再次打印状态
        logging.info("\n下载完成后的状态:")
        manager.print_model_status()


if __name__ == "__main__":
    main()