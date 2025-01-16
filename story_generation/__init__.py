"""
AI Story Generation Framework

一个基于大语言模型的故事生成框架，使用多角色协作方式创作故事。

主要组件：
- StoryGenerator: 故事生成器，协调多个角色完成故事创作
- Roles: 不同的角色（规划者、作家、评论家）
- LLMClient: 大语言模型客户端
- Utils: 工具类（日志、使用统计等）
"""

from .story_generator import StoryGenerator
from .llm_utils import LLMClient, DeepSeekClient
from .utils.logger import StoryLogger
from .config.story_requirements import StoryRequirements
from .roles.base_role import BaseRole
from .roles.writer_role import WriterRole
from .roles.critic_role import CriticRole
from .roles.planner_role import PlannerRole

__version__ = "0.1.0"
__author__ = "Codeium"
__email__ = "support@codeium.com"

__all__ = [
    'StoryGenerator',
    'LLMClient',
    'DeepSeekClient',
    'StoryLogger',
    'StoryRequirements',
    'BaseRole',
    'WriterRole',
    'CriticRole',
    'PlannerRole',
]
