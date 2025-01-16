import os
import sys
import asyncio
import json
import traceback
# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from story_generation.roles.planner_role import PlannerRole
from story_generation.llm_utils import DeepSeekClient


async def test_planner():
    # 初始化 LLM 客户端和规划者角色
    llm_client = DeepSeekClient(api_key="sk-76284e5c07964ddb9a5134ed6c094e8e")
    planner = PlannerRole(llm_client)
    
    # 准备故事需求
    requirements = {
        "requirements": """
        写一个3章的奇幻故事，目标读者是青少年。
        主题是关于成长与友情，语言要轻松活泼。
        主角是一个12岁的小女孩，她意外发现自己拥有了魔法能力。
        故事要突出友情的力量，以及成长过程中的勇气和担当。
        每章不少于1000字。
        世界观要新颖有趣，但不要太黑暗。
        """
    }
    
    try:
        # 执行规划流程
        result = await planner.process(requirements)
        
        # 验证结果格式
        assert isinstance(result, dict), "结果必须是字典格式"
        assert "title" in result, "缺少标题"
        assert "characters" in result, "缺少角色"
        assert "themes" in result, "缺少主题"
        assert "structure" in result, "缺少结构"
        assert "world_building" in result, "缺少世界观"
        assert "outline" in result, "缺少大纲"
        
        # 验证结构内容
        assert isinstance(result["characters"], list), "角色必须是列表"
        assert isinstance(result["themes"], list), "主题必须是列表"
        assert isinstance(result["structure"], dict), "结构必须是字典"
        assert isinstance(result["world_building"], dict), "世界观必须是字典"
        assert isinstance(result["outline"], dict), "大纲必须是字典"
        
        # 验证大纲格式
        outline = result["outline"]
        assert "chapters" in outline, "大纲缺少章节"
        assert isinstance(outline["chapters"], list), "章节必须是列表"
        assert len(outline["chapters"]) > 0, "章节不能为空"
        
        # 验证章节格式
        for chapter in outline["chapters"]:
            assert "title" in chapter, "章节缺少标题"
            assert "summary" in chapter, "章节缺少摘要"
            assert "scenes" in chapter, "章节缺少场景"
            assert isinstance(chapter["scenes"], list), "场景必须是列表"
        
        # 打印完整结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"错误: {str(e)}")
        traceback.print_exc()
        
if __name__ == "__main__":
    asyncio.run(test_planner())
