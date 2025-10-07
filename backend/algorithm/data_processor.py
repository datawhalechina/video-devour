# -*- coding: utf-8 -*-
"""
处理 ASR（自动语音识别）数据

本模块负责加载 ASR JSON 输出，并根据预定义规则对对话进行分块处理。
支持新的 Paraformer V2 格式（说话人信息已在句子级别）
"""
import json
import logging

class ASRProcessor:
    """
    处理 ASR 结果以创建结构化、分块的对话
    
    支持两种格式：
    1. 旧格式：需要基于时间戳匹配 segments 和 speakers
    2. 新格式（Paraformer V2）：说话人信息已在 transcript 的每个句子中
    """
    
    def __init__(self, asr_result_path):
        """
        初始化处理器，从 JSON 文件加载 ASR 结果
        
        Args:
            asr_result_path (str): ASR 结果 JSON 文件路径
        """
        logging.info(f"正在从 {asr_result_path} 加载 ASR 数据...")
        try:
            with open(asr_result_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            # 处理数组格式（通常是 [{ ... }]）
            if isinstance(self.data, list) and self.data:
                data_dict = self.data[0]
            else:
                data_dict = self.data
            
            # 尝试加载新格式（Paraformer V2）
            self.transcript = data_dict.get('transcript')
            
            if self.transcript:
                # 新格式：transcript 中已包含说话人信息
                logging.info(f"检测到新格式（Paraformer V2），共 {len(self.transcript)} 个句子")
                self.format_version = 'v2'
                self.segments = None
                self.speakers = None
            else:
                # 旧格式：需要分别处理 segments 和 speakers
                self.segments = data_dict.get('segments')
                self.speakers = data_dict.get('speakers')
                
                if self.segments is None or self.speakers is None:
                    raise ValueError("JSON 文件中缺少必要字段。新格式需要 'transcript'，旧格式需要 'segments' 和 'speakers'。")
                
                logging.info(f"检测到旧格式，共 {len(self.segments)} 个文本片段和 {len(self.speakers)} 个说话人片段")
                self.format_version = 'v1'
                self.transcript = None
                
        except FileNotFoundError:
            logging.error(f"错误：输入文件未找到 {asr_result_path}")
            raise
        except json.JSONDecodeError:
            logging.error(f"错误：解析 JSON 文件时出错 {asr_result_path}")
            raise
        except Exception as e:
            logging.error(f"加载数据时发生未知错误: {e}")
            raise
    
    def _generate_dialogue_from_transcript_v2(self):
        """
        从新格式的 transcript 中生成对话列表
        
        新格式中每个句子已包含：
        - index: 序号
        - spk_id: 说话人 ID
        - sentence: 文本内容
        - start_time: 开始时间（秒）
        - end_time: 结束时间（秒）
        
        Returns:
            list[dict]: 标准化的对话列表
        """
        logging.info("正在从新格式 transcript 生成对话列表...")
        dialogue = []
        
        if not self.transcript:
            logging.warning("transcript 数据为空")
            return []
        
        for item in self.transcript:
            # 提取字段
            speaker = item.get('spk_id', 'UNKNOWN')
            text = item.get('sentence', '').strip()
            start_time = item.get('start_time', 0.0)
            end_time = item.get('end_time', 0.0)
            
            # 跳过空文本
            if not text:
                continue
            
            dialogue.append({
                'speaker': f"SPEAKER_{speaker}",  # 格式化说话人 ID
                'start': float(start_time),
                'end': float(end_time),
                'text': text
            })
        
        logging.info(f"成功生成 {len(dialogue)} 个对话条目")
        return dialogue
    
    def _generate_speaker_dialogue_from_words(self):
        """
        根据词级别的时间戳来切分对话，精确地将每个词分配给对应的说话人
        
        此方法用于旧格式（v1）
        
        Returns:
            list[dict]: 对话列表
        """
        logging.info("正在基于词级别时间戳进行更精细的说话人对话切分...")
        dialogue = []
        
        if not self.segments or not self.speakers:
            logging.warning("缺少 segments 或 speakers 数据，无法进行词级别切分")
            return []

        for segment in self.segments:
            # 如果没有词级别信息，使用整个 segment 进行匹配
            if 'words' not in segment or not segment['words']:
                max_overlap = 0
                best_speaker = "UNKNOWN_SPEAKER"
                for turn in self.speakers:
                    overlap_start = max(segment['start'], turn['start'])
                    overlap_end = min(segment['end'], turn['end'])
                    overlap = overlap_end - overlap_start
                    if overlap > max_overlap:
                        max_overlap = overlap
                        best_speaker = turn['speaker']
                dialogue.append({
                    'speaker': best_speaker,
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip()
                })
                continue

            # 处理词级别信息
            current_speaker = None
            current_words = []
            current_start_time = -1

            for word_info in segment['words']:
                word_start_time = word_info['start']
                word_end_time = word_info['end']
                word_speaker = None

                # 使用词的中点时间查找说话人
                word_midpoint_time = word_start_time + (word_end_time - word_start_time) / 2
                for turn in self.speakers:
                    if turn['start'] <= word_midpoint_time < turn['end']:
                        word_speaker = turn['speaker']
                        break

                # 如果没有找到匹配的说话人，使用最近的说话人
                if word_speaker is None:
                    min_distance = float('inf')
                    closest_speaker = self.speakers[0]['speaker'] if self.speakers else "UNKNOWN_SPEAKER"
                    for turn in self.speakers:
                        if word_start_time >= turn['end']:
                            distance = word_start_time - turn['end']
                        elif word_end_time <= turn['start']:
                            distance = turn['start'] - word_end_time
                        else:
                            distance = 0
                        if distance < min_distance:
                            min_distance = distance
                            closest_speaker = turn['speaker']
                            if distance == 0:
                                break
                    word_speaker = closest_speaker
                
                # 处理说话人切换
                if current_speaker is None:
                    current_speaker = word_speaker
                    current_words.append(word_info['word'])
                    current_start_time = word_info['start']
                elif word_speaker == current_speaker:
                    current_words.append(word_info['word'])
                else:
                    # 说话人切换，保存当前块
                    if current_words:
                        previous_word_end_time = segment['words'][segment['words'].index(word_info) - 1]['end']
                        dialogue.append({
                            'speaker': current_speaker,
                            'start': current_start_time,
                            'end': previous_word_end_time,
                            'text': "".join(current_words)
                        })
                    current_speaker = word_speaker
                    current_words = [word_info['word']]
                    current_start_time = word_info['start']
            
            # 保存最后一个块
            if current_words:
                dialogue.append({
                    'speaker': current_speaker,
                    'start': current_start_time,
                    'end': segment['words'][-1]['end'],
                    'text': "".join(current_words)
                })

        logging.info(f"词级别对话切分完成，共生成 {len(dialogue)} 个对话条目")
        return dialogue

    def _chunk_dialogue(self, speaker_dialogue):
        """
        将对话条目列表分块
        
        分块规则：
        1. 说话人改变时分块
        2. 时间间隔超过 3 秒时分块
        3. 当前块文本长度达到 200 字符时分块
        
        Args:
            speaker_dialogue (list[dict]): 对话列表
            
        Returns:
            list[dict]: 分块后的对话列表
        """
        logging.info("正在将对话分块...")
        if not speaker_dialogue:
            return []

        chunks = []
        current_chunk = []

        for item in speaker_dialogue:
            # 第一个条目
            if not current_chunk:
                current_chunk.append(item)
                continue

            last_item = current_chunk[-1]

            # 检查分块条件
            speaker_changed = item['speaker'] != last_item['speaker']
            time_gap_exceeded = (item['start'] - last_item['end']) > 3.0

            if speaker_changed or time_gap_exceeded:
                # 保存当前块
                text = "".join(d['text'] for d in current_chunk)
                chunks.append({
                    'speaker': current_chunk[0]['speaker'],
                    'start': current_chunk[0]['start'],
                    'end': current_chunk[-1]['end'],
                    'text': text
                })
                current_chunk = [item]
                continue

            # 添加到当前块
            current_chunk.append(item)
            current_len = sum(len(d['text']) for d in current_chunk)

            # 检查长度限制
            if current_len >= 200:
                text = "".join(d['text'] for d in current_chunk)
                chunks.append({
                    'speaker': current_chunk[0]['speaker'],
                    'start': current_chunk[0]['start'],
                    'end': current_chunk[-1]['end'],
                    'text': text
                })
                current_chunk = []

        # 保存最后一个块
        if current_chunk:
            text = "".join(d['text'] for d in current_chunk)
            chunks.append({
                'speaker': current_chunk[0]['speaker'],
                'start': current_chunk[0]['start'],
                'end': current_chunk[-1]['end'],
                'text': text
            })
        
        logging.info(f"分块完成，共生成 {len(chunks)} 个块")
        return chunks

    def process(self):
        """
        执行完整的 ASR 数据处理流程
        
        根据数据格式版本选择不同的处理方法：
        - v2: 使用新格式处理（Paraformer V2）
        - v1: 使用旧格式处理（基于词级别时间戳）
        
        Returns:
            list[dict]: 处理后的分块对话列表
        """
        logging.info(f"开始处理 ASR 数据（格式版本: {self.format_version}）...")
        
        if self.format_version == 'v2':
            # 新格式：直接从 transcript 生成对话
            speaker_dialogue = self._generate_dialogue_from_transcript_v2()
        else:
            # 旧格式：基于词级别时间戳匹配
            speaker_dialogue = self._generate_speaker_dialogue_from_words()
        
        # 对对话进行分块
        chunked_dialogue = self._chunk_dialogue(speaker_dialogue)
        
        logging.info(f"ASR 数据处理完成，共 {len(chunked_dialogue)} 个分块")
        return chunked_dialogue
