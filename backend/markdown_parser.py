import os
from pathlib import Path
from typing import List, Optional
import logging
from .content_processor import Article

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MarkdownParser:
    """Markdown文档解析器类"""
    
    def __init__(self, folder_path: str):
        """
        初始化Markdown解析器
        
        Args:
            folder_path (str): Markdown文件所在文件夹路径
        """
        self.folder_path = Path(folder_path)
        logger.info(f"初始化Markdown解析器，文件夹路径: {folder_path}")

    def read_markdown_file(self, file_path: Path) -> str:
        """
        读取Markdown文件内容
        
        Args:
            file_path (Path): Markdown文件路径
            
        Returns:
            str: 文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件 {file_path} 失败: {str(e)}")
            return ""

    def process_file(self, file_path: Path) -> Article:
        """
        处理单个Markdown文件
        
        Args:
            file_path (Path): Markdown文件路径
            
        Returns:
            Article: 提取的文章
        """
        logger.info(f"开始处理文件: {file_path}")
        content = self.read_markdown_file(file_path)
        if not content:
            return None
            
        try:
            # 使用文件名作为标题
            title = file_path.stem
            
            article = Article(
                title=title,
                content=content,
                type='story',  # 默认类型为story
                tags=[],  # 空标签列表
                page_numbers=[1]  # Markdown文件默认为单页
            )
            
            logger.info(f"成功读取文件 {file_path}")
            return article
            
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生错误: {str(e)}")
            return None

    def process_folder(self) -> List[Article]:
        """
        处理文件夹中的所有Markdown文件
        
        Returns:
            List[Article]: 所有提取的文章列表
        """
        all_articles = []
        markdown_files = list(self.folder_path.glob("**/*.md"))
        
        logger.info(f"找到 {len(markdown_files)} 个Markdown文件")
        
        for file_path in markdown_files:
            article = self.process_file(file_path)
            if article:
                all_articles.append(article)
        
        logger.info(f"总共读取了 {len(all_articles)} 篇文章")
        return all_articles
