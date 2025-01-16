import pytest
import json
from unittest.mock import Mock, patch
from story_generation.roles.critic_role import CriticRole
from story_generation.utils.error_handler import ContentParsingError
from story_generation.config.settings import Settings

@pytest.fixture
def mock_llm_client():
    return Mock()

@pytest.fixture
def critic_role(mock_llm_client):
    return CriticRole(mock_llm_client)

@pytest.fixture
def sample_content():
    return """
    阳光透过魔法学院古老的彩绘玻璃窗，在大厅的石板地面上投下斑斓的光影。艾玛站在入口处，仰望着高耸的穹顶，心中充满了期待和些许紧张。这就是她梦寐以求的魔法学院！

    "新生报到处在左边。"一个温和的声音传来。艾玛转头看去，是一位戴着圆框眼镜的男生，他的校袍上别着高年级学生的徽章。

    "谢谢！"艾玛露出灿烂的笑容，"我是艾玛，今天刚来报到。"

    "我是卢克，"男生微微点头，"作为学长，我可以带你参观一下学院。"

    艾玛惊喜地发现，原本内向的卢克在谈到魔法课程时会变得异常健谈。当他们经过图书馆时，卢克的眼睛闪闪发亮，滔滔不绝地介绍着各种魔法典籍。

    "你对魔法真的很了解呢！"艾玛由衷地赞叹道。

    卢克不好意思地推了推眼镜，"如果你有任何问题，随时都可以来找我。"

    这一刻，艾玛感觉自己不仅找到了一位向导，更找到了一位潜在的好朋友。魔法学院的生活，正在以一种美好的方式展开。
    """

@pytest.fixture
def sample_outline():
    return {
        "title": "新的开始",
        "summary": "艾玛进入魔法学院的第一天",
        "scenes": ["报到场景", "入学仪式", "相遇卢克"],
        "goals": ["介绍主角", "建立世界观"],
        "requirements": {
            "style": "轻松欢快",
            "focus": ["人物互动", "环境描写", "情感表达"]
        }
    }

@pytest.fixture
def sample_analysis():
    return {
        "overall_rating": 8,
        "analysis": {
            "plot": "情节展开自然，从报到到交友的过程流畅真实。场景转换合理，人物互动生动。",
            "characters": "主角艾玛性格鲜明，表现出了新生的期待和紧张。卢克的性格转变也很有趣，展现了人物的立体感。",
            "theme": "友情主题突出，通过初次相遇和互动，展现了友谊的萌芽。同时也体现了对新环境的适应过程。",
            "structure": "三个场景的安排合理，从报到到相识再到深入交谈，层次分明。",
            "details": "环境描写细腻，魔法学院的氛围营造到位。对话自然，情感表达真实。"
        },
        "issues": [
            {
                "type": "节奏",
                "description": "入学仪式场景略显单薄",
                "suggestion": "可以增加一些仪式感和魔法元素"
            },
            {
                "type": "人物",
                "description": "卢克的转变稍显突兀",
                "suggestion": "可以增加一些过渡的心理描写"
            }
        ],
        "highlights": [
            "环境描写生动形象",
            "对话自然流畅",
            "情感表达真挚"
        ],
        "next_steps": [
            "丰富入学仪式场景",
            "增加卢克的心理描写",
            "可以加入更多魔法元素"
        ]
    }

@pytest.mark.asyncio
async def test_analyze_story_success(critic_role, mock_llm_client, sample_content, sample_analysis):
    """测试故事分析成功"""
    mock_llm_client.generate.return_value = json.dumps(sample_analysis)
    
    result = await critic_role.analyze_story(sample_content)
    
    assert result["overall_rating"] == 8
    assert "情节" in result["analysis"]["plot"]
    assert "人物" in result["analysis"]["characters"]
    assert len(result["issues"]) > 0
    assert len(result["highlights"]) > 0
    assert len(result["next_steps"]) > 0

@pytest.mark.asyncio
async def test_analyze_story_aspects(critic_role, mock_llm_client, sample_content):
    """测试分析的各个维度"""
    aspects = {
        "plot": "故事情节分析",
        "characters": "人物塑造分析",
        "theme": "主题思想分析",
        "structure": "结构布局分析",
        "details": "细节表现分析"
    }
    
    mock_llm_client.generate.return_value = json.dumps({
        "overall_rating": 7,
        "analysis": aspects,
        "issues": []
    })
    
    result = await critic_role.analyze_story(sample_content)
    
    for aspect, content in aspects.items():
        assert aspect in result["analysis"]
        assert result["analysis"][aspect] == content

@pytest.mark.asyncio
async def test_analyze_story_rating_range(critic_role, mock_llm_client, sample_content):
    """测试评分范围限制"""
    # 测试评分过高
    mock_llm_client.generate.return_value = json.dumps({
        "overall_rating": 11,
        "analysis": {},
        "issues": []
    })
    result = await critic_role.analyze_story(sample_content)
    assert result["overall_rating"] <= 10
    
    # 测试评分过低
    mock_llm_client.generate.return_value = json.dumps({
        "overall_rating": 0,
        "analysis": {},
        "issues": []
    })
    result = await critic_role.analyze_story(sample_content)
    assert result["overall_rating"] >= 1

@pytest.mark.asyncio
async def test_analyze_story_requirements(critic_role, mock_llm_client, sample_content, sample_outline):
    """测试根据需求进行分析"""
    mock_llm_client.generate.return_value = json.dumps({
        "overall_rating": 8,
        "analysis": {
            "style_match": "符合轻松欢快的风格要求",
            "focus_analysis": {
                "人物互动": "对话生动，互动自然",
                "环境描写": "场景描写细腻",
                "情感表达": "情感真挚"
            }
        },
        "issues": []
    })
    
    context = {
        "content": sample_content,
        "requirements": sample_outline["requirements"]
    }
    
    result = await critic_role.process(context)
    
    assert "style_match" in result["analysis"]
    assert "focus_analysis" in result["analysis"]
    for focus in sample_outline["requirements"]["focus"]:
        assert focus in result["analysis"]["focus_analysis"]

@pytest.mark.asyncio
async def test_analyze_story_improvement_suggestions(critic_role, mock_llm_client, sample_content):
    """测试改进建议的质量"""
    mock_llm_client.generate.return_value = json.dumps({
        "overall_rating": 7,
        "analysis": {},
        "issues": [
            {
                "type": "描写",
                "description": "环境描写可以更丰富",
                "suggestion": "增加更多感官描写，如声音、气味等",
                "example": "可以描写魔法能量的波动，或者古老建筑散发的神秘气息"
            }
        ],
        "next_steps": [
            "在关键场景增加感官描写",
            "加入更多魔法元素",
            "深化人物心理描写"
        ]
    })
    
    result = await critic_role.analyze_story(sample_content)
    
    for issue in result["issues"]:
        assert "type" in issue
        assert "description" in issue
        assert "suggestion" in issue
        assert len(issue["suggestion"]) > 10  # 确保建议足够详细
    
    assert len(result["next_steps"]) > 0
    for step in result["next_steps"]:
        assert len(step) > 5  # 确保步骤说明清晰

@pytest.mark.asyncio
async def test_analyze_story_json_error(critic_role, mock_llm_client, sample_content):
    """测试JSON解析错误"""
    # 设置无效的JSON响应
    mock_llm_client.generate.return_value = "invalid json"
    
    # 验证错误处理
    with pytest.raises(ContentParsingError):
        await critic_role.analyze_story(sample_content)

@pytest.mark.asyncio
async def test_analyze_story_fallback(critic_role, mock_llm_client, sample_content):
    """测试后备处理机制"""
    # 设置非JSON但可解析的响应
    response = """
    评分：8
    
    情节：情节紧凑，引人入胜
    人物：人物形象鲜明
    主题：主题深刻
    结构：结构完整
    细节：细节丰富
    
    问题：
    1. 中段节奏略慢
    2. 人物动机不够清晰
    
    亮点：
    1. 开场吸引人
    2. 结尾有力
    
    建议：
    1. 优化中段节奏
    2. 加强人物刻画
    """
    mock_llm_client.generate.return_value = response
    
    # 执行分析
    result = await critic_role.analyze_story(sample_content)
    
    # 验证后备解析结果
    assert result["overall_rating"] == 8
    assert "情节紧凑" in result["analysis"]["plot"]
    assert len(result["issues"]) == 2
    assert len(result["highlights"]) == 2
    assert len(result["next_steps"]) == 2

@pytest.mark.asyncio
async def test_review_chapter_success(critic_role, mock_llm_client, sample_content, sample_outline, sample_analysis):
    """测试章节审查成功"""
    # 设置模拟响应
    mock_llm_client.generate.return_value = json.dumps(sample_analysis)
    
    # 执行审查
    result = await critic_role.review_chapter(sample_content, sample_outline)
    
    # 验证结果
    assert result["overall_rating"] == 8
    assert len(result["issues"]) == 1
    assert len(result["next_steps"]) == 2

@pytest.mark.asyncio
async def test_rating_range(critic_role, mock_llm_client, sample_content):
    """测试评分范围限制"""
    # 设置超出范围的评分
    response = """
    评分：11
    
    情节：测试内容
    """
    mock_llm_client.generate.return_value = response
    
    # 执行分析
    result = await critic_role.analyze_story(sample_content)
    
    # 验证评分被限制在有效范围内
    assert 1 <= result["overall_rating"] <= 10

@pytest.mark.asyncio
async def test_required_analysis_aspects(critic_role, mock_llm_client, sample_content):
    """测试必需的分析维度"""
    # 获取配置的分析维度
    required_aspects = Settings().get_role_config(Settings.RoleType.CRITIC)["analysis_aspects"]
    
    # 执行分析
    mock_llm_client.generate.return_value = json.dumps(sample_analysis)
    result = await critic_role.analyze_story(sample_content)
    
    # 验证所有必需的分析维度都存在
    for aspect in required_aspects:
        assert aspect in result["analysis"]
