from typing import Dict, Any, List
from .base_role import BaseRole
from ..prompts.base_prompts import RolePrompts, WriterPrompts, BasePromptTemplate
from ..utils.logger import StoryLogger
from ..utils.error_handler import with_error_handling, ContentParsingError
from ..config.settings import Settings, RoleType
import json

class WriterRole(BaseRole):
    """创作者角色，负责故事内容创作"""
    
    def __init__(self, llm_client):
        """
        初始化创作者角色
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(
            name="Writer",
            system_prompt=RolePrompts.WRITER,
            llm_client=llm_client
        )
        self.logger = StoryLogger()
        self.settings = Settings()
        self.config = self.settings.get_role_config(RoleType.WRITER)
    
    @with_error_handling(StoryLogger())
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理创作请求，生成章节内容
        
        Args:
            context: {
                "title": "章节标题",
                "summary": "章节概要",
                "scenes": ["场景列表"],
                "goals": ["章节目标"],
                "requirements": "具体要求"
            }
        
        Returns:
            Dict[str, Any]: {
                "content": "故事内容",
                "word_count": 字数统计,
                "scenes": [
                    {
                        "title": "场景标题",
                        "content": "场景内容",
                        "word_count": 字数统计
                    }
                ]
            }
        """
        # 验证输入参数
        required_fields = ["title", "summary", "scenes", "goals", "requirements"]
        for field in required_fields:
            if field not in context:
                raise ValueError(f"Missing required field: {field}")
        
        # 生成章节内容
        self.logger.info(f"开始生成章节: {context['title']}", role=self.name)
        chapter_response = await self.generate_response(
            BasePromptTemplate.format(
                WriterPrompts.WRITE_CHAPTER,
                title=context["title"],
                summary=context["summary"],
                scenes=json.dumps(context["scenes"], ensure_ascii=False),
                goals=json.dumps(context["goals"], ensure_ascii=False),
                requirements=context["requirements"]
            )
        )
        
        # 解析响应
        default_chapter = {
            "content": "",
            "word_count": 0,
            "scenes": [
                {
                    "title": scene,
                    "content": "场景内容生成失败",
                    "word_count": 0
                }
                for scene in context["scenes"]
            ]
        }
        
        chapter = self.parse_json_response(chapter_response, default_chapter)
        
        # 验证和补充内容
        if not chapter.get("content"):
            self.logger.warning("章节内容为空，使用场景内容拼接", role=self.name)
            chapter["content"] = "\n\n".join(
                scene["content"] for scene in chapter.get("scenes", [])
            )
        
        if not chapter.get("word_count"):
            chapter["word_count"] = len(chapter["content"])
        
        self.logger.info(
            f"章节生成完成\n"
            f"标题: {context['title']}\n"
            f"字数: {chapter['word_count']}\n"
            f"场景数: {len(chapter.get('scenes', []))}", 
            role=self.name
        )
        
        return chapter
