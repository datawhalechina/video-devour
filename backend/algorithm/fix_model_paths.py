#!/usr/bin/env python3
"""
修复 ModelScope 模型路径问题
将 models/models/iic/iic/模型名 移动到 models/models/iic/模型名
"""

import os
import shutil
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_model_paths():
    """修复模型路径"""
    project_root = Path(__file__).parent.parent.parent
    models_dir = project_root / "models" / "models" / "iic"
    
    # 检查是否存在错误的路径结构
    wrong_path = models_dir / "iic"
    if not wrong_path.exists():
        logging.info("未发现路径问题，无需修复")
        return
    
    logging.info("发现路径问题，开始修复...")
    
    # 获取所有需要移动的模型目录
    model_dirs = [d for d in wrong_path.iterdir() if d.is_dir()]
    
    for model_dir in model_dirs:
        target_path = models_dir / model_dir.name
        
        logging.info(f"移动模型: {model_dir.name}")
        logging.info(f"从: {model_dir}")
        logging.info(f"到: {target_path}")
        
        try:
            # 如果目标路径已存在，先删除
            if target_path.exists():
                shutil.rmtree(target_path)
            
            # 移动模型目录
            shutil.move(str(model_dir), str(target_path))
            logging.info(f"✅ 模型 {model_dir.name} 移动成功")
            
        except Exception as e:
            logging.error(f"❌ 移动模型 {model_dir.name} 失败: {e}")
    
    # 删除空的 iic 目录
    try:
        if wrong_path.exists() and not any(wrong_path.iterdir()):
            wrong_path.rmdir()
            logging.info("删除空的 iic 目录")
    except Exception as e:
        logging.warning(f"删除空目录失败: {e}")
    
    logging.info("路径修复完成！")

if __name__ == "__main__":
    fix_model_paths()