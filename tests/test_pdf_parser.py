import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import Mock, patch
import fitz
from backend.pdf_parser import PDFParser
from backend.content_processor import Article

@pytest.fixture
def sample_pdf_path():
    """创建一个测试用的PDF文件"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # 创建一个简单的PDF文件
        doc = fitz.open()
        page = doc.new_page()
        
        # 添加一些测试文本
        page.insert_text((50, 50), "测试标题1")
        page.insert_text((50, 100), "这是第一个故事的内容。")
        page.insert_text((50, 150), "测试标题2")
        page.insert_text((50, 200), "这是第二个笑话的内容。")
        
        doc.save(tmp.name)
        doc.close()
        
        yield tmp.name
        
        # 清理临时文件
        os.unlink(tmp.name)

@pytest.fixture
def pdf_parser():
    """创建PDF解析器实例"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        parser = PDFParser(tmp_dir)
        yield parser

def test_get_pdf_files(pdf_parser, sample_pdf_path):
    """测试获取PDF文件列表功能"""
    # 复制示例PDF到解析器的目录
    target_path = Path(pdf_parser.folder_path) / "test.pdf"
    with open(sample_pdf_path, 'rb') as src, open(target_path, 'wb') as dst:
        dst.write(src.read())
    
    # 测试文件列表获取
    pdf_files = pdf_parser.get_pdf_files()
    assert len(pdf_files) == 1
    assert pdf_files[0].name == "test.pdf"

def test_parse_with_pypdf2(pdf_parser, sample_pdf_path):
    """测试PyPDF2解析方法"""
    result = pdf_parser.parse_with_pypdf2(Path(sample_pdf_path))
    
    assert result is not None
    assert isinstance(result, dict)
    assert len(result) > 0
    assert any("测试标题" in text for text in result.values())

def test_parse_with_pdfplumber(pdf_parser, sample_pdf_path):
    """测试pdfplumber解析方法"""
    result = pdf_parser.parse_with_pdfplumber(Path(sample_pdf_path))
    
    assert result is not None
    assert isinstance(result, dict)
    assert len(result) > 0
    assert any("测试标题" in text for text in result.values())

def test_parse_with_pymupdf_advanced(pdf_parser, sample_pdf_path):
    """测试PyMuPDF高级解析方法"""
    result = pdf_parser.parse_with_pymupdf_advanced(Path(sample_pdf_path))
    
    assert result is not None
    assert isinstance(result, dict)
    assert len(result) > 0
    assert any("测试标题" in text for text in result.values())

def test_parse_pdf_with_encrypted_file(pdf_parser):
    """测试处理加密PDF文件"""
    # 创建一个加密的PDF文件
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "加密文档测试")
        
        # 添加密码保护
        doc.save(tmp.name, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
        doc.close()
        
        # 测试解析
        result = pdf_parser.parse_pdf(Path(tmp.name))
        assert isinstance(result, dict)
        assert len(result) == 0  # 应该无法解析加密文件
        
        os.unlink(tmp.name)

def test_batch_process(pdf_parser, sample_pdf_path):
    """测试批量处理功能"""
    # 准备测试文件
    target_path = Path(pdf_parser.folder_path) / "test.pdf"
    with open(sample_pdf_path, 'rb') as src, open(target_path, 'wb') as dst:
        dst.write(src.read())
    
    # 创建模拟的ContentProcessor
    mock_article = Article(
        title="测试标题1",
        content="这是测试内容",
        type="story",
        tags=["测试"],
        page_numbers=[1]
    )
    
    with patch('backend.content_processor.ContentProcessor') as MockContentProcessor:
        # 配置模拟对象
        mock_processor = MockContentProcessor.return_value
        mock_processor.process_content.return_value = [mock_article]
        
        # 替换解析器的content_processor
        pdf_parser.content_processor = mock_processor
        
        # 测试批量处理
        with tempfile.TemporaryDirectory() as output_dir:
            results = pdf_parser.batch_process(output_dir)
            
            assert len(results) == 1
            assert "test.pdf" in results
            assert isinstance(results["test.pdf"], list)
            assert len(results["test.pdf"]) == 1
            assert results["test.pdf"][0].title == "测试标题1"
