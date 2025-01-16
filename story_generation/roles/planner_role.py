from typing import Dict, Any
from .base_role import BaseRole
from ..prompts.base_prompts import RolePrompts, PlannerPrompts, BasePromptTemplate
from ..utils.logger import StoryLogger
import json
import re

class PlannerRole(BaseRole):
    """规划者角色，负责故事规划和情节设计"""
    
    def __init__(self, llm_client):
        """
        初始化规划者角色
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(
            name="Planner",
            system_prompt=RolePrompts.FRAMEWORK_PLANNER,  # 默认使用框架设计角色
            llm_client=llm_client
        )
        self.logger = StoryLogger()
    
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
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理规划请求，包括生成框架和大纲
        
        Args:
            context: {
                "requirements": "故事需求文本"
            }
        
        Returns:
            Dict[str, Any]: {
                "title": "故事标题",
                "characters": ["角色信息"],
                "themes": ["主题"],
                "structure": {
                    "beginning": "开端",
                    "middle": "发展",
                    "end": "结局"
                },
                "outline": {
                    "chapters": ["章节大纲"],
                    "next_steps": ["后续建议"]
                }
            }
            
        Raises:
            ValueError: 当必要的参数缺失或格式不正确时抛出
        """
        # 验证输入参数
        if not isinstance(context, dict):
            raise ValueError("Context must be a dictionary")
        if "requirements" not in context:
            raise ValueError("Missing required field: requirements")
        if not isinstance(context["requirements"], str):
            raise ValueError("Requirements must be a string")
        if not context["requirements"].strip():
            raise ValueError("Requirements cannot be empty")
        
        # 1. 使用框架设计专家生成框架
        self.logger.info("开始生成故事框架", role=self.name)
        framework_response = await self.generate_response(
            BasePromptTemplate.format(
                PlannerPrompts.FRAMEWORK_USER,
                requirements=context["requirements"]
            )
        )
        
        # 解析框架响应
        default_framework = {
            "title": "未命名故事",
            "themes": [],
            "characters": [],
            "structure": {
                "beginning": "开始",
                "middle": "发展",
                "end": "结局",
                "key_points": []
            },
            "world_building": {
                "setting": "待定",
                "rules": [],
                "unique_elements": []
            }
        }
        framework = self.parse_json_response(framework_response, default_framework)
        
        self.logger.info(
            f"故事框架生成成功\n"
            f"标题: {framework.get('title', 'Unknown')}\n"
            f"角色数: {len(framework.get('characters', []))}\n"
            f"主题数: {len(framework.get('themes', []))}\n"
            f"世界观: {framework.get('world_building', {}).get('setting', '未设置')}", 
            role=self.name
        )
        
        # 2. 切换到大纲设计专家
        self.logger.info("切换到大纲设计专家", role=self.name)
        self.system_prompt = RolePrompts.OUTLINE_PLANNER
        
        # 3. 生成章节大纲
        self.logger.info("开始生成章节大纲", role=self.name)
        outline_response = await self.generate_response(
            BasePromptTemplate.format(
                PlannerPrompts.OUTLINE_USER,
                title=framework.get("title", "未命名故事"),
                themes=BasePromptTemplate.to_json_str(framework.get("themes", [])),
                characters=BasePromptTemplate.to_json_str(framework.get("characters", [])),
                structure=BasePromptTemplate.to_json_str(framework.get("structure", {})),
                world_building=BasePromptTemplate.to_json_str(framework.get("world_building", {})),
                requirements=context["requirements"]
            )
        )
        
        try:
            # 预处理响应文本
            processed_response = self._preprocess_json_response(outline_response)
            self.logger.debug(f"处理后的响应:\n{processed_response}", role=self.name)
            
            detailed_outline = json.loads(processed_response)
            if not detailed_outline.get("chapters"):
                self.logger.warning("大纲中缺少章节", role=self.name)
                detailed_outline["chapters"] = []
                
            self.logger.info(
                f"章节大纲生成成功\n"
                f"章节数: {len(detailed_outline.get('chapters', []))}\n"
                f"节奏设计: {'tension_curve' in detailed_outline.get('pacing', {})}\n"
                f"设置回收: {'setup_payoffs' in detailed_outline}", 
                role=self.name
            )
        except json.JSONDecodeError as e:
            self.logger.warning(
                f"大纲解析失败\n"
                f"错误信息: {str(e)}\n"
                f"原始响应:\n{outline_response}\n"
                f"尝试位置: {e.pos}\n"
                f"出错行: {outline_response.splitlines()[len(outline_response[:e.pos].splitlines())-1]}\n"
                f"使用后备方案",
                role=self.name
            )
            detailed_outline = self._parse_outline_fallback(outline_response)
        
        # 4. 整合结果
        framework["outline"] = detailed_outline
        self.logger.info("故事规划完成", role=self.name)
        return framework
    
    def _parse_framework_fallback(self, response: str) -> Dict[str, Any]:
        """
        解析非JSON格式的框架响应
        
        Args:
            response: 原始响应文本
        
        Returns:
            Dict[str, Any]: 解析后的框架数据
        """
        # 预编译所有正则表达式
        PATTERNS = {
            "title": [
                re.compile(r"标题[：:]\s*(.+)(?:\n|$)"),
                re.compile(r"《(.+)》"),
                re.compile(r"^(.+?)(?:[\n\。]|$)")
            ],
            "char_section": re.compile(r"(?:角色|人物)[：:](.*?)(?=(?:主题|世界观)[：:]|\Z)", re.DOTALL),
            "char_info": re.compile(r"(?:^|\n)[-\s]*(.+?)[:：](.+?)(?=\n|$)"),
            "theme_section": re.compile(r"主题[：:](.*?)(?=(?:结构|世界观)[：:]|\Z)", re.DOTALL),
            "theme_split": re.compile(r"[,，、]"),
            "world_section": re.compile(r"世界观[：:](.*?)(?=\n\n|\Z)", re.DOTALL),
            "structure": {
                "beginning": re.compile(r"开[始端][：:](.*?)(?=发展[：:]|\n\n|\Z)", re.DOTALL),
                "middle": re.compile(r"发展[：:](.*?)(?=结[局尾][：:]|\n\n|\Z)", re.DOTALL),
                "end": re.compile(r"结[局尾][：:](.*?)(?=\n\n|\Z)", re.DOTALL),
                "key_points": re.compile(r"关键[节点点][：:](.*?)(?=\n\n|\Z)", re.DOTALL)
            }
        }
        
        # 提取标题
        title = "未命名故事"
        for pattern in PATTERNS["title"]:
            if match := pattern.search(response):
                title = match.group(1).strip()
                break
        
        # 提取角色信息
        characters = []
        if char_section := PATTERNS["char_section"].search(response):
            char_text = char_section.group(1)
            for match in PATTERNS["char_info"].finditer(char_text):
                name, desc = match.groups()
                characters.append({
                    "name": name.strip(),
                    "description": desc.strip(),
                    "personality": [],
                    "goals": [],
                    "growth_arc": ""
                })
        
        # 提取主题
        themes = []
        if theme_section := PATTERNS["theme_section"].search(response):
            theme_text = theme_section.group(1)
            themes = [t.strip() for t in PATTERNS["theme_split"].split(theme_text) if t.strip()]
        
        # 提取世界观
        world_building = {
            "setting": "",
            "rules": [],
            "unique_elements": []
        }
        if world_section := PATTERNS["world_section"].search(response):
            world_building["setting"] = world_section.group(1).strip()
        
        # 提取结构
        structure = {
            "beginning": "",
            "middle": "",
            "end": "",
            "key_points": []
        }
        for key, pattern in PATTERNS["structure"].items():
            if match := pattern.search(response):
                if key == "key_points":
                    points = match.group(1).strip().split("\n")
                    structure[key] = [p.strip("- ").strip() for p in points if p.strip()]
                else:
                    structure[key] = match.group(1).strip()
        
        return {
            "title": title,
            "characters": characters,
            "themes": themes,
            "structure": structure,
            "world_building": world_building
        }
    
    def _parse_outline_fallback(self, response: str) -> Dict[str, Any]:
        """
        解析非JSON格式的大纲响应
        
        Args:
            response: 原始响应文本
        
        Returns:
            Dict[str, Any]: 解析后的大纲数据
        """
        chapters = []
        current_chapter = None
        current_scene = None
        
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是章节标题
            if line.startswith(("第", "Chapter", "章")):
                if current_chapter:
                    # 确保每个章节都有必要的字段
                    if not current_chapter.get("goals"):
                        current_chapter["goals"] = {
                            "plot": [],
                            "character": [],
                            "theme": []
                        }
                    if not current_chapter.get("transitions"):
                        current_chapter["transitions"] = {
                            "from_previous": "",
                            "to_next": ""
                        }
                    chapters.append(current_chapter)
                    
                current_chapter = {
                    "title": line,
                    "summary": "",
                    "word_count": "1000",  # 默认字数
                    "progress": "0%",
                    "scenes": [],
                    "goals": {
                        "plot": [],
                        "character": [],
                        "theme": []
                    },
                    "transitions": {
                        "from_previous": "",
                        "to_next": ""
                    }
                }
                current_scene = None
                
            # 检查是否是场景
            elif line.startswith(("场景", "Scene")):
                if current_chapter:
                    current_scene = {
                        "title": line,
                        "description": "",
                        "purpose": "",
                        "characters": [],
                        "emotions": [],
                        "key_elements": [],
                        "setup_points": [],
                        "payoff_points": []
                    }
                    current_chapter["scenes"].append(current_scene)
                    
            # 其他内容作为描述或总结
            elif current_scene:
                current_scene["description"] += line + "\n"
            elif current_chapter:
                current_chapter["summary"] += line + "\n"
        
        # 添加最后一章
        if current_chapter:
            # 确保最后一章也有必要的字段
            if not current_chapter.get("goals"):
                current_chapter["goals"] = {
                    "plot": [],
                    "character": [],
                    "theme": []
                }
            if not current_chapter.get("transitions"):
                current_chapter["transitions"] = {
                    "from_previous": "",
                    "to_next": ""
                }
            chapters.append(current_chapter)
            
        # 清理描述和总结中的多余换行
        for chapter in chapters:
            chapter["summary"] = chapter["summary"].strip()
            for scene in chapter["scenes"]:
                scene["description"] = scene["description"].strip()
        
        return {
            "chapters": chapters,
            "pacing": {
                "tension_curve": [],
                "emotional_beats": []
            },
            "setup_payoffs": {
                "setups": [],
                "payoffs": []
            }
        }
