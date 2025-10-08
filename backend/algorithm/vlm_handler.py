
import logging
import json
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.messages import BaseMessage
from PIL import Image
import config  # Assuming config file stores API keys and URLs

class VLMHandler:
    """
    一个用于与视觉语言模型（VLM）交互的处理器。

    该类封装了模型的初始化、构建prompt以及调用VLM对图片进行打分的功能。
    """

    def __init__(self):
        """
        初始化VLM处理器，设置并创建模型实例。
        """
        try:
            self.model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
                model_type=config.VLM_MODEL_TYPE,
                api_key=config.VLM_API_KEY,
                url=config.VLM_API_URL,
            )
            self.agent = ChatAgent(model=self.model, output_language='中文')
            logging.info("VLM 处理器初始化成功。")
        except Exception as e:
            logging.error(f"VLM 处理器初始化失败: {e}", exc_info=True)
            raise

    def score_frame(self, image_path: str, topic: str) -> tuple[int, str]:
        """
        使用 VLM评估图片与给定主题的相关性。

        Args:
            image_path (str): 需要评估的图片文件路径。
            topic (str): 用于评估相关性的主题文本。

        Returns:
            tuple[int, str]: 返回一个元组，包含 (相关性得分, 图片描述)。
                             如果处理失败，则返回 (-1, "处理失败")。
        """
        try:
            logging.info(f"正在使用 VLM 评估图片 '{image_path}'，主题为 '{topic}'...")
            img = Image.open(image_path)
            
            prompt = (
                f"你是一个图片理解专家，你需要根据我的要求回答图片相关的问题。\n"
                f"1. 你需要描述图片的内容，具体有什么。描述要完整清晰有条理。\n"
                f"2. 你需要判断图片的内容是否符合【{topic}】的主题。满分10分，最低分0分。你需要认真判断主题和画面内容的关系并给出合理的评分。\n"
                f"3. 你需要结构化的回复，并且使用json结构。\n"
                f"回复样例：{json.dumps({'图片内容':'描述图片中的内容即可','相关性打分':10}, ensure_ascii=False)}"
            )

            user_msg = BaseMessage.make_user_message(
                role_name="User",
                content=prompt,
                image_list=[img]
            )

            response = self.agent.step(user_msg)
            content = response.msgs[0].content
            
            # 清理和解析JSON响应
            # VLM 可能返回包裹在 ```json ... ``` 或其他文本中的JSON
            json_match = content[content.find('{'):content.rfind('}')+1]
            if not json_match:
                logging.error(f"VLM 响应中未找到有效的JSON内容: {content}")
                return -1, "无法解析VLM响应"

            data = json.loads(json_match)
            score = data.get('相关性打分', -1)
            description = data.get('图片内容', '无描述')
            
            logging.info(f"图片 '{image_path}' 评估完成。得分: {score}, 描述: {description[:50]}...")
            return int(score), description

        except FileNotFoundError:
            logging.error(f"图片文件未找到: {image_path}")
            return -1, "图片文件未找到"
        except json.JSONDecodeError:
            logging.error(f"解析VLM的JSON响应失败: {content}")
            return -1, "解析VLM响应失败"
        except Exception as e:
            logging.error(f"VLM 评估图片时发生未知错误: {e}", exc_info=True)
            return -1, "VLM处理未知错误"
