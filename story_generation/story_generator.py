from typing import Dict, Any
from story_generation.roles.planner_role import PlannerRole
from story_generation.roles.writer_role import WriterRole
from story_generation.roles.critic_role import CriticRole
from story_generation.config.story_requirements import StoryRequirements
from story_generation.utils.logger import StoryLogger
import asyncio

class StoryGenerator:
    """故事生成器"""
    
    def __init__(self, llm_client):
        """初始化故事生成器"""
        self.llm_client = llm_client
        self.logger = StoryLogger()
        
        # 初始化角色
        self.planner = PlannerRole(llm_client)
        self.writer = WriterRole(llm_client)
        self.critic = CriticRole(llm_client)
        
    async def generate_story(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成完整的故事
        
        Args:
            requirements: 创作需求
            
        Returns:
            完整的故事内容
        """
        story_operation = self.logger.start_operation(
            operation_name="生成故事",
            role="StoryGenerator",
            requirements=requirements
        )
        
        try:
            # 1. 生成故事框架和大纲
            framework = await self.planner.process({"requirements": requirements})
            
            # 2. 生成故事内容
            story_content = []
            chapters = framework.get("outline", {}).get("chapters", [])
            total_chapters = len(chapters)
            
            for i, chapter in enumerate(chapters, 1):
                chapter_operation = self.logger.start_operation(
                    operation_name=f"生成第{i}章",
                    role="StoryGenerator",
                    chapter_title=chapter.get("title", f"第{i}章")
                )
                
                try:
                    # 准备章节信息
                    chapter_info = {
                        "title": chapter.get("title", f"第{i}章"),
                        "summary": chapter.get("summary", ""),
                        "word_count": chapter.get("word_count", "2000-3000"),
                        "progress": f"{(i-1)/total_chapters*100:.1f}%",
                        "scenes": BasePromptTemplate.to_json_str(chapter.get("scenes", [])),
                        "plot_goals": BasePromptTemplate.to_json_str(
                            chapter.get("goals", {}).get("plot", [])
                        ),
                        "character_goals": BasePromptTemplate.to_json_str(
                            chapter.get("goals", {}).get("character", [])
                        ),
                        "theme_goals": BasePromptTemplate.to_json_str(
                            chapter.get("goals", {}).get("theme", [])
                        ),
                        "from_previous": chapter.get("transitions", {}).get("from_previous", ""),
                        "to_next": chapter.get("transitions", {}).get("to_next", "")
                    }
                    
                    # 生成章节内容
                    chapter_content = await self.writer.process(chapter_info)
                    
                    # 评估和修改
                    critique = await self.critic.process({
                        "content": chapter_content,
                        "requirements": requirements,
                        "framework": framework,
                        "chapter_info": chapter_info
                    })
                    
                    if critique.get("overall_rating", 0) < 7:
                        self.logger.warning(
                            f"章节评分较低: {critique.get('overall_rating')}",
                            role="StoryGenerator"
                        )
                        # TODO: 根据评价修改内容
                    
                    story_content.append(chapter_content)
                    chapter_operation.complete()
                    
                except Exception as e:
                    self.logger.error(
                        f"生成第{i}章时出错: {str(e)}",
                        role="StoryGenerator"
                    )
                    chapter_operation.fail(str(e))
                    raise
            
            # 3. 整合结果
            story = {
                "title": framework.get("title", "未命名故事"),
                "framework": framework,
                "content": story_content
            }
            
            story_operation.complete()
            return story
            
        except Exception as e:
            self.logger.error(f"生成故事失败: {str(e)}", role="StoryGenerator")
            story_operation.fail(str(e))
            raise

    async def generate_story_with_feedback(
        self,
        requirements: Dict[str, Any],
        feedback_handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        带反馈的故事生成
        
        Args:
            requirements: 故事需求文本
            feedback_handler: 反馈处理函数，接收当前故事状态，返回反馈信息
        
        Returns:
            Dict[str, Any]: 生成的故事
        """
        # 开始故事生成
        operation_id = self.logger.start_operation(
            operation_name="带反馈的故事生成",
            role="StoryGenerator",
            requirements=requirements
        )
        
        try:
            # 创建需求对象
            config = StoryRequirements.create(requirements)
            self.logger.info("故事需求解析完成", role="StoryGenerator")
            
            # 1. 规划故事框架
            self.logger.info("开始规划故事框架", role="StoryGenerator")
            framework = await self.planner.process(config.to_dict())
            
            # 验证框架数据
            if not framework:
                self.logger.error("故事框架生成失败", role="StoryGenerator", data=framework)
                raise ValueError("故事框架生成失败")
            
            # 记录框架内容
            self.logger.info(
                "框架数据验证",
                role="StoryGenerator",
                data={
                    "title": framework.get("title"),
                    "has_characters": "characters" in framework,
                    "has_themes": "themes" in framework,
                    "has_structure": "structure" in framework,
                    "has_world_building": "world_building" in framework,
                    "has_outline": "outline" in framework,
                    "raw_framework": framework
                }
            )
            
            if not framework.get("title"):
                self.logger.error(
                    "故事框架缺少标题",
                    role="StoryGenerator",
                    data={
                        "framework_keys": list(framework.keys()),
                        "raw_framework": framework
                    }
                )
                raise ValueError("故事框架缺少标题")
            
            if not framework.get("world_building"):
                self.logger.error(
                    "故事框架缺少世界观设定",
                    role="StoryGenerator",
                    data={
                        "framework_keys": list(framework.keys()),
                        "raw_framework": framework
                    }
                )
                raise ValueError("故事框架缺少世界观设定")
                
            if not framework.get("outline", {}).get("chapters"):
                self.logger.error(
                    "故事框架缺少章节大纲",
                    role="StoryGenerator",
                    data={
                        "outline": framework.get("outline"),
                        "raw_framework": framework
                    }
                )
                raise ValueError("故事框架缺少章节大纲")
            
            self.logger.info(
                f"故事框架规划完成",
                role="StoryGenerator",
                data={
                    "title": framework.get("title", "未知"),
                    "themes": framework.get("themes", []),
                    "character_count": len(framework.get("characters", [])),
                    "world_setting": framework.get("world_building", {}).get("setting", "未设置"),
                    "chapter_count": len(framework.get("outline", {}).get("chapters", [])),
                    "pacing_design": "pacing" in framework.get("outline", {}),
                    "raw_framework": framework
                }
            )
            
            # 获取框架反馈
            feedback = await feedback_handler({
                "stage": "framework",
                "framework": framework
            })
            if feedback.get("stop"):
                self.logger.end_operation(
                    operation_id,
                    success=False,
                    error_type="FeedbackStop",
                    error_message=feedback.get("reason")
                )
                return {"status": "stopped", "reason": feedback.get("reason")}
            
            # 2. 生成故事内容
            story_content = []
            chapters = framework.get("outline", {}).get("chapters", [])
            total_chapters = len(chapters)
            
            for i, chapter in enumerate(chapters, 1):
                chapter_operation = self.logger.start_operation(
                    operation_name=f"生成第{i}章",
                    role="StoryGenerator",
                    chapter_title=chapter.get("title", f"第{i}章")
                )
                
                try:
                    # 准备章节上下文
                    chapter_context = {
                        "title": chapter.get("title", f"第{i}章"),
                        "summary": chapter.get("summary", ""),
                        "scenes": chapter.get("scenes", []),
                        "goals": chapter.get("goals", []),
                        "requirements": requirements
                    }
                    
                    # 记录章节上下文
                    self.logger.info(
                        "准备生成章节",
                        role="StoryGenerator",
                        data={
                            "chapter_number": i,
                            "chapter_context": chapter_context
                        }
                    )
                    
                    # 生成章节内容
                    chapter_result = await self.writer.process(chapter_context)
                    
                    # 验证章节内容
                    if not isinstance(chapter_result, dict):
                        self.logger.error(
                            "章节内容格式错误",
                            role="StoryGenerator",
                            data={
                                "expected_type": "dict",
                                "actual_type": type(chapter_result),
                                "raw_result": chapter_result
                            }
                        )
                        raise ValueError(f"章节内容格式错误: {type(chapter_result)}")
                        
                    if not chapter_result.get("content"):
                        self.logger.error(
                            "无法生成章节内容",
                            role="StoryGenerator",
                            data={
                                "chapter_result_keys": list(chapter_result.keys()),
                                "raw_result": chapter_result,
                                "chapter_context": chapter_context
                            }
                        )
                        raise ValueError(f"无法生成章节内容: {chapter_result}")
                        
                    if not isinstance(chapter_result.get("content"), str):
                        self.logger.error(
                            "章节内容类型错误",
                            role="StoryGenerator",
                            data={
                                "expected_type": "str",
                                "actual_type": type(chapter_result.get("content")),
                                "raw_content": chapter_result.get("content")
                            }
                        )
                        raise ValueError(f"章节内容必须是字符串: {type(chapter_result.get('content'))}")
                        
                    story_content.append(chapter_result["content"])
                    
                    self.logger.end_operation(
                        chapter_operation,
                        success=True,
                        content_length=len(chapter_result["content"])
                    )
                    
                    # 获取章节反馈
                    feedback = await feedback_handler({
                        "stage": "chapter",
                        "chapter_index": i,
                        "chapter_content": chapter_result,
                        "story_so_far": "\n\n".join(story_content)
                    })
                    if feedback.get("stop"):
                        self.logger.end_operation(
                            operation_id,
                            success=False,
                            error_type="FeedbackStop",
                            error_message=feedback.get("reason")
                        )
                        return {"status": "stopped", "reason": feedback.get("reason")}
                    
                    # 应用反馈建议
                    if feedback.get("revise"):
                        chapter_context["feedback"] = feedback["revise"]
                        chapter_result = await self.writer.process(chapter_context)
                        story_content[-1] = chapter_result["content"]
                
                except Exception as e:
                    self.logger.end_operation(
                        chapter_operation,
                        success=False,
                        error=str(e),
                        traceback=traceback.format_exc()
                    )
                    raise
            
            # 3. 评估故事质量
            self.logger.info("开始评估故事质量", role="StoryGenerator")
            analysis = await self.critic.process({
                "content": "\n".join(story_content),
                "requirements": requirements,
                "framework": framework
            })
            
            # 4. 整合结果
            result = {
                "title": framework.get("title", "未知标题"),
                "content": "\n\n".join(story_content),
                "framework": framework,
                "analysis": analysis
            }
            
            self.logger.end_operation(
                operation_id,
                success=True,
                total_chapters=total_chapters,
                total_words=len(result["content"]),
                score=analysis.get("score", 0)
            )
            
            return result
            
        except Exception as e:
            self.logger.end_operation(
                operation_id,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc()
            )
            raise
