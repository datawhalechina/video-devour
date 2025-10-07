# -*- coding: utf-8 -*-
"""
Handles all interactions with the Large Language Model (LLM).

This module is responsible for generating the final prompt from processed
dialogue chunks and interfacing with the LLM via the camel-ai library to
produce a Markdown outline.
"""
import logging
import os
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
import config

class LLMHandler:
    """
    Manages prompt generation and LLM API calls.
    """
    def __init__(self):
        """
        Initializes the LLM handler by setting up the model configuration.
        """
        self.api_key = config.get_api_key()
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type=config.LLM_MODEL_TYPE,
            api_key=self.api_key,
            url=config.LLM_API_URL,
            model_config_dict={"temperature": config.LLM_TEMPERATURE},
            # token_counter=config.LLM_TOKEN_COUNTER
            # token_limit = 999999999
        )

    def _generate_llm_prompt(self, chunked_dialogue):
        """
        Generates a complete prompt for the LLM to create an outline.
        """
        logging.info("正在生成LLM大纲任务的prompt...")
        prompt_header = (
            "请根据以下会议记录文本，生成一份详细的Markdown格式的文档大纲。\n\n"
            "重要提示：\n"
            "- 以下文本是自动语音识别（ASR）的结果，可能包含口语化表达、重复、错误或不通顺的句子。请在理解和总结时，智能地识别并忽略这些潜在的瑕疵。\n"
            "- 你的任务是梳理文本的逻辑结构，提炼核心议题和关键点，而不是简单地复述原文。\n"
            "- 大纲应采用Markdown的层级标题格式，且要求只到二级大纲（一级大纲的起始使用 #,二级使用 ##）。\n\n"
            "- 每个二级大纲下给出匹配的asr内容"
            "- 切记不要增加文本以外的内容大纲，不要自主补全后续大纲。\n"
            "- 输出样例如下：\n"
            """# 系统架构组成\n
            ## 用户对话输入接口\n
            我们使用对话输入接口……\n
            ## 微调模块与Prompt优化模块\n
            微调部分我们采用了…\n
            ## 知识融合与风格化处理\n
            我们将原文小说融合进知识与风格化……\n"""
            "会议记录文本如下：\n"
            "-------------------\n\n"
        )
        formatted_dialogue = []
        for chunk in chunked_dialogue:
            start_time_str = f"{int(chunk['start'] // 60):02d}:{int(chunk['start'] % 60):02d}"
            end_time_str = f"{int(chunk['end'] // 60):02d}:{int(chunk['end'] % 60):02d}"
            dialogue_line = f"[{start_time_str} - {end_time_str}] {chunk['speaker']}: {chunk['text']}"
            formatted_dialogue.append(dialogue_line)
        full_dialogue_text = "\n".join(formatted_dialogue)
        final_prompt = prompt_header + full_dialogue_text
        logging.info("LLM prompt生成完毕。")
        return final_prompt

    def get_outline(self, chunked_dialogue):
        """
        Takes chunked dialogue and returns a Markdown outline from the LLM.
        """
        logging.info("正在调用 LLM 生成大纲...")
        prompt = self._generate_llm_prompt(chunked_dialogue)
        try:
            assistant_sys_msg = "你是一个专业的会议记录分析师。你的任务是根据提供的带有说话人和时间戳的会议文本，生成一份结构清晰、逻辑严谨的Markdown格式文档大纲。"
            agent = ChatAgent(assistant_sys_msg, model=self.model,token_limit = 999999999)
            assistant_response = agent.step(prompt)
            outline = assistant_response.msg.content
            logging.info("LLM 大纲生成成功。")
            return outline
        except ImportError:
            logging.error("无法导入 camel 库。请确保 'camel-ai' 已安装 (pip install camel-ai)。")
            return "错误：camel-ai 库未安装。"
        except Exception as e:
            logging.error(f"调用 LLM 时发生错误: {e}", exc_info=True)
            return f"错误：调用 LLM 失败: {e}"

    def match_chunk_to_headings(self, chunk, headings, chunk_index=None, all_chunks=None, context_window=3):
        """
        Matches a single dialogue chunk to the best heading from a list.

        Args:
            chunk (dict): A dictionary representing a single text chunk.
            headings (list): A list of strings, each being a candidate heading.
            chunk_index (int, optional): The index of the current chunk in all_chunks.
            all_chunks (list, optional): Complete list of all dialogue chunks for context reference.
            context_window (int): Number of chunks before and after to include as context (default: 3).

        Returns:
            str: The best matching heading from the list.
        """
        logging.info(f"正在为文本块匹配最合适的标题: '{chunk['text'][:30]}...'")
        
        # Format the dialogue chunk
        start_time_str = f"{int(chunk['start'] // 60):02d}:{int(chunk['start'] % 60):02d}"
        end_time_str = f"{int(chunk['end'] // 60):02d}:{int(chunk['end'] % 60):02d}"
        chunk_text = f"[{start_time_str} - {end_time_str}] {chunk['speaker']}: {chunk['text']}"

        # Format the headings
        headings_text = "\n".join(f"- {h}" for h in headings)

        # Build context reference if available
        context_text = ""
        if all_chunks and chunk_index is not None:
            context_chunks = []
            
            # Get previous context
            start_idx = max(0, chunk_index - context_window)
            for i in range(start_idx, chunk_index):
                c = all_chunks[i]
                s_time = f"{int(c['start'] // 60):02d}:{int(c['start'] % 60):02d}"
                e_time = f"{int(c['end'] // 60):02d}:{int(c['end'] % 60):02d}"
                context_chunks.append(f"[{s_time} - {e_time}] {c['speaker']}: {c['text']}")
            
            # Mark current chunk
            context_chunks.append(f">>> {chunk_text} <<<  [当前待匹配文本块]")
            
            # Get following context
            end_idx = min(len(all_chunks), chunk_index + context_window + 1)
            for i in range(chunk_index + 1, end_idx):
                c = all_chunks[i]
                s_time = f"{int(c['start'] // 60):02d}:{int(c['start'] % 60):02d}"
                e_time = f"{int(c['end'] // 60):02d}:{int(c['end'] % 60):02d}"
                context_chunks.append(f"[{s_time} - {e_time}] {c['speaker']}: {c['text']}")
            
            context_text = "\n".join(context_chunks)
            logging.info(f"为匹配任务添加了上下文参考（前 {chunk_index - start_idx} 个块，后 {end_idx - chunk_index - 1} 个块）")
        
        # Create the prompt with or without context
        if context_text:
            prompt = (
                "你是一个智能文本分析助手。你的任务是将一个给定的文本块，与一个列表中最合适的标题进行匹配。\n\n"
                "**原文参考（带上下文）:**\n"
                "以下是包含当前待匹配文本块及其前后上下文的原始对话记录，用于帮助你更好地理解文本的语境和主题。\n"
                "当前待匹配的文本块已用 >>> ... <<< 标记。\n\n"
                f"```\n{context_text}\n```\n\n"
                f"**可用标题列表:**\n{headings_text}\n\n"
                "**任务要求:**\n"
                "1. 请仔细阅读标记的文本块，并结合其上下文，理解其核心内容和所属主题。\n"
                "2. 从上方的标题列表中，选择一个最能总结或归类该文本块的标题。\n"
                "3. **重要提示**: 你的回答必须 **只包含** 所选标题的完整文本，不要添加任何额外的词语、编号、解释或格式。例如，如果选择了第一个标题，你的输出就应该是该标题的文本本身。\n"
            )
        else:
            # Fallback to simple prompt without context
            prompt = (
                "你是一个智能文本分析助手。你的任务是将一个给定的文本块，与一个列表中最合适的标题进行匹配。\n\n"
                f"**待匹配文本块:**\n```\n{chunk_text}\n```\n\n"
                f"**可用标题列表:**\n{headings_text}\n\n"
                "**任务要求:**\n"
                "1. 请仔细阅读文本块，理解其核心内容。\n"
                "2. 从上方的标题列表中，选择一个最能总结或归类该文本块的标题。\n"
                "3. **重要提示**: 你的回答必须 **只包含** 所选标题的完整文本，不要添加任何额外的词语、编号、解释或格式。例如，如果选择了第一个标题，你的输出就应该是该标题的文本本身。\n"
            )

        try:
            assistant_sys_msg = "你是一个智能文本分析助手，精准地将文本匹配到最合适的标题。"
            agent = ChatAgent(assistant_sys_msg, model=self.model)
            assistant_response = agent.step(prompt)
            logging.info(prompt,assistant_response)
            matched_heading = assistant_response.msg.content.strip()
            
            # Clean up the response to ensure it's just the heading
            # Sometimes the model might still add extra characters like hyphens or quotes
            cleaned_heading = matched_heading.lstrip('- ').strip().strip('"`')

            # Ensure the returned heading is one of the candidates
            if cleaned_heading in headings:
                logging.info(f"匹配成功: '{cleaned_heading}'")
                return cleaned_heading
            else:
                logging.warning(f"LLM返回了不在候选列表中的标题: '{cleaned_heading}'。将尝试在返回结果中查找最相似的候选标题。")
                # Fallback: find the most similar heading in the response
                for h in headings:
                    if h in cleaned_heading:
                        logging.info(f"回退匹配成功: '{h}'")
                        return h
                logging.error("回退匹配失败，将返回 None。")
                return None # Default to the first heading if matching fails

        except Exception as e:
            logging.error(f"调用 LLM 进行匹配时发生错误: {e}", exc_info=True)
            # In case of error, return None as a fallback
            return None
