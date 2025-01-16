# AI Story Generation Framework

一个基于大语言模型的智能故事生成框架，使用多角色协作方式创作故事。

## 功能特点

- 多角色协作：规划者、作家、评论家共同完成故事创作
- 记忆管理：维护故事上下文和角色发展
- 实时反馈：支持用户在生成过程中提供反馈
- 完整日志：记录生成过程和资源使用情况

## 项目结构

```
story_generation/
├── roles/              # 角色定义
│   ├── base_role.py    # 角色基类
│   ├── planner_role.py # 规划者角色
│   ├── writer_role.py  # 作家角色
│   └── critic_role.py  # 评论家角色
├── utils/              # 工具类
│   ├── logger.py       # 日志管理
│   └── usage_stats.py  # 使用统计
├── llm_utils.py        # LLM客户端
└── story_generator.py  # 故事生成器
```

## 使用示例

```python
from story_generation import StoryGenerator

async def main():
    # 初始化生成器
    generator = StoryGenerator(api_key="your-api-key")
    
    # 生成故事
    story = await generator.generate_story(
        prompt="写一个关于友情和成长的温暖故事",
        max_chapters=5
    )
    
    print(f"故事标题: {story['title']}")
    print(f"故事内容:\n{story['content']}")
    
    # 带反馈的生成
    async def feedback_handler(story_data):
        print(f"当前进度：第{story_data['current_chapter']}章")
        return {"continue": True}
    
    story = await generator.generate_story_with_feedback(
        prompt="写一个冒险故事",
        feedback_callback=feedback_handler,
        max_chapters=5
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## 技术栈

- Python 3.8+
- OpenAI/DeepSeek API
- asyncio - 异步处理
- tenacity - 重试机制

## 开发说明

本项目采用模块化设计：
- 每个角色都继承自基类，便于扩展新角色
- 使用依赖注入方式管理LLM客户端
- 完整的日志和统计功能，方便调试和优化
- 异步设计，支持实时反馈
