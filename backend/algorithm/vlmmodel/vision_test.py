from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.messages import BaseMessage

from PIL import Image
from pathlib import Path




model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,

    # model_type="qwen3-vl-30b-a3b-instruct",
    # api_key="sk-905584c90bf444eebfb08534964d6c21",
    # url="https://dashscope.aliyuncs.com/compatible-mode/v1",

    model_type="doubao-seed-1-6-flash-250828",
    api_key="eb4ff0cf-fa34-4686-a64b-8a6628943cd9",
    url="https://ark.cn-beijing.volces.com/api/v3",
)

agent = ChatAgent(
    model=model,
    output_language='中文'
)

# 图片本地路径
image_path = Path(__file__).parent / "testp1.png"
img = Image.open(image_path)
topic = '04_语音合成与数字人输出'
user_msg = BaseMessage.make_user_message(
    role_name="User", 
    content=f"你是一个图片理解专家，你需要根据我的要求回答图片相关的问题。\
        1.你需要描述图片的内容，具体有什么。描述完整清晰有条理。\
        2.你需要判断图片的内容是否符合【{topic}】的主题。满分10分。最低分0分。你需要认真判断主题和画面内容的关系并给出合理的评分。\
        3.你需要结构化的回复，并且使用json结构。    \
        回复样例：{str({'图片内容':'描述图片中的内容即可','相关性打分':10})}", 
    image_list=[img]  # 将图片放入列表中
)

response = agent.step(user_msg)
print(response.msgs[0].content)
