"""LLM客户端实现"""

from typing import List, Dict, Optional, Tuple, Literal
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from .utils.logger import StoryLogger
from .utils.usage_stats import get_stats
from .utils.error_handler import ContentParsingError

# 定义角色和操作类型
RoleType = Literal["FrameworkPlanner", "OutlinePlanner", "Writer", "Critic", "unknown"]
OperationType = Literal["生成故事框架", "生成章节大纲", "生成章节内容", "评估故事质量", "未知操作"]

class LLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self):
        self.logger = StoryLogger()
        self.default_model = "default-model"
    
    def _determine_role_and_operation(self, messages: List[Dict[str, str]], role: str) -> Tuple[RoleType, OperationType]:
        """
        根据消息内容确定当前角色和操作类型
        
        Args:
            messages: 消息列表，第一个是 system 消息，包含角色定义
            role: 默认角色名称
            
        Returns:
            Tuple[RoleType, OperationType]: (角色名称, 操作类型)
        """
        if not isinstance(messages, list) or not messages:
            raise ValueError("消息列表不能为空")
            
        # 获取 system 消息（第一条消息）
        system_message = messages[0]
        if system_message.get("role") != "system" or "content" not in system_message:
            return role, "未知操作"
            
        system_prompt = system_message["content"].lower()
        
        # 定义角色和操作的映射关系
        role_operation_map = [
            {
                "keywords": ["故事框架设计专家", "framework planner"],
                "role": "FrameworkPlanner",
                "operation": "生成故事框架"
            },
            {
                "keywords": ["大纲设计专家", "outline planner"],
                "role": "OutlinePlanner",
                "operation": "生成章节大纲"
            },
            {
                "keywords": ["故事创作专家", "story writer", "创作者"],
                "role": "Writer",
                "operation": "生成章节内容"
            },
            {
                "keywords": ["故事评论专家", "story critic", "评论者"],
                "role": "Critic",
                "operation": "评估故事质量"
            }
        ]
        
        # 遍历映射关系，找到匹配的角色和操作
        for mapping in role_operation_map:
            if any(keyword in system_prompt for keyword in mapping["keywords"]):
                return mapping["role"], mapping["operation"]
        
        # 如果没有匹配，返回传入的角色名称
        return role, "未知操作"

    @abstractmethod
    async def generate_response(self, 
                         messages: List[Dict[str, str]], 
                         temperature: float = 0.7,
                         max_tokens: int = 4000,
                         role: str = "unknown") -> str:
        """
        生成响应的抽象方法
        
        Args:
            messages: 消息列表，格式为[{"role": "system"/"user"/"assistant", "content": "消息内容"}]
            temperature: 温度参数，控制响应的随机性，范围[0, 1]
            max_tokens: 最大生成token数，范围[1, 8192]
            role: 调用者的角色名称，用于统计
            
        Returns:
            str: 生成的响应文本
            
        Raises:
            ValueError: 参数验证失败时抛出
            ContentParsingError: 消息格式不正确时抛出
        """
        pass

class DeepSeekClient(LLMClient):
    """DeepSeek API客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or self._get_api_key_from_env()
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        self.default_model = "deepseek-chat"
        self.stats = get_stats()

    def _get_api_key_from_env(self) -> str:
        """从环境变量获取 API Key"""
        import os
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY 环境变量")
        return api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, 
                         messages: List[Dict[str, str]], 
                         temperature: float = 0.7,
                         max_tokens: int = 4000,
                         role: str = "unknown") -> str:
        """
        调用DeepSeek API生成响应
        
        Args:
            messages: 消息列表
            temperature: 温度参数，范围[0, 1]
            max_tokens: 最大生成token数，范围[1, 8192]
            role: 调用者的角色名称
            
        Returns:
            str: 生成的响应文本
            
        Raises:
            ValueError: 参数验证失败时抛出
            ContentParsingError: 消息格式不正确时抛出
        """
        # 参数验证
        if not isinstance(messages, list):
            raise ValueError("messages 必须是列表")
        if not messages:
            raise ValueError("消息列表不能为空")
        if not isinstance(temperature, (int, float)):
            raise ValueError("temperature 必须是数字")
        if not 0 <= temperature <= 1:
            raise ValueError("temperature 必须在 0 到 1 之间")
        if not isinstance(max_tokens, int):
            raise ValueError("max_tokens 必须是整数")
        if not 1 <= max_tokens <= 8192:
            raise ValueError("max_tokens 必须在 1 到 8192 之间")
        if not isinstance(role, str):
            raise ValueError("role 必须是字符串")

        try:
            # 确定当前角色和操作类型
            current_role, operation = self._determine_role_and_operation(messages, role)
        except ValueError as e:
            self.logger.error(f"解析消息失败: {str(e)}", role=role)
            raise
        
        try:
            # 记录请求开始
            self.logger.info(
                f"开始{operation}\n"
                f"模型: {self.default_model}\n"
                f"温度: {temperature}\n"
                f"最大token数: {max_tokens}", 
                role=current_role
            )
            
            # 调用API
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 获取响应文本
            response_text = response.choices[0].message.content
            
            # 记录请求成功
            self.logger.info(
                f"{operation}成功\n"
                f"响应长度: {len(response_text)}", 
                role=current_role
            )
            
            # 更新统计信息
            self.stats.record_request(
                model=self.default_model,
                role=current_role,
                operation=operation,
                tokens_in=response.usage.prompt_tokens,
                tokens_out=response.usage.completion_tokens
            )
            
            return response_text
            
        except Exception as e:
            # 记录错误并重新抛出
            self.logger.error(
                f"{operation}失败: {str(e)}\n"
                f"错误类型: {type(e).__name__}", 
                role=current_role
            )
            raise
