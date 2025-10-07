# -*- coding: utf-8 -*-
"""
测试 ASRProcessor 对新格式（Paraformer V2）的处理能力
"""
import json
import logging
from pathlib import Path
from data_processor import ASRProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_paraformer_v2():
    """
    测试 Paraformer V2 格式的处理
    """
    logging.info("="*60)
    logging.info("开始测试 Paraformer V2 格式处理")
    logging.info("="*60)
    
    # 获取项目根目录
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # 加载 Paraformer V2 的 ASR 结果
    asr_file = project_root / "output" / "asr_results_paraformer_v2.json"
    
    if not asr_file.exists():
        logging.error(f"测试文件不存在: {asr_file}")
        return
    
    try:
        # 初始化处理器
        processor = ASRProcessor(str(asr_file))
        
        # 处理数据
        chunked_dialogue = processor.process()
        
        # 输出结果统计
        logging.info("\n" + "="*60)
        logging.info("处理结果统计")
        logging.info("="*60)
        logging.info(f"总分块数: {len(chunked_dialogue)}")
        
        # 统计说话人
        speakers = set(item['speaker'] for item in chunked_dialogue)
        logging.info(f"说话人数: {len(speakers)}")
        logging.info(f"说话人列表: {', '.join(sorted(speakers))}")
        
        # 统计每个说话人的分块数
        speaker_counts = {}
        for item in chunked_dialogue:
            speaker = item['speaker']
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        
        logging.info("\n各说话人分块统计:")
        for speaker, count in sorted(speaker_counts.items()):
            logging.info(f"  {speaker}: {count} 个分块")
        
        # 计算总时长
        if chunked_dialogue:
            total_duration = chunked_dialogue[-1]['end'] - chunked_dialogue[0]['start']
            logging.info(f"\n总时长: {total_duration:.2f} 秒 ({total_duration/60:.2f} 分钟)")
        
        # 显示前几个分块示例
        logging.info("\n" + "="*60)
        logging.info("前 5 个分块示例")
        logging.info("="*60)
        for i, chunk in enumerate(chunked_dialogue[:5], 1):
            logging.info(f"\n分块 {i}:")
            logging.info(f"  说话人: {chunk['speaker']}")
            logging.info(f"  时间: {chunk['start']:.2f}s - {chunk['end']:.2f}s")
            logging.info(f"  时长: {chunk['end'] - chunk['start']:.2f}s")
            logging.info(f"  文本长度: {len(chunk['text'])} 字符")
            logging.info(f"  文本: {chunk['text'][:100]}{'...' if len(chunk['text']) > 100 else ''}")
        
        # 保存处理结果
        output_file = project_root / "output" / "processed_dialogue_v2.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunked_dialogue, f, ensure_ascii=False, indent=2)
        
        logging.info("\n" + "="*60)
        logging.info(f"✅ 处理结果已保存到: {output_file}")
        logging.info("="*60)
        
    except Exception as e:
        logging.error(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def compare_chunk_quality(chunked_dialogue):
    """
    分析分块质量
    
    Args:
        chunked_dialogue (list[dict]): 分块对话列表
    """
    logging.info("\n" + "="*60)
    logging.info("分块质量分析")
    logging.info("="*60)
    
    chunk_lengths = [len(chunk['text']) for chunk in chunked_dialogue]
    chunk_durations = [chunk['end'] - chunk['start'] for chunk in chunked_dialogue]
    
    logging.info(f"文本长度统计:")
    logging.info(f"  平均: {sum(chunk_lengths) / len(chunk_lengths):.1f} 字符")
    logging.info(f"  最小: {min(chunk_lengths)} 字符")
    logging.info(f"  最大: {max(chunk_lengths)} 字符")
    
    logging.info(f"\n分块时长统计:")
    logging.info(f"  平均: {sum(chunk_durations) / len(chunk_durations):.2f} 秒")
    logging.info(f"  最小: {min(chunk_durations):.2f} 秒")
    logging.info(f"  最大: {max(chunk_durations):.2f} 秒")
    
    # 分析连续性（检查时间间隔）
    gaps = []
    for i in range(1, len(chunked_dialogue)):
        gap = chunked_dialogue[i]['start'] - chunked_dialogue[i-1]['end']
        gaps.append(gap)
    
    if gaps:
        logging.info(f"\n分块间隔统计:")
        logging.info(f"  平均间隔: {sum(gaps) / len(gaps):.2f} 秒")
        logging.info(f"  最小间隔: {min(gaps):.2f} 秒")
        logging.info(f"  最大间隔: {max(gaps):.2f} 秒")
        
        # 找出异常大的间隔
        large_gaps = [(i+1, gap) for i, gap in enumerate(gaps) if gap > 5.0]
        if large_gaps:
            logging.info(f"\n发现 {len(large_gaps)} 个大间隔 (>5秒):")
            for idx, gap in large_gaps[:5]:  # 只显示前5个
                logging.info(f"  分块 {idx} 后: {gap:.2f} 秒")


if __name__ == "__main__":
    logging.info("🧪 ASRProcessor 测试开始\n")
    
    success = test_paraformer_v2()
    
    if success:
        # 读取处理结果进行质量分析
        project_root = Path(__file__).resolve().parent.parent.parent
        output_file = project_root / "output" / "processed_dialogue_v2.json"
        
        with open(output_file, 'r', encoding='utf-8') as f:
            chunked_dialogue = json.load(f)
        
        compare_chunk_quality(chunked_dialogue)
        
        logging.info("\n🎉 所有测试完成！")
    else:
        logging.error("\n❌ 测试失败")

