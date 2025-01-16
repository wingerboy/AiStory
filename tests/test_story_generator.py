import asyncio
import os
import sys
import pytest
from typing import Dict, Any

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from story_generation.story_generator import StoryGenerator
from story_generation.llm_utils import DeepSeekClient
from story_generation.utils.logger import StoryLogger

class TestStoryGenerator:
    """故事生成器测试类"""
    
    def create_generator(self):
        """创建故事生成器实例"""
        # api_key = os.getenv("DEEPSEEK_API_KEY")
        api_key = "sk-"
        if not api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY 环境变量")
        llm_client = DeepSeekClient(api_key=api_key)
        return StoryGenerator(llm_client)
    
    @pytest.mark.asyncio
    async def test_story_generation(self):
        """测试故事生成流程"""
        logger = StoryLogger()
        logger.info("开始测试故事生成", role="TestStoryGenerator")
        
        # 创建生成器
        generator = self.create_generator()
        
        # 准备测试数据
        requirements = """
        写一个3章的奇幻故事，目标读者是青少年。
        主题是关于成长与友情，语言要轻松活泼。
        主角是一个12岁的小女孩，她意外发现自己拥有了魔法能力。
        故事要突出友情的力量，以及成长过程中的勇气和担当。
        每章不少于1000字。
        世界观要新颖有趣，但不要太黑暗。
        """
        
        try:
            # 生成故事
            story = await generator.generate_story(requirements)
            
            # 验证故事结构
            assert isinstance(story, dict), "故事必须是字典格式"
            assert "title" in story, "故事缺少标题"
            assert "framework" in story, "故事缺少框架"
            assert "content" in story, "故事缺少内容"
            assert "analysis" in story, "故事缺少分析"
            
            # 验证框架结构
            framework = story["framework"]
            assert "characters" in framework, "框架缺少角色"
            assert "themes" in framework, "框架缺少主题"
            assert "structure" in framework, "框架缺少结构"
            assert "world_building" in framework, "框架缺少世界观"
            
            # 验证内容结构
            content = story["content"]
            assert isinstance(content, list), "内容必须是列表"
            assert len(content) > 0, "内容不能为空"
            
            for chapter in content:
                assert "title" in chapter, "章节缺少标题"
                assert "content" in chapter, "章节缺少内容"
                assert isinstance(chapter["content"], str), "章节内容必须是字符串"
                assert len(chapter["content"]) >= 1000, "章节内容不能少于1000字"
            
            # 验证分析结构
            analysis = story["analysis"]
            assert "theme_development" in analysis, "分析缺少主题发展"
            assert "character_arcs" in analysis, "分析缺少角色弧"
            assert "world_consistency" in analysis, "分析缺少世界观一致性"
            assert "feedback" in analysis, "分析缺少反馈"
            
            # 打印结果摘要
            print("\n=== 故事生成完成 ===")
            print(f"标题: {story['title']}")
            print(f"主题: {', '.join(framework['themes'])}")
            print(f"章节数: {len(content)}")
            print(f"总字数: {sum(len(chapter['content']) for chapter in content)}")
            print("\n=== 分析摘要 ===")
            print(f"主题发展: {analysis['theme_development']}")
            print(f"反馈建议: {analysis['feedback']}")
            
        except Exception as e:
            print(f"错误: {str(e)}")
            # traceback.print_exc()
            
# 运行测试
if __name__ == "__main__":
    async def main():
        # 创建测试类实例
        test = TestStoryGenerator()
        # 运行测试
        await test.test_story_generation()
    
    # 运行异步主函数
    asyncio.run(main())