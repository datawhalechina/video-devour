# -*- coding: utf-8 -*-
"""
Handles all interactions with the Large Language Model (LLM).

This module is responsible for generating the final prompt from processed
dialogue chunks and interfacing with the LLM via the camel-ai library to
produce a Markdown outline.

借鉴 light 版的核心改进：
- 学习阶段（小学/初中/高中）注入到所有 prompt
- 限流/超时自动重试（指数退避 + 随机抖动）
"""
import logging
import os
import random
import time
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
import config
from backend.algorithm import timing

# 限流重试参数（源自 light 版实践）
MAX_RETRIES = 5
BASE_RETRY_DELAY = 2

# 学习阶段 -> prompt 指令
EDUCATION_LEVEL_INSTRUCTIONS = {
    "自由学习": "面向普通学习者，不预设专业背景，语言平实自然，注重直观理解与实用性。",
    "小学": "使用简单易懂的语言，适合小学生理解。",
    "初中": "使用清晰明了的语言，适合初中生理解。",
    "高中": "可以使用较为专业的术语，适合高中生理解。",
    "大学": "使用严谨准确的语言，适合本科阶段学习，可包含学科基础理论与关键推导。",
    "硕士": "面向硕士研究生的深度，覆盖理论体系、方法比较与相关研究视野。",
    "博士": "面向博士研究生的深度，聚焦前沿问题、方法论创新与跨领域关联。",
    "深入研究": "面向深入钻研场景，追求系统性与深度：原理推导、方法对比、局限分析与进一步探索建议。",
    "垂直领域研究": "面向特定垂直领域的从业者与研究者，强调领域术语体系、行业实践与专业纵深。",
}


# 全局输出语言要求：无论原视频/文本是什么语言，LLM 产出一律用简体中文
CHINESE_OUTPUT_RULE = "【输出语言】必须全程使用简体中文输出（专有名词、技术术语可保留英文原文）。"


def get_level_instruction(education_level: str = None) -> str:
    """获取学习阶段对应的 prompt 指令片段"""
    if not education_level:
        return ""
    instruction = EDUCATION_LEVEL_INSTRUCTIONS.get(education_level)
    if not instruction:
        return ""
    return f"当前学习阶段为：{education_level}，{instruction}"


class LLMHandler:
    """
    Manages prompt generation and LLM API calls.
    """
    def __init__(self, education_level: str = None):
        """
        Initializes the LLM handler by setting up the model configuration.

        Args:
            education_level: 学习阶段（小学/初中/高中）；为空时取设置中的默认值
        """
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type=config.LLM_MODEL_TYPE,
            api_key=config.LLM_API_KEY,
            url=config.LLM_API_URL,
            model_config_dict={"temperature": config.LLM_TEMPERATURE},
        )
        if education_level is None:
            try:
                from backend.algorithm.settings_store import load_settings
                education_level = load_settings().get("default_education_level", "自由学习")
            except Exception:
                education_level = "自由学习"
        self.education_level = education_level

    def _call_with_retry(self, agent, prompt: str, task_desc: str = "LLM调用") -> str:
        """
        带指数退避的 LLM 调用，对限流（429/rate limit）和超时类错误自动重试。
        """
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = agent.step(prompt)
                return response.msg.content
            except Exception as e:
                last_error = e
                message = str(e).lower()
                retryable = any(kw in message for kw in ("rate", "429", "timeout", "timed out", "throttl", "overloaded", "500", "502", "503"))
                if not retryable or attempt == MAX_RETRIES - 1:
                    raise
                delay = BASE_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"{task_desc} 触发限流/超时，{delay:.1f} 秒后重试 "
                                f"(第 {attempt + 1}/{MAX_RETRIES - 1} 次): {e}")
                time.sleep(delay)
        raise last_error

    def _generate_llm_prompt(self, chunked_dialogue):
        """
        Generates a complete prompt for the LLM to create an outline.
        """
        logging.info("正在生成LLM大纲任务的prompt...")
        prompt_header = (
            f"{CHINESE_OUTPUT_RULE}\n\n"
            "请根据以下视频字幕转写文本，生成一份结构清晰的 Markdown 文档大纲。\n\n"
            "【输入说明】\n"
            "文本来自自动语音识别（ASR），可能含口语化表达、重复、错别字或不通顺句子；"
            "请理解意图后归纳，不要照抄原话，也不要凭空补充原文没有的内容。\n\n"
            "【结构要求】\n"
            "1. 只有一个一级标题（`#`），作为整份内容的主题名，不超过 20 字。\n"
            "2. 一级标题下用 3-8 个二级标题（`##`）划分内容板块，标题为**名词性短语**，"
            "长度 4-16 字，不使用问句、不使用「我们」「你们」等口语词。\n"
            "3. 每个二级标题下的正文：先写 2-4 句连贯的概述段落（说明该板块讲了什么），"
            "再按需补充 0-3 条要点（用 `-` 开头），要点要具体、含关键数据或结论。\n"
            "4. 不要出现三级及更深标题，不要出现「首先/然后/接下来」这类口头连接词。\n"
            "5. 只输出 Markdown 正文，不要输出任何解释性文字或代码块标记。\n\n"
            "【输出示例】\n"
            "# 系统架构与实现要点\n\n"
            "## 对话输入接口设计\n\n"
            "该模块负责接收用户输入并做初步意图识别，是整个流程的入口。"
            "接口采用异步方式处理，单次响应控制在 200ms 内。\n\n"
            "- 支持多轮上下文，保留最近 10 轮对话\n"
            "- 输入内容先做敏感词过滤再进入后续环节\n\n"
            "## 微调与提示词优化\n\n"
            "微调部分采用 LoRA 方案，在保持基座模型不变的前提下适配垂直场景。"
            "提示词优化则通过模板化与少样本示例提升稳定性。\n\n"
            "视频字幕转写文本如下：\n"
            "-------------------\n\n"
        )
        level_instruction = get_level_instruction(self.education_level)
        if level_instruction:
            prompt_header = (
                f"【学习阶段】{level_instruction}。请根据学习阶段调整大纲的语言深度与表达方式。\n\n"
                + prompt_header
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
            assistant_sys_msg = ("你是一位专业的内容架构师，擅长把口语化视频转写整理成结构清晰的 Markdown 大纲。"
                                "输出必须严格遵循用户给定的层级与格式规范：单一一级标题 + 3-8 个名词性二级标题，"
                                "每个板块先概述段落后要点列表，不出现三级标题与口语连接词。"
                                "无论原始文本是什么语言，一律使用简体中文输出。")
            if self.education_level:
                assistant_sys_msg += f"目标读者为{self.education_level}学生。"
            agent = ChatAgent(assistant_sys_msg, model=self.model, token_limit=999999999)
            outline = self._call_with_retry(agent, prompt, "生成大纲")
            logging.info("LLM 大纲生成成功。")
            return outline
        except ImportError:
            logging.error("无法导入 camel 库。请确保 'camel-ai' 已安装 (pip install camel-ai)。")
            return "错误：camel-ai 库未安装。"
        except Exception as e:
            logging.error(f"调用 LLM 时发生错误: {e}", exc_info=True)
            return f"错误：调用 LLM 失败: {e}"

    def get_response(self, prompt: str, system_message: str = "你是一个能力强大的人工智能助手。") -> str:
        with timing.track(f"LLM调用({getattr(self, 'model_type', 'llm')})", category="llm"):
            return self._get_response_impl(prompt, system_message)

    def _get_response_impl(self, prompt: str, system_message: str) -> str:
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
            system_message = f"{system_message} {CHINESE_OUTPUT_RULE}"
            agent = ChatAgent(system_message, model=self.model, token_limit=999999999)
            content = self._call_with_retry(agent, prompt, "通用请求")
            logging.info("已成功从 LLM 获取响应。")
            return content
        except Exception as e:
            logging.error(f"调用 LLM 时发生错误: {e}", exc_info=True)
            return f"错误: 调用 LLM 失败: {e}"
