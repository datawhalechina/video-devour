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

from llm_handler import LLMHandler

def match_chunk_to_headings_llm(chunk, headings, chunk_index=None, all_chunks=None, context_window=3):
    """
    使用 LLM 将单个对话块匹配到最合适的标题。

    Args:
        chunk (dict): 代表单个文本块的字典。
        headings (list): 候选标题字符串列表。
        chunk_index (int, optional): 当前块在 all_chunks 中的索引。
        all_chunks (list, optional): 用于上下文参考的所有对话块的完整列表。
        context_window (int): 上下文包含的前后块数（默认为3）。

    Returns:
        str: 列表中最匹配的标题。
    """
    logging.info(f"正在为文本块匹配最合适的标题: '{chunk['text'][:30]}...'")
    
    # 格式化对话块
    start_time_str = f"{int(chunk['start'] // 60):02d}:{int(chunk['start'] % 60):02d}"
    end_time_str = f"{int(chunk['end'] // 60):02d}:{int(chunk['end'] % 60):02d}"
    chunk_text = f"[{start_time_str} - {end_time_str}] {chunk['speaker']}: {chunk['text']}"

    # 格式化标题
    headings_text = "\\n".join(f"- {h}" for h in headings)

    # 如果可用，构建上下文参考
    context_text = ""
    if all_chunks and chunk_index is not None:
        context_chunks = []
        
        # 获取上文
        start_idx = max(0, chunk_index - context_window)
        for i in range(start_idx, chunk_index):
            c = all_chunks[i]
            s_time = f"{int(c['start'] // 60):02d}:{int(c['start'] % 60):02d}"
            e_time = f"{int(c['end'] // 60):02d}:{int(c['end'] % 60):02d}"
            context_chunks.append(f"[{s_time} - {e_time}] {c['speaker']}: {c['text']}")
        
        # 标记当前块
        context_chunks.append(f">>> {chunk_text} <<<  [当前待匹配文本块]")
        
        # 获取下文
        end_idx = min(len(all_chunks), chunk_index + context_window + 1)
        for i in range(chunk_index + 1, end_idx):
            c = all_chunks[i]
            s_time = f"{int(c['start'] // 60):02d}:{int(c['start'] % 60):02d}"
            e_time = f"{int(c['end'] // 60):02d}:{int(c['end'] % 60):02d}"
            context_chunks.append(f"[{s_time} - {e_time}] {c['speaker']}: {c['text']}")
        
        context_text = "\\n".join(context_chunks)
        logging.info(f"为匹配任务添加了上下文参考（前 {chunk_index - start_idx} 个块，后 {end_idx - chunk_index - 1} 个块）")
    
    # 根据是否有上下文创建提示
    if context_text:
        prompt = (
            "你是一个智能文本分析助手。你的任务是将一个给定的文本块，与一个列表中最合适的标题进行匹配。\\n\\n"
            "**原文参考（带上下文）:**\\n"
            "以下是包含当前待匹配文本块及其前后上下文的原始对话记录，用于帮助你更好地理解文本的语境和主题。\\n"
            "当前待匹配的文本块已用 >>> ... <<< 标记。\\n\\n"
            f"```\\n{context_text}\\n```\\n\\n"
            f"**可用标题列表:**\\n{headings_text}\\n\\n"
            "**任务要求:**\\n"
            "1. 请仔细阅读标记的文本块，并结合其上下文，理解其核心内容和所属主题。\\n"
            "2. 从上方的标题列表中，选择一个最能总结或归类该文本块的标题。\\n"
            "3. **重要提示**: 你的回答必须 **只包含** 所选标题的完整文本，不要添加任何额外的词语、编号、解释或格式。例如，如果选择了第一个标题，你的输出就应该是该标题的文本本身。\\n"
        )
    else:
        # 无上下文的回退提示
        prompt = (
            "你是一个智能文本分析助手。你的任务是将一个给定的文本块，与一个列表中最合适的标题进行匹配。\\n\\n"
            f"**待匹配文本块:**\\n```\\n{chunk_text}\\n```\\n\\n"
            f"**可用标题列表:**\\n{headings_text}\\n\\n"
            "**任务要求:**\\n"
            "1. 请仔细阅读文本块，理解其核心内容。\\n"
            "2. 从上方的标题列表中，选择一个最能总结或归类该文本块的标题。\\n"
            "3. **重要提示**: 你的回答必须 **只包含** 所选标题的完整文本，不要添加任何额外的词语、编号、解释或格式。例如，如果选择了第一个标题，你的输出就应该是该标题的文本本身。\\n"
        )

    try:
        llm_handler = LLMHandler()
        system_message = "你是一个智能文本分析助手，精准地将文本匹配到最合适的标题。"
        matched_heading = llm_handler.get_response(prompt, system_message).strip()
        
        # 清理响应，确保它只是标题
        # 模型有时可能仍会添加额外的字符，如连字符或引号
        cleaned_heading = matched_heading.lstrip('- ').strip().strip('"`')

        # 确保返回的标题是候选标题之一
        if cleaned_heading in headings:
            logging.info(f"匹配成功: '{cleaned_heading}'")
            return cleaned_heading
        else:
            logging.warning(f"LLM返回了不在候选列表中的标题: '{cleaned_heading}'。将尝试在返回结果中查找最相似的候选标题。")
            # 回退：在响应中查找最相似的标题
            for h in headings:
                if h in cleaned_heading:
                    logging.info(f"回退匹配成功: '{h}'")
                    return h
            logging.error("回退匹配失败，将返回 None。")
            return None # 如果匹配失败，默认为 None
    except Exception as e:
        logging.error(f"调用 LLM 进行匹配时发生错误: {e}", exc_info=True)
        # 出现错误时，返回 None 作为回退
        return None

