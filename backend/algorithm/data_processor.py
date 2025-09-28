# -*- coding: utf-8 -*-
"""
Handles the processing of ASR (Automatic Speech Recognition) data.

This module is responsible for loading the initial ASR JSON output,
accurately assigning speakers to each word based on timestamps, and
chunking the resulting dialogue according to predefined rules.
"""
import json
import logging

class ASRProcessor:
    """
    Processes ASR results to create structured, chunked dialogue.
    """
    def __init__(self, asr_result_path):
        """
        Initializes the processor by loading the ASR results from a JSON file.

        Args:
            asr_result_path (str): The path to the ASR result JSON file.
        """
        logging.info(f"正在从 {asr_result_path} 加载ASR数据...")
        try:
            with open(asr_result_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            if isinstance(self.data, list) and self.data:
                data_dict = self.data[0]
            else:
                data_dict = self.data

            self.segments = data_dict.get('transcript')
            self.speakers = data_dict.get('speakers')
            if self.segments is None or self.speakers is None:
                self.segments = self.data.get('segments') if isinstance(self.data, dict) else None
                self.speakers = self.data.get('speakers') if isinstance(self.data, dict) else None
                if self.segments is None or self.speakers is None:
                    raise ValueError("JSON文件中缺少 'transcript'/'segments' 或 'speakers' 键。")
            logging.info(f"成功加载 {len(self.segments)} 个文本片段和 {len(self.speakers)} 个说话人片段。")
        except FileNotFoundError:
            logging.error(f"错误：输入文件未找到于 {asr_result_path}")
            raise
        except json.JSONDecodeError:
            logging.error(f"错误：解析JSON文件时出错 {asr_result_path}")
            raise
        except Exception as e:
            logging.error(f"加载数据时发生未知错误: {e}")
            raise

    def _generate_speaker_dialogue_from_words(self):
        """
        根据词级别的时间戳来切分对话，精确地将每个词分配给对应的说话人。
        """
        logging.info("正在基于词级别时间戳进行更精细的说话人对话切分...")
        dialogue = []
        
        if not self.segments or not self.speakers:
            logging.warning("缺少 segments 或 speakers 数据，无法进行词级别切分。")
            return []

        for segment in self.segments:
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

            current_speaker = None
            current_words = []
            current_start_time = -1

            for word_info in segment['words']:
                word_start_time = word_info['start']
                word_end_time = word_info['end']
                word_speaker = None

                word_midpoint_time = word_start_time + (word_end_time - word_start_time) / 2
                for turn in self.speakers:
                    if turn['start'] <= word_midpoint_time < turn['end']:
                        word_speaker = turn['speaker']
                        break

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
                
                if current_speaker is None:
                    current_speaker = word_speaker
                    current_words.append(word_info['word'])
                    current_start_time = word_info['start']
                elif word_speaker == current_speaker:
                    current_words.append(word_info['word'])
                else:
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
            
            if current_words:
                dialogue.append({
                    'speaker': current_speaker,
                    'start': current_start_time,
                    'end': segment['words'][-1]['end'],
                    'text': "".join(current_words)
                })

        logging.info(f"词级别对话切分完成，共生成 {len(dialogue)} 个对话条目。")
        return dialogue

    def _chunk_dialogue(self, speaker_dialogue):
        """
        将对话条目列表分块。
        """
        logging.info("正在将对话分块...")
        if not speaker_dialogue:
            return []

        chunks = []
        current_chunk = []

        for item in speaker_dialogue:
            if not current_chunk:
                current_chunk.append(item)
                continue

            last_item = current_chunk[-1]

            speaker_changed = item['speaker'] != last_item['speaker']
            time_gap_exceeded = (item['start'] - last_item['end']) > 3.0

            if speaker_changed or time_gap_exceeded:
                text = "".join(d['text'] for d in current_chunk)
                chunks.append({
                    'speaker': current_chunk[0]['speaker'],
                    'start': current_chunk[0]['start'],
                    'end': current_chunk[-1]['end'],
                    'text': text
                })
                current_chunk = [item]
                continue

            current_chunk.append(item)
            current_len = sum(len(d['text']) for d in current_chunk)

            if current_len >= 200:
                text = "".join(d['text'] for d in current_chunk)
                chunks.append({
                    'speaker': current_chunk[0]['speaker'],
                    'start': current_chunk[0]['start'],
                    'end': current_chunk[-1]['end'],
                    'text': text
                })
                current_chunk = []

        if current_chunk:
            text = "".join(d['text'] for d in current_chunk)
            chunks.append({
                'speaker': current_chunk[0]['speaker'],
                'start': current_chunk[0]['start'],
                'end': current_chunk[-1]['end'],
                'text': text
            })
        
        logging.info(f"分块完成，共生成 {len(chunks)} 个块。")
        return chunks

    def process(self):
        """
        执行完整的ASR数据处理流程。
        """
        speaker_dialogue = self._generate_speaker_dialogue_from_words()
        chunked_dialogue = self._chunk_dialogue(speaker_dialogue)
        return chunked_dialogue
