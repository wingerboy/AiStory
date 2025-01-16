from typing import Dict, Any, List
from .base_role import BaseRole
from ..prompts.base_prompts import RolePrompts, CriticPrompts, BasePromptTemplate
from ..utils.logger import StoryLogger
from ..utils.error_handler import with_error_handling, ContentParsingError
from ..config.settings import Settings, RoleType
import json
import re

class CriticRole(BaseRole):
    """评论者角色，负责故事评估和分析"""
    
    def __init__(self, llm_client):
        """
        初始化评论者角色
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(
            name="Critic",
            system_prompt=RolePrompts.CRITIC,
            llm_client=llm_client
        )
        self.logger = StoryLogger()
        self.settings = Settings()
        self.config = self.settings.get_role_config(RoleType.CRITIC)
    
    @with_error_handling(StoryLogger())
    async def analyze_story(self, content: str) -> Dict[str, Any]:
        """
        分析整个故事
        
        Args:
            content: 故事内容
        
        Returns:
            Dict[str, Any]: {
                "overall_rating": 总体评分(1-10),
                "analysis": {
                    "plot": "情节分析",
                    "characters": "人物分析",
                    "theme": "主题分析",
                    "structure": "结构分析",
                    "details": "细节分析"
                },
                "issues": [
                    {
                        "type": "问题类型",
                        "description": "问题描述",
                        "suggestion": "改进建议"
                    }
                ]
            }
        """
        if not content or not isinstance(content, str):
            raise ValueError("故事内容不能为空且必须是字符串")
            
        self.logger.info("开始分析故事", role=self.name)
        
        # 生成分析
        analysis_response = await self.generate_response(
            BasePromptTemplate.format(
                CriticPrompts.ANALYZE_STORY,
                content=content[:self.settings.generation["max_content_length"]]
            )
        )
        
        # 解析响应
        default_analysis = {
            "overall_rating": 5,
            "analysis": {
                "plot": "情节分析生成失败",
                "characters": "人物分析生成失败",
                "theme": "主题分析生成失败",
                "structure": "结构分析生成失败",
                "details": "细节分析生成失败"
            },
            "issues": []
        }
        
        analysis = self.parse_json_response(analysis_response, default_analysis)
        
        # 验证评分范围
        rating = analysis.get("overall_rating", 5)
        if not isinstance(rating, (int, float)) or not (1 <= rating <= 10):
            self.logger.warning("评分超出范围，使用默认值5", role=self.name)
            analysis["overall_rating"] = 5
            
        self.logger.info(
            f"故事分析完成\n"
            f"总体评分: {analysis['overall_rating']}\n"
            f"发现问题: {len(analysis.get('issues', []))}个", 
            role=self.name
        )
        
        return analysis
    
    @with_error_handling(StoryLogger())
    async def review_chapter(self, content: str, outline: Dict[str, Any]) -> Dict[str, Any]:
        """
        审查单个章节
        
        Args:
            content: 章节内容
            outline: 原始大纲
        
        Returns:
            Dict[str, Any]: 与 analyze_story 相同的格式，但更关注章节级别的分析
        """
        self.logger.info(
            "开始审查章节",
            role=self.name,
            content_length=len(content),
            outline_title=outline.get("title", "未命名章节")
        )
        
        review_response = await self.generate_response(
            BasePromptTemplate.format(
                CriticPrompts.REVIEW_CHAPTER,
                content=content[:self.settings.generation["max_content_length"]],
                outline=BasePromptTemplate.to_json_str(outline)
            )
        )
        
        try:
            review = json.loads(review_response)
            
            # 验证评分范围
            rating = review.get("overall_rating", self.config["default_rating"])
            review["overall_rating"] = min(
                max(rating, self.config["min_rating"]),
                self.config["max_rating"]
            )
            
            # 验证分析维度
            for aspect in self.config["analysis_aspects"]:
                if aspect not in review.get("analysis", {}):
                    self.logger.warning(
                        f"缺少分析维度: {aspect}",
                        role=self.name
                    )
                    review.setdefault("analysis", {})[aspect] = "未提供分析"
            
            self.logger.info(
                "章节审查完成",
                role=self.name,
                rating=review["overall_rating"],
                issue_count=len(review.get("issues", [])),
                highlight_count=len(review.get("highlights", [])),
                metrics={
                    "rating": review["overall_rating"],
                    "issue_count": len(review.get("issues", [])),
                    "highlight_count": len(review.get("highlights", [])),
                    "suggestion_count": len(review.get("next_steps", []))
                }
            )
            
            return review
            
        except json.JSONDecodeError as e:
            self.logger.warning(
                "审查解析失败，使用后备方案",
                role=self.name,
                error=str(e),
                position=e.pos
            )
            return self._parse_analysis_fallback(review_response)
    
    @with_error_handling(StoryLogger())
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理输入并返回结果
        
        Args:
            context: 上下文信息，包含：
                - content: 要分析的内容
                - outline: 可选，章节大纲
                - type: 可选，分析类型（"story"/"chapter"）
                
        Returns:
            Dict[str, Any]: 分析结果
            
        Raises:
            ValueError: 当必要的参数缺失或格式不正确时抛出
        """
        # 验证基本参数
        if not isinstance(context, dict):
            raise ValueError("Context must be a dictionary")
            
        content = context.get("content")
        if not content:
            raise ValueError("Content is required for analysis")
        if not isinstance(content, str):
            raise ValueError("Content must be a string")
            
        # 验证可选参数
        outline = context.get("outline")
        if outline is not None and not isinstance(outline, dict):
            raise ValueError("Outline must be a dictionary if provided")
            
        analysis_type = context.get("type", "story")
        if analysis_type not in ["story", "chapter"]:
            raise ValueError("Analysis type must be either 'story' or 'chapter'")
        
        # 根据类型调用相应的分析方法
        if analysis_type == "chapter" and outline:
            return await self.review_chapter(content, outline)
        else:
            return await self.analyze_story(content)
    
    def _parse_analysis_fallback(self, response: str) -> Dict[str, Any]:
        """
        解析非JSON格式的分析响应
        
        Args:
            response: 原始响应文本
        
        Returns:
            Dict[str, Any]: 解析后的分析数据
        """
        # 预编译所有正则表达式
        PATTERNS = {
            "rating": re.compile(r"评分[：:]\s*(\d+)"),
            "analysis": {
                "plot": re.compile(r"情节[：:](.*?)(?=人物[：:]|\n\n|\Z)", re.DOTALL),
                "characters": re.compile(r"人物[：:](.*?)(?=主题[：:]|\n\n|\Z)", re.DOTALL),
                "theme": re.compile(r"主题[：:](.*?)(?=结构[：:]|\n\n|\Z)", re.DOTALL),
                "structure": re.compile(r"结构[：:](.*?)(?=细节[：:]|\n\n|\Z)", re.DOTALL),
                "details": re.compile(r"细节[：:](.*?)(?=\n\n|\Z)", re.DOTALL)
            },
            "sections": {
                "issues": re.compile(r"问题[：:](.*?)(?=亮点[：:]|\n\n|\Z)", re.DOTALL),
                "highlights": re.compile(r"亮点[：:](.*?)(?=建议[：:]|\n\n|\Z)", re.DOTALL),
                "suggestions": re.compile(r"建议[：:](.*?)(?=\Z)", re.DOTALL)
            },
            "splitter": re.compile(r"[\n。]")
        }
        
        # 提取评分
        rating = self.config["default_rating"]
        if rating_match := PATTERNS["rating"].search(response):
            try:
                rating = int(rating_match.group(1))
                rating = min(max(rating, self.config["min_rating"]), self.config["max_rating"])
            except ValueError:
                pass
        
        # 提取分析内容
        analysis = {aspect: "" for aspect in self.config["analysis_aspects"]}
        for key, pattern in PATTERNS["analysis"].items():
            if match := pattern.search(response):
                analysis[key] = match.group(1).strip()
        
        # 提取问题列表
        issues = []
        if issues_match := PATTERNS["sections"]["issues"].search(response):
            issue_texts = [text.strip() for text in PATTERNS["splitter"].split(issues_match.group(1))]
            issues = [
                {
                    "type": "待分类",
                    "description": text,
                    "suggestion": "需要进一步分析"
                }
                for text in issue_texts if text
            ]
        
        # 提取亮点列表（使用集合去重）
        highlights = set()
        if highlights_match := PATTERNS["sections"]["highlights"].search(response):
            highlights.update(
                text.strip()
                for text in PATTERNS["splitter"].split(highlights_match.group(1))
                if text.strip()
            )
        
        # 提取建议列表（使用集合去重）
        next_steps = set()
        if suggestions_match := PATTERNS["sections"]["suggestions"].search(response):
            next_steps.update(
                text.strip()
                for text in PATTERNS["splitter"].split(suggestions_match.group(1))
                if text.strip()
            )
        
        self.logger.info(
            "使用后备方案解析完成",
            role=self.name,
            rating=rating,
            issue_count=len(issues),
            highlight_count=len(highlights)
        )
        
        return {
            "overall_rating": rating,
            "analysis": analysis,
            "issues": issues,
            "highlights": list(highlights),  # 转换回列表
            "next_steps": list(next_steps)   # 转换回列表
        }
