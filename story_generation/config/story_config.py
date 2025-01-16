"""故事生成配置"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class StoryType(Enum):
    """故事类型"""
    FANTASY = "奇幻"
    SCIFI = "科幻"
    ROMANCE = "言情"
    MYSTERY = "悬疑"
    ADVENTURE = "冒险"
    HISTORICAL = "历史"
    COMEDY = "喜剧"
    DRAMA = "剧情"
    HORROR = "恐怖"
    THRILLER = "惊悚"

class AudienceType(Enum):
    """目标受众"""
    CHILDREN = "儿童"
    YOUNG_ADULT = "青少年"
    ADULT = "成人"
    ALL_AGES = "全年龄"

class StoryLength(Enum):
    """故事长度"""
    SHORT = "短篇"  # 1-3章
    MEDIUM = "中篇"  # 4-10章
    LONG = "长篇"   # 10章以上

@dataclass
class NamingConvention:
    """角色命名规则"""
    style: str = "现代"  # 现代、古风、玄幻等
    language: str = "中文"  # 中文、英文、日文等
    patterns: List[str] = field(default_factory=list)  # 特定的命名模式
    forbidden: List[str] = field(default_factory=list)  # 禁用的名字或模式
    
@dataclass
class ThemeRequirements:
    """主题要求"""
    main_theme: str  # 主题
    sub_themes: List[str] = field(default_factory=list)  # 副主题
    mood: str = "不限"  # 情感基调
    message: str = ""  # 主旨寓意

@dataclass
class StyleGuide:
    """写作风格指南"""
    tone: str = "不限"  # 叙事语气
    pov: str = "第三人称"  # 视角
    tense: str = "过去时"  # 时态
    narrative_style: str = "不限"  # 叙事风格（写实、意识流等）
    language_style: str = "不限"  # 语言风格（简洁、华丽等）

@dataclass
class QualityRequirements:
    """质量要求"""
    min_words_per_chapter: int = 1000  # 每章最少字数
    max_words_per_chapter: int = 3000  # 每章最多字数
    min_chapters: int = 1  # 最少章节数
    max_chapters: int = 20  # 最多章节数
    readability_level: str = "中等"  # 可读性级别
    content_rating: str = "全年龄"  # 内容分级

@dataclass
class CharacterRequirements:
    """角色要求"""
    min_characters: int = 1  # 最少角色数
    max_characters: int = 10  # 最多角色数
    protagonist_traits: List[str] = field(default_factory=list)  # 主角特征
    relationships: List[Dict[str, str]] = field(default_factory=list)  # 角色关系
    character_arcs: List[Dict[str, str]] = field(default_factory=list)  # 角色成长路线

@dataclass
class PlotRequirements:
    """情节要求"""
    plot_structure: str = "三幕式"  # 故事结构
    required_elements: List[str] = field(default_factory=list)  # 必需元素
    forbidden_elements: List[str] = field(default_factory=list)  # 禁用元素
    plot_twists: int = 0  # 情节转折次数
    subplots: int = 0  # 支线数量

@dataclass
class StoryConfig:
    """故事生成配置"""
    story_type: StoryType = StoryType.DRAMA
    audience: AudienceType = AudienceType.ALL_AGES
    length: StoryLength = StoryLength.MEDIUM
    naming: NamingConvention = field(default_factory=NamingConvention)
    theme: ThemeRequirements = field(default_factory=lambda: ThemeRequirements(main_theme="成长"))
    style: StyleGuide = field(default_factory=StyleGuide)
    quality: QualityRequirements = field(default_factory=QualityRequirements)
    character: CharacterRequirements = field(default_factory=CharacterRequirements)
    plot: PlotRequirements = field(default_factory=PlotRequirements)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "story_type": self.story_type.value,
            "target_audience": self.audience.value,
            "length": self.length.value,
            "naming_convention": {
                "style": self.naming.style,
                "language": self.naming.language,
                "patterns": self.naming.patterns,
                "forbidden": self.naming.forbidden
            },
            "theme": {
                "main": self.theme.main_theme,
                "sub_themes": self.theme.sub_themes,
                "mood": self.theme.mood,
                "message": self.theme.message
            },
            "style_guide": {
                "tone": self.style.tone,
                "pov": self.style.pov,
                "tense": self.style.tense,
                "narrative_style": self.style.narrative_style,
                "language_style": self.style.language_style
            },
            "quality_requirements": {
                "words_per_chapter": {
                    "min": self.quality.min_words_per_chapter,
                    "max": self.quality.max_words_per_chapter
                },
                "chapters": {
                    "min": self.quality.min_chapters,
                    "max": self.quality.max_chapters
                },
                "readability": self.quality.readability_level,
                "content_rating": self.quality.content_rating
            },
            "character_requirements": {
                "count": {
                    "min": self.character.min_characters,
                    "max": self.character.max_characters
                },
                "protagonist_traits": self.character.protagonist_traits,
                "relationships": self.character.relationships,
                "character_arcs": self.character.character_arcs
            },
            "plot_requirements": {
                "structure": self.plot.plot_structure,
                "required_elements": self.plot.required_elements,
                "forbidden_elements": self.plot.forbidden_elements,
                "plot_twists": self.plot.plot_twists,
                "subplots": self.plot.subplots
            }
        }
    
    @classmethod
    def create_simple(cls, 
                     story_type: str,
                     audience: str,
                     length: str,
                     main_theme: str,
                     style: Optional[Dict[str, str]] = None) -> 'StoryConfig':
        """创建简单配置"""
        config = cls(
            story_type=StoryType(story_type),
            audience=AudienceType(audience),
            length=StoryLength(length),
            theme=ThemeRequirements(main_theme=main_theme)
        )
        
        if style:
            config.style = StyleGuide(**style)
            
        return config
