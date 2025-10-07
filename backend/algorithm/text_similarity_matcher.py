# -*- coding: utf-8 -*-
"""
基于文本相似度/重复率的匹配器

检查文本块的内容是否与大纲中的文本内容重复或相似
如果重复率达到90%以上，说明该块属于对应的大纲标题
"""
import logging
from difflib import SequenceMatcher

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers 库未安装，将使用基于字符串的相似度计算")


class TextSimilarityMatcher:
    """
    文本相似度匹配器
    
    核心思路：检查块的文本是否与大纲内容重复
    如果块的文本在大纲内容中出现（重复率 >= 90%），则匹配成功
    """
    
    def __init__(self, similarity_threshold=0.90, use_semantic=True):
        """
        初始化匹配器
        
        Args:
            similarity_threshold (float): 相似度阈值，默认0.90（90%）
            use_semantic (bool): 是否使用语义相似度（需要sentence-transformers）
        """
        self.similarity_threshold = similarity_threshold
        self.use_semantic = use_semantic and SENTENCE_TRANSFORMERS_AVAILABLE
        self.model = None
        self.headings_content = {}
        self.headings_embeddings = {}
        
        if self.use_semantic:
            try:
                logging.info("正在加载轻量级语义模型...")
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                logging.info("语义模型加载成功")
            except Exception as e:
                logging.error(f"加载语义模型失败: {e}")
                self.model = None
                self.use_semantic = False
        
        if not self.use_semantic:
            logging.info("将使用基于字符串的相似度计算（更快，准确度略低）")
    
    def initialize_headings(self, headings_with_content):
        """
        初始化大纲标题及其内容
        
        Args:
            headings_with_content (dict): 标题到内容的映射 {标题: 内容文本}
        """
        self.headings_content = headings_with_content
        logging.info(f"已加载 {len(headings_with_content)} 个标题的内容")
        
        # 如果使用语义相似度，预先计算大纲内容的向量
        if self.use_semantic and self.model:
            logging.info("正在预计算大纲内容的向量表示...")
            for heading, content in headings_with_content.items():
                if content:
                    try:
                        # 将大纲内容分句编码
                        sentences = self._split_into_sentences(content)
                        embeddings = self.model.encode(sentences, convert_to_numpy=True)
                        self.headings_embeddings[heading] = {
                            'sentences': sentences,
                            'embeddings': embeddings
                        }
                    except Exception as e:
                        logging.error(f"计算标题 '{heading}' 的向量时出错: {e}")
            
            logging.info(f"成功预计算 {len(self.headings_embeddings)} 个标题的向量")
    
    def _split_into_sentences(self, text):
        """
        将文本分割成句子
        
        Args:
            text (str): 输入文本
            
        Returns:
            list: 句子列表
        """
        # 简单的句子分割（按标点符号）
        import re
        sentences = re.split(r'[。！？\n]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def string_similarity(self, str1, str2):
        """
        计算两个字符串的相似度（基于序列匹配）
        
        Args:
            str1 (str): 字符串1
            str2 (str): 字符串2
            
        Returns:
            float: 相似度 [0, 1]
        """
        return SequenceMatcher(None, str1, str2).ratio()
    
    def calculate_overlap_ratio(self, chunk_text, outline_content):
        """
        计算文本块与大纲内容的重叠率
        
        核心逻辑：检查块的文本有多少比例出现在大纲内容中
        
        Args:
            chunk_text (str): 文本块内容
            outline_content (str): 大纲内容
            
        Returns:
            float: 重叠率 [0, 1]
        """
        if not chunk_text or not outline_content:
            return 0.0
        
        # 方法1：直接字符串相似度
        direct_similarity = self.string_similarity(chunk_text, outline_content)
        
        # 方法2：检查块的文本是否包含在大纲中
        chunk_lower = chunk_text.lower().strip()
        outline_lower = outline_content.lower().strip()
        
        # 如果块的文本直接出现在大纲中
        if chunk_lower in outline_lower:
            return 1.0
        
        # 方法3：分词后计算重叠度
        chunk_words = set(chunk_lower.replace('，', ' ').replace('。', ' ').split())
        outline_words = set(outline_lower.replace('，', ' ').replace('。', ' ').split())
        
        if not chunk_words:
            return 0.0
        
        common_words = chunk_words & outline_words
        word_overlap_ratio = len(common_words) / len(chunk_words)
        
        # 综合考虑：取最大值
        overlap_ratio = max(direct_similarity, word_overlap_ratio)
        
        return overlap_ratio
    
    def semantic_similarity_score(self, chunk_text, heading):
        """
        计算语义相似度分数（使用向量）
        
        Args:
            chunk_text (str): 文本块内容
            heading (str): 标题
            
        Returns:
            float: 最高相似度分数
        """
        if not self.model or heading not in self.headings_embeddings:
            return 0.0
        
        try:
            # 编码块的文本
            chunk_embedding = self.model.encode(chunk_text, convert_to_numpy=True)
            
            # 与该标题下所有句子的向量计算相似度
            heading_data = self.headings_embeddings[heading]
            embeddings = heading_data['embeddings']
            
            # 计算余弦相似度
            similarities = []
            for outline_embedding in embeddings:
                dot_product = np.dot(chunk_embedding, outline_embedding)
                norm1 = np.linalg.norm(chunk_embedding)
                norm2 = np.linalg.norm(outline_embedding)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    similarities.append(similarity)
            
            # 返回最高相似度
            return max(similarities) if similarities else 0.0
            
        except Exception as e:
            logging.error(f"计算语义相似度时出错: {e}")
            return 0.0
    
    def match_chunk(self, chunk_text, candidate_headings):
        """
        将文本块匹配到最合适的标题
        
        Args:
            chunk_text (str): 文本块内容
            candidate_headings (list): 候选标题列表
            
        Returns:
            tuple: (匹配的标题, 相似度分数) 或 (None, 0.0)
        """
        if not chunk_text or not candidate_headings:
            return None, 0.0
        
        best_heading = None
        best_score = 0.0
        
        for heading in candidate_headings:
            if heading not in self.headings_content:
                continue
            
            outline_content = self.headings_content[heading]
            
            if not outline_content:
                continue
            
            # 方法1：基于字符串的重叠率（快速）
            overlap_ratio = self.calculate_overlap_ratio(chunk_text, outline_content)
            
            # 方法2：语义相似度（如果可用）
            semantic_score = 0.0
            if self.use_semantic:
                semantic_score = self.semantic_similarity_score(chunk_text, heading)
            
            # 综合评分：取两者的最大值
            final_score = max(overlap_ratio, semantic_score)
            
            logging.debug(f"标题 '{heading}': 重叠率={overlap_ratio:.2%}, 语义={semantic_score:.2%}, 最终={final_score:.2%}")
            
            if final_score > best_score:
                best_score = final_score
                best_heading = heading
        
        # 检查是否达到阈值
        if best_score >= self.similarity_threshold:
            logging.info(f"找到高相似度匹配: '{best_heading}' (相似度: {best_score:.2%})")
            return best_heading, best_score
        else:
            logging.info(f"最高相似度 {best_score:.2%} 未达到阈值 {self.similarity_threshold:.0%}")
            return None, best_score
    
    def match_chunk_with_fallback(self, chunk_text, candidate_headings, fallback_heading=None):
        """
        将文本块匹配到标题，如果相似度不够则返回回退标题
        
        Args:
            chunk_text (str): 文本块内容
            candidate_headings (list): 候选标题列表
            fallback_heading (str, optional): 回退标题
            
        Returns:
            tuple: (匹配的标题, 相似度分数, 是否使用了回退)
        """
        matched_heading, similarity = self.match_chunk(chunk_text, candidate_headings)
        
        if matched_heading:
            return matched_heading, similarity, False
        else:
            # 使用回退标题
            if fallback_heading:
                logging.warning(f"相似度不足 ({similarity:.2%} < {self.similarity_threshold:.0%})，使用回退标题: '{fallback_heading}'")
                return fallback_heading, similarity, True
            else:
                return None, similarity, False



