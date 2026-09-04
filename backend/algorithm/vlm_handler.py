
import logging
import json
import asyncio
import aiohttp
import base64
from typing import List, Tuple, Union
from PIL import Image
import io
import config


class VLMHandler:
    """
    VLM 处理器
    
    """

    def __init__(self, max_concurrent: int = 10, temperature: float = 0.6):
        """
        初始化VLM处理器
        
        Args:
            max_concurrent: 最大并发数
            temperature: 温度
        """
        try:
            self.max_concurrent = max_concurrent
            self.temperature = temperature
            
            # 从 config 读取配置
            self.api_url = config.VLM_API_URL
            self.api_key = config.VLM_API_KEY
            self.model_type = config.VLM_MODEL_TYPE
            
            self.session = None
            
            # 事件循环和信号量
            self._loop = None
            self._semaphore = None
            
            # 任务计数器
            self._task_counter = 0
            
            logging.info(f"VLM 处理器初始化成功，最大并发数: {max_concurrent}")
            logging.info(f"API URL: {self.api_url}")
            logging.info(f"Model: {self.model_type}")
        except Exception as e:
            logging.error(f"VLM 处理器初始化失败: {e}", exc_info=True)
            raise

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        获取或创建 HTTP 会话
        
        Returns:
            aiohttp.ClientSession: HTTP 会话
        """
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent * 2,  
                limit_per_host=self.max_concurrent * 2,
                ttl_dns_cache=300
            )
            timeout = aiohttp.ClientTimeout(total=60) 
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self.session

    def close_sync(self):
        """
        同步关闭会话
        """
        if self.session and not self.session.closed:
            try:
                # 直接关闭连接器，不依赖事件循环
                if hasattr(self.session, '_connector') and self.session._connector:
                    self.session._connector.close()
                logging.info("HTTP 会话已同步关闭")
            except Exception as e:
                logging.warning(f"同步关闭会话时出错: {e}")

    def _image_to_base64(self, image_path: str) -> str:
        """
        将图片转换为 base64 编码

        Args:
            image_path: 图片路径
            
        Returns:
            str: base64 编码的图片数据 URL
        """
        with Image.open(image_path) as img:
            # 转换为 RGB（如果是 RGBA）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 压缩图片（如果太大）
            max_size = (1024, 1024)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换为 base64
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_bytes = buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            return f"data:image/jpeg;base64,{img_base64}"

    async def _call_api(
        self,
        image_path: str,
        prompt: str,
        task_id: int = 0
    ) -> dict:
        """
        调用 VLM API

        Args:
            image_path: 图片路径
            prompt: 提示词
            task_id: 任务ID
            
        Returns:
            dict: API 响应的 JSON 数据
        """
        session = await self._get_session()
        
        # 将图片转换为 base64
        image_data_url = self._image_to_base64(image_path)
        
        # 构建请求体
        payload = {
            "model": self.model_type,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": self.temperature
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 发送请求
        logging.debug(f"[任务{task_id}] 发送 API 请求...")
        async with session.post(self.api_url, json=payload, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            logging.debug(f"[任务{task_id}] API 响应成功")
            return result

    def _get_semaphore(self):
        """
        获取或创建信号量
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def _score_frame_async(
        self,
        image_path: str,
        topic: str,
        task_id: int = 0,
        max_retries: int = 3
    ) -> Tuple[int, str]:
        """
        异步评估单张图片

        Args:
            image_path: 图片路径
            topic: 评估主题
            task_id: 任务ID
            max_retries: 最大重试次数

        Returns:
            tuple[int, str]: 返回一个元组，包含 (相关性得分, 图片描述)。
                             如果处理失败，则返回 (-1, "处理失败")。
        """
        semaphore = self._get_semaphore()
        async with semaphore:
            for attempt in range(1, max_retries + 1):
                try:
                    logging.info(
                        f"[任务{task_id}] 开始评估图片 '{image_path}' "
                        f"(尝试 {attempt}/{max_retries})"
                    )
                    
                    # 构建提示词
                    prompt = (
                        f"你是一个图片理解专家，你需要根据我的要求回答图片相关的问题。\n"
                        f"1. 你需要描述图片的内容，具体有什么。描述要完整清晰有条理。\n"
                        f"2. 你需要判断图片的内容是否符合【{topic}】的主题。"
                        f"满分10分，最低分0分。你需要认真判断主题和画面内容的关系并给出合理的评分。\n"
                        f"3. 你需要结构化的回复，并且使用json结构。\n"
                        f'回复样例：{{"图片内容": "描述图片中的内容即可", "相关性打分": 10}}'
                    )
                    
                    # 调用 API
                    response = await self._call_api(image_path, prompt, task_id)
                    
                    # 解析响应
                    if 'choices' in response and len(response['choices']) > 0:
                        content = response['choices'][0]['message']['content']
                        
                        # 提取 JSON
                        if '```json' in content:
                            json_str = content.split('```json')[1].split('```')[0].strip()
                        elif '```' in content:
                            json_str = content.split('```')[1].split('```')[0].strip()
                        else:
                            json_str = content.strip()
                        
                        result = json.loads(json_str)
                        score = int(result.get('相关性打分', 0))
                        description = result.get('图片内容', '')
                        
                        logging.info(
                            f"[任务{task_id}] 图片 '{image_path}' 评估完成。"
                            f"得分: {score}"
                        )
                        
                        return (score, description)
                    else:
                        raise ValueError("API 返回空响应")
                
                except Exception as e:
                    logging.warning(
                        f"[任务{task_id}] 评估图片 '{image_path}' 失败 "
                        f"(尝试 {attempt}/{max_retries}): {e}"
                    )
                    if attempt == max_retries:
                        logging.error(
                            f"[任务{task_id}] 图片 '{image_path}' "
                            f"评估失败，已达最大重试次数"
                        )
                        return (-1, "处理失败")
                    
                    # 重试前等待
                    await asyncio.sleep(1)
            
            return (-1, "处理失败")
    
    async def _score_frames_batch_async(
        self,
        image_paths: List[str],
        topics: Union[str, List[str]]
    ) -> List[Tuple[int, str]]:
        """
        批量异步评估图片
        
        Args:
            image_paths: 图片路径列表
            topics: 主题
            
        Returns:
            List[Tuple[int, str]]: 评估结果列表，每个元素为 (相关性得分, 图片描述)
        """
        # 如果 topics 是单个字符串，扩展为列表
        if isinstance(topics, str):
            topics_list = [topics] * len(image_paths)
        else:
            topics_list = topics
            
        if len(image_paths) != len(topics_list):
            raise ValueError("图片数量和主题数量不匹配")
        
        logging.info(f"开始批量异步评估 {len(image_paths)} 张图片...")
        
        # 创建所有任务
        tasks = [
            self._score_frame_async(img, topic, task_id=i+1)
            for i, (img, topic) in enumerate(zip(image_paths, topics_list))
        ]
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks)
        
        # 统计成功率
        successful = sum(1 for score, _ in results if score > 0)
        logging.info(f"批量评估完成，成功: {successful}/{len(results)}")
        
        return results
    
    def score_frames_batch(
        self,
        image_paths: List[str],
        topic: str
    ) -> List[Tuple[int, str]]:
        """
        批量评估图片
        
        Args:
            image_paths: 图片路径列表
            topic: 评估主题（所有图片使用相同主题）
            
        Returns:
            List[Tuple[int, str]]: 评估结果列表，每个元素为 (相关性得分, 图片描述)
        """
        # 获取或创建事件循环
        loop = self._get_or_create_loop()
        
        # 在事件循环中运行批量异步评估
        results = loop.run_until_complete(
            self._score_frames_batch_async(image_paths, topic)
        )
        
        return results
    
    def _get_or_create_loop(self):
        """
        获取或创建事件循环
        """
        if self._loop is None or self._loop.is_closed():
            try:
                # 尝试获取当前事件循环
                self._loop = asyncio.get_event_loop()
                if self._loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                # 如果没有事件循环或已关闭，创建新的
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def score_frame(self, image_path: str, topic: str) -> Tuple[int, str]:
        """
        同步接口
        
        Args:
            image_path: 图片路径
            topic: 评估主题
            
        Returns:
            tuple[int, str]: 返回一个元组，包含 (相关性得分, 图片描述)。
                             如果处理失败，则返回 (-1, "处理失败")。
        """
        # 获取持久化的事件循环
        loop = self._get_or_create_loop()
        
        # 增加任务计数器
        self._task_counter += 1
        task_id = self._task_counter
        
        result = loop.run_until_complete(
            self._score_frame_async(image_path, topic, task_id=task_id)
        )
        return result
    
    async def close(self):
        """
        关闭 HTTP 会话
        """
        if self.session and not self.session.closed:
            await self.session.close()
            logging.info("HTTP 会话已关闭")
    
    def __del__(self):
        """
        析构函数，确保资源释放
        """
        try:
            self.close_sync()
            
            # 关闭事件循环
            if self._loop and not self._loop.is_closed():
                self._loop.close()
        except Exception:
            pass
