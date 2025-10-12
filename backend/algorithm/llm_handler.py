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
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type=config.LLM_MODEL_TYPE,
            api_key=config.LLM_API_KEY,
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

    def get_response(self, prompt: str, system_message: str = "你是一个能力强大的人工智能助手。") -> str:
        """
        向LLM发送一个通用的prompt并获取响应。

        Args:
            prompt (str): 发送给LLM的完整prompt。
            system_message (str): 代理的系统消息。

        Returns:
            str: LLM返回的文本内容。
        """
        logging.info("正在向 LLM 发送通用请求...")
        try:
            agent = ChatAgent(system_message, model=self.model, token_limit=999999999)
            response = agent.step(prompt)
            content = response.msg.content
            logging.info("已成功从 LLM 获取响应。")
            return content
        except Exception as e:
            logging.error(f"调用 LLM 时发生错误: {e}", exc_info=True)
            return f"错误: 调用 LLM 失败: {e}"
