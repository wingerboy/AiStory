import pytest
import json
from unittest.mock import Mock, patch
from story_generation.roles.writer_role import WriterRole
from story_generation.utils.error_handler import ContentParsingError
from story_generation.config.settings import Settings

@pytest.fixture
def mock_llm_client():
    return Mock()

@pytest.fixture
def writer_role(mock_llm_client):
    return WriterRole(mock_llm_client)

@pytest.fixture
def sample_context():
    return {
        "title": "新的开始",
        "summary": "艾玛进入魔法学院的第一天",
        "scenes": ["报到场景", "入学仪式", "相遇卢克"],
        "goals": ["介绍主角", "建立世界观"],
        "requirements": {
            "style": "轻松欢快",
            "word_count": {
                "min": 500,
                "max": 2000
            },
            "focus": ["环境描写", "人物对话", "情感表达"]
        }
    }

@pytest.fixture
def sample_response():
    return {
        "content": """
        阳光透过魔法学院古老的彩绘玻璃窗，在大厅的石板地面上投下斑斓的光影。艾玛站在入口处，仰望着高耸的穹顶，心中充满了期待和些许紧张。这就是她梦寐以求的魔法学院！

        "新生报到处在左边。"一个温和的声音传来。艾玛转头看去，是一位戴着圆框眼镜的男生，他的校袍上别着高年级学生的徽章。

        "谢谢！"艾玛露出灿烂的笑容，"我是艾玛，今天刚来报到。"

        "我是卢克，"男生微微点头，"作为学长，我可以带你参观一下学院。"

        艾玛惊喜地发现，原本内向的卢克在谈到魔法课程时会变得异常健谈。当他们经过图书馆时，卢克的眼睛闪闪发亮，滔滔不绝地介绍着各种魔法典籍。

        "你对魔法真的很了解呢！"艾玛由衷地赞叹道。

        卢克不好意思地推了推眼镜，"如果你有任何问题，随时都可以来找我。"

        这一刻，艾玛感觉自己不仅找到了一位向导，更找到了一位潜在的好朋友。魔法学院的生活，正在以一种美好的方式展开。
        """,
        "word_count": 1500,
        "scenes": [
            {
                "title": "报到场景",
                "content": "阳光透过魔法学院古老的彩绘玻璃窗...",
                "characters": ["艾玛"],
                "emotions": ["期待", "紧张"],
                "environment": "魔法学院大厅"
            },
            {
                "title": "相遇卢克",
                "content": "一个温和的声音传来...",
                "characters": ["艾玛", "卢克"],
                "emotions": ["友好", "惊喜"],
                "dialogue": ["问路", "自我介绍", "学院介绍"]
            }
        ]
    }

@pytest.mark.asyncio
async def test_process_success(writer_role, mock_llm_client, sample_context, sample_response):
    """测试正常处理流程"""
    # 设置模拟响应
    mock_llm_client.generate.return_value = json.dumps(sample_response)
    
    # 执行处理
    result = await writer_role.process(sample_context)
    
    # 验证结果
    assert result["word_count"] >= 500
    assert result["word_count"] <= 2000
    assert len(result["scenes"]) == len(sample_context["scenes"])
    
    # 验证场景内容
    for scene in result["scenes"]:
        assert "title" in scene
        assert "content" in scene
        assert "characters" in scene
        assert "emotions" in scene
        assert len(scene["content"]) > 0
        assert len(scene["characters"]) > 0
        assert len(scene["emotions"]) > 0

@pytest.mark.asyncio
async def test_process_style_requirements(writer_role, mock_llm_client, sample_context):
    """测试写作风格要求"""
    context = sample_context.copy()
    context["requirements"]["style"] = "悬疑紧张"
    
    mock_llm_client.generate.return_value = json.dumps({
        "content": "神秘的脚步声在走廊回荡...",
        "word_count": 1000,
        "scenes": [{
            "title": "神秘事件",
            "content": "诡异的氛围笼罩着整个学院...",
            "emotions": ["恐惧", "好奇"],
            "environment": "阴森的走廊"
        }]
    })
    
    result = await writer_role.process(context)
    assert "神秘" in result["content"] or "诡异" in result["content"]
    assert any("恐惧" in scene["emotions"] for scene in result["scenes"])

@pytest.mark.asyncio
async def test_process_dialogue_focus(writer_role, mock_llm_client, sample_context):
    """测试对话内容要求"""
    context = sample_context.copy()
    context["requirements"]["focus"] = ["人物对话"]
    
    mock_llm_client.generate.return_value = json.dumps({
        "content": '"你好！"艾玛说。\n"欢迎！"卢克回应。',
        "word_count": 1000,
        "scenes": [{
            "title": "对话场景",
            "content": "两人展开了热烈的交谈...",
            "dialogue": ["问候", "交流", "告别"],
            "characters": ["艾玛", "卢克"]
        }]
    })
    
    result = await writer_role.process(context)
    assert '"' in result["content"]
    assert any("dialogue" in scene for scene in result["scenes"])

@pytest.mark.asyncio
async def test_process_environment_description(writer_role, mock_llm_client, sample_context):
    """测试环境描写要求"""
    context = sample_context.copy()
    context["requirements"]["focus"] = ["环境描写"]
    
    mock_llm_client.generate.return_value = json.dumps({
        "content": "古老的城堡矗立在云端，魔法光芒环绕...",
        "word_count": 1000,
        "scenes": [{
            "title": "城堡描写",
            "content": "宏伟的建筑散发着神秘的气息...",
            "environment": "魔法城堡",
            "atmosphere": "神秘庄重"
        }]
    })
    
    result = await writer_role.process(context)
    assert "城堡" in result["content"] or "建筑" in result["content"]
    assert any("environment" in scene for scene in result["scenes"])

@pytest.mark.asyncio
async def test_process_json_error(writer_role, mock_llm_client, sample_context):
    """测试JSON解析错误"""
    # 设置无效的JSON响应
    mock_llm_client.generate.return_value = "invalid json"
    
    # 验证错误处理
    with pytest.raises(ContentParsingError):
        await writer_role.process(sample_context)

@pytest.mark.asyncio
async def test_process_fallback(writer_role, mock_llm_client, sample_context):
    """测试后备处理机制"""
    # 设置非JSON但可解析的响应
    response = """
    场景1：开场
    这是第一个场景的内容
    角色1：你好
    角色2：你也好
    情感：开心，期待
    
    场景2：结尾
    这是第二个场景的内容
    角色3：再见
    情感：不舍
    """
    mock_llm_client.generate.return_value = response
    
    # 执行处理
    result = await writer_role.process(sample_context)
    
    # 验证后备解析结果
    assert len(result["scenes"]) == 2
    assert "开场" in result["scenes"][0]["title"]
    assert "结尾" in result["scenes"][1]["title"]
    assert "角色1" in result["scenes"][0]["characters"]
    assert "不舍" in result["scenes"][1]["emotions"]

@pytest.mark.asyncio
async def test_process_empty_response(writer_role, mock_llm_client, sample_context):
    """测试空响应"""
    # 设置空响应
    mock_llm_client.generate.return_value = ""
    
    # 执行处理
    result = await writer_role.process(sample_context)
    
    # 验证默认值
    assert result["word_count"] == 0
    assert len(result["scenes"]) == 1
    assert result["scenes"][0]["title"] == "整体场景"

@pytest.mark.asyncio
async def test_process_performance(writer_role, mock_llm_client, sample_context, sample_response):
    """测试性能记录"""
    # 设置模拟响应
    mock_llm_client.generate.return_value = json.dumps(sample_response)
    
    # 执行处理并记录时间
    import time
    start_time = time.time()
    result = await writer_role.process(sample_context)
    end_time = time.time()
    
    # 验证处理时间在合理范围内
    assert end_time - start_time < Settings().generation["timeout"]

@pytest.mark.asyncio
async def test_process_content_length(writer_role, mock_llm_client, sample_context):
    """测试内容长度限制"""
    # 创建超长响应
    max_length = Settings().generation["max_content_length"]
    long_content = "x" * (max_length + 1)
    response = {
        "content": long_content,
        "word_count": len(long_content),
        "scenes": []
    }
    mock_llm_client.generate.return_value = json.dumps(response)
    
    # 验证长度检查
    with pytest.raises(ValueError):
        await writer_role.process(sample_context)
