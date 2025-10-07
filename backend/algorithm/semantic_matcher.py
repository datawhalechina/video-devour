# -*- coding: utf-8 -*-
"""
基于向量相似度的语义匹配器

使用 sentence-transformers 计算文本块与大纲内容的语义相似度
"""
import logging
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers 库未安装，将使用简单的字符串匹配作为后备方案")


class SemanticMatcher:
    """
    语义匹配器，使用向量相似度进行文本块与大纲的匹配
    """
    
    def __init__(self, similarity_threshold=0.90, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        """
        初始化语义匹配器
        
        Args:
            similarity_threshold (float): 相似度阈值，默认0.90（90%）
            model_name (str): sentence-transformers 模型名称
        """
        self.similarity_threshold = similarity_threshold
        self.model = None
        self.headings_embeddings = {}
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logging.info(f"正在加载语义模型: {model_name}")
                self.model = SentenceTransformer(model_name)
                logging.info("语义模型加载成功")
            except Exception as e:
                logging.error(f"加载语义模型失败: {e}")
                self.model = None
        else:
            logging.warning("sentence-transformers 不可用，请安装: pip install sentence-transformers")
    
    def initialize_headings(self, headings_with_content):
        """
        初始化大纲标题，计算每个标题内容的向量表示
        
        Args:
            headings_with_content (dict): 标题到内容的映射 {标题: 内容文本}
        """
        if not self.model:
            logging.warning("语义模型未加载，跳过向量计算")
            return
        
        logging.info(f"正在为 {len(headings_with_content)} 个标题计算向量表示...")
        
        for heading, content in headings_with_content.items():
            if content:
                try:
                    # 计算内容的向量表示
                    embedding = self.model.encode(content, convert_to_numpy=True)
                    self.headings_embeddings[heading] = embedding
                    logging.debug(f"标题 '{heading}' 的向量表示已计算")
                except Exception as e:
                    logging.error(f"计算标题 '{heading}' 的向量时出错: {e}")
        
        logging.info(f"成功计算 {len(self.headings_embeddings)} 个标题的向量表示")
    
    def cosine_similarity(self, vec1, vec2):
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1 (np.array): 向量1
            vec2 (np.array): 向量2
            
        Returns:
            float: 余弦相似度 [0, 1]
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def match_chunk(self, chunk_text, candidate_headings):
        """
        将文本块匹配到最合适的标题
        
        Args:
            chunk_text (str): 文本块内容
            candidate_headings (list): 候选标题列表
            
        Returns:
            tuple: (匹配的标题, 相似度分数) 或 (None, 0.0) 如果没有找到合适的匹配
        """
        if not self.model or not self.headings_embeddings:
            logging.warning("语义模型未初始化，无法进行匹配")
            return None, 0.0
        
        if not chunk_text or not candidate_headings:
            return None, 0.0
        
        try:
            # 计算文本块的向量表示
            chunk_embedding = self.model.encode(chunk_text, convert_to_numpy=True)
            
            # 计算与每个候选标题的相似度
            best_heading = None
            best_similarity = 0.0
            
            for heading in candidate_headings:
                if heading in self.headings_embeddings:
                    heading_embedding = self.headings_embeddings[heading]
                    similarity = self.cosine_similarity(chunk_embedding, heading_embedding)
                    
                    logging.debug(f"标题 '{heading}' 的相似度: {similarity:.4f}")
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_heading = heading
            
            # 检查是否达到阈值
            if best_similarity >= self.similarity_threshold:
                logging.info(f"找到高相似度匹配: '{best_heading}' (相似度: {best_similarity:.4f})")
                return best_heading, best_similarity
            else:
                logging.info(f"最高相似度 {best_similarity:.4f} 未达到阈值 {self.similarity_threshold}")
                return None, best_similarity
                
        except Exception as e:
            logging.error(f"匹配过程中出错: {e}", exc_info=True)
            return None, 0.0
    
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
                logging.warning(f"相似度不足，使用回退标题: '{fallback_heading}'")
                return fallback_heading, similarity, True
            else:
                return None, similarity, False
    
    def simple_string_match(self, chunk_text, candidate_headings):
        """
        简单的字符串匹配（后备方案，当 sentence-transformers 不可用时）
        
        Args:
            chunk_text (str): 文本块内容
            candidate_headings (list): 候选标题列表
            
        Returns:
            tuple: (匹配的标题, 0.0) 或 (None, 0.0)
        """
        logging.warning("使用简单字符串匹配作为后备方案")
        
        # 简单的关键词匹配
        for heading in candidate_headings:
            # 如果标题中的关键词出现在文本块中
            if heading in chunk_text or any(word in chunk_text for word in heading.split()):
                logging.info(f"简单匹配成功: '{heading}'")
                return heading, 0.0
        
        return None, 0.0

