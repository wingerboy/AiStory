"""故事需求解析"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class StoryRequirements:
    """故事需求"""
    requirements_text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将需求文本转换为结构化数据
        这里我们不再硬编码结构，而是让模型理解文本需求
        """
        return {
            "requirements": self.requirements_text
        }
    
    @classmethod
    def create(cls, requirements: str) -> 'StoryRequirements':
        """创建故事需求"""
        return cls(requirements_text=requirements)
