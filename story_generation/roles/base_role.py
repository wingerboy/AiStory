from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypeVar, Type
from ..llm_utils import LLMClient
from ..utils.logger import StoryLogger
import json
import re

T = TypeVar('T', bound=Dict[str, Any])

class BaseRole(ABC):
    """角色基类，定义所有角色的通用接口和功能"""
    
    def __init__(self, name: str, system_prompt: str, llm_client: LLMClient):
        self.name = name
        self._system_prompt = system_prompt
        self.llm_client = llm_client
        self.logger = StoryLogger()
        self.logger.info(f"初始化角色: {name}", role=name)
        
    @property
    def system_prompt(self) -> str:
        """获取系统提示词"""
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, value: str):
        """设置系统提示词"""
        self._system_prompt = value
        self.logger.info(f"角色 {self.name} 切换系统提示词", role=self.name)
    
    def _preprocess_json_response(self, response: str) -> str:
        """
        预处理 JSON 响应，移除可能存在的 markdown 代码块标记
        
        Args:
            response: 原始响应文本
            
        Returns:
            str: 处理后的 JSON 文本
        """
        # 移除开头的 ```json 或 ``` 标记
        response = re.sub(r'^```json\s*\n', '', response.strip())
        response = re.sub(r'^```\s*\n', '', response.strip())
        # 移除结尾的 ``` 标记
        response = re.sub(r'\n\s*```\s*$', '', response.strip())
        return response
    
    def parse_json_response(self, response: str, default_value: Optional[T] = None) -> T:
        """
        解析 JSON 响应，包含预处理和错误处理
        
        Args:
            response: 原始响应文本
            default_value: 解析失败时的默认值
            
        Returns:
            Dict[str, Any]: 解析后的 JSON 对象
            
        Raises:
            ValueError: 当解析失败且没有提供默认值时抛出
        """
        try:
            # 预处理响应文本
            processed_response = self._preprocess_json_response(response)
            self.logger.debug(f"处理后的响应:\n{processed_response}", role=self.name)
            
            # 尝试解析 JSON
            return json.loads(processed_response)
        except json.JSONDecodeError as e:
            self.logger.warning(
                f"JSON 解析失败\n"
                f"错误信息: {str(e)}\n"
                f"原始响应: {response[:200]}...", 
                role=self.name
            )
            if default_value is not None:
                self.logger.info(f"使用默认值: {default_value}", role=self.name)
                return default_value
            raise ValueError(f"JSON 解析失败: {str(e)}")
        
    async def generate_response(self, prompt: str) -> str:
        """使用LLM生成响应"""
        self.logger.debug(f"生成响应开始\n提示词: {prompt[:200]}...", role=self.name)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.llm_client.generate_response(messages=messages, role=self.name)
            self.logger.debug(f"生成响应成功\n响应内容: {response[:200]}...", role=self.name)
            return response
        except Exception as e:
            self.logger.error(f"生成响应失败: {str(e)}", role=self.name)
            raise
    
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入并返回结果"""
        pass
