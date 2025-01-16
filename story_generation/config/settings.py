from typing import Dict, Any
from enum import Enum
import os
import json

class RoleType(Enum):
    """角色类型枚举"""
    FRAMEWORK_PLANNER = "framework_planner"
    OUTLINE_PLANNER = "outline_planner"
    WRITER = "writer"
    CRITIC = "critic"

class Settings:
    """配置管理类"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._load_config()
        self._initialized = True
    
    def _load_config(self):
        """加载配置文件"""
        # 默认配置
        self._config = {
            "logging": {
                "level": "DEBUG",
                "file_path": "logs/story_generation.log",
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5
            },
            "generation": {
                "max_retries": 3,
                "timeout": 30,  # seconds
                "batch_size": 1000,
                "max_content_length": 50000
            },
            "roles": {
                "framework_planner": {
                    "max_frameworks": 3,
                    "min_rating": 7
                },
                "outline_planner": {
                    "max_chapters": 50,
                    "min_scenes_per_chapter": 1,
                    "max_scenes_per_chapter": 10
                },
                "writer": {
                    "min_words_per_scene": 100,
                    "max_words_per_scene": 2000,
                    "default_rating": 5
                },
                "critic": {
                    "min_rating": 1,
                    "max_rating": 10,
                    "default_rating": 5,
                    "analysis_aspects": [
                        "plot",
                        "characters",
                        "theme",
                        "structure",
                        "details"
                    ]
                }
            },
            "patterns": {
                "scene_split": r"\n*场景\s*\d*[：:：\s]*",
                "title_extract": r"^(.+?)(?:\n|$)",
                "character_extract": r"(?:^|\n)[-\s]*(.+?)[:：]",
                "emotion_extract": r"情感[：:](.*?)(?=\n\n|\Z)"
            }
        }
        
        # 尝试从文件加载配置
        config_path = os.getenv("STORY_CONFIG_PATH", "config/story_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._update_config(self._config, file_config)
            except Exception as e:
                print(f"加载配置文件失败: {str(e)}")
    
    def _update_config(self, base: Dict[str, Any], update: Dict[str, Any]):
        """递归更新配置"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._update_config(base[key], value)
            else:
                base[key] = value
    
    @property
    def logging(self) -> Dict[str, Any]:
        """日志配置"""
        return self._config["logging"]
    
    @property
    def generation(self) -> Dict[str, Any]:
        """生成配置"""
        return self._config["generation"]
    
    @property
    def roles(self) -> Dict[str, Dict[str, Any]]:
        """角色配置"""
        return self._config["roles"]
    
    @property
    def patterns(self) -> Dict[str, str]:
        """正则表达式模式"""
        return self._config["patterns"]
    
    def get_role_config(self, role_type: RoleType) -> Dict[str, Any]:
        """获取指定角色的配置"""
        return self.roles[role_type.value]
    
    def get_pattern(self, pattern_name: str) -> str:
        """获取指定的正则表达式模式"""
        return self.patterns[pattern_name]
