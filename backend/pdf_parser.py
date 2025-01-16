import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import PyPDF2
import pdfplumber
import fitz
from tqdm import tqdm
from operator import itemgetter
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from functools import partial
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from .content_processor import ContentProcessor, Article

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PDFParser:
    """PDF文档解析器类"""
    
    def __init__(self, folder_path: str, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        初始化PDF解析器
        
        Args:
            folder_path (str): PDF文件所在文件夹路径
            api_key (Optional[str]): OpenAI API密钥
            cache_dir (Optional[str]): 缓存目录路径
        """
        self.folder_path = Path(folder_path)
        self.content_processor = ContentProcessor(api_key)
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.pdf_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置marker转换器
        self.marker_converter = PdfConverter(
            artifact_dict=create_model_dict()
        )
        logger.info(f"初始化PDF解析器，文件夹路径: {folder_path}")

    def _get_cache_path(self, pdf_path: Path, page_num: int) -> Path:
        """获取缓存文件路径"""
        # 使用文件内容的hash作为缓存key
        file_hash = hashlib.md5(open(pdf_path, 'rb').read()).hexdigest()
        return self.cache_dir / f"{file_hash}_page_{page_num}.json"

    def _process_page(self, pdf_path: str, page_range: Tuple[int, int]) -> Dict[int, str]:
        """
        处理PDF的特定页面范围
        
        Args:
            pdf_path: PDF文件路径
            page_range: 页面范围元组 (start_page, end_page)
            
        Returns:
            Dict[int, str]: 页码和对应的文本内容
        """
        start_page, end_page = page_range
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
            page_numbers=list(range(start_page, end_page))  # 指定要处理的页面范围
        )
        
        try:
            rendered = converter(pdf_path)
            text, _, _ = text_from_rendered(rendered)
            
            # 分割页面文本
            pages = text.split("[PAGE]")
            result = {}
            
            for i, page_text in enumerate(pages, start_page):
                if page_text.strip():
                    result[i] = page_text.strip()
                    
            return result
            
        except Exception as e:
            logger.error(f"处理页面 {start_page}-{end_page} 失败: {str(e)}")
            return {}

    def _log_pdf_info(self, pdf_path: Path):
        """
        记录PDF文件的基本信息
        
        Args:
            pdf_path: PDF文件路径
        """
        try:
            file_size = os.path.getsize(pdf_path)
            logger.info(f"PDF文件信息:")
            logger.info(f"- 路径: {pdf_path}")
            logger.info(f"- 大小: {file_size / 1024:.2f} KB")
            logger.info(f"- 是否存在: {pdf_path.exists()}")
            logger.info(f"- 是否可读: {os.access(pdf_path, os.R_OK)}")
        except Exception as e:
            logger.error(f"获取PDF信息失败: {str(e)}")

    def get_pdf_files(self) -> List[Path]:
        """
        获取文件夹中所有的PDF文件
        
        Returns:
            List[Path]: PDF文件路径列表
        """
        logger.info("获取PDF文件列表")
        return list(self.folder_path.glob("**/*.pdf"))

    @staticmethod
    def sort_blocks(blocks: List[Dict]) -> List[Dict]:
        """
        对文本块进行排序，考虑分栏和阅读顺序
        
        Args:
            blocks: 包含文本块信息的列表
            
        Returns:
            List[Dict]: 排序后的文本块列表
        """
        logger.debug("开始排序文本块")
        # 定义一个阈值来判断是否属于同一行
        VERTICAL_TOLERANCE = 3
        
        # 按y坐标分组
        rows = {}
        for block in blocks:
            y0 = block['bbox'][1]  # 文本块的顶部y坐标
            found_row = False
            for row_y in rows.keys():
                # 如果y坐标相近，认为是同一行
                if abs(y0 - row_y) < VERTICAL_TOLERANCE:
                    rows[row_y].append(block)
                    found_row = True
                    break
            if not found_row:
                rows[y0] = [block]
        
        # 对每一行内的块按x坐标排序
        sorted_blocks = []
        for y in sorted(rows.keys()):
            row_blocks = rows[y]
            # 按x坐标排序每一行的块
            row_blocks.sort(key=lambda b: b['bbox'][0])
            sorted_blocks.extend(row_blocks)
            
        logger.debug("完成排序文本块")
        return sorted_blocks

    def parse_with_pypdf2(self, pdf_path: Path) -> Optional[Dict[int, str]]:
        """
        使用PyPDF2解析PDF文件
        
        Args:
            pdf_path (Path): PDF文件路径
            
        Returns:
            Optional[Dict[int, str]]: 页码和对应的文本内容，解析失败返回None
        """
        logger.info(f"开始使用PyPDF2解析文件: {pdf_path}")
        self._log_pdf_info(pdf_path)
        
        try:
            with open(pdf_path, 'rb') as file:
                logger.debug("成功打开PDF文件")
                pdf_reader = PyPDF2.PdfReader(file)
                logger.info(f"PDF页数: {len(pdf_reader.pages)}")
                
                if pdf_reader.is_encrypted:
                    logger.warning("PDF文件已加密")
                    return None
                
                text_content = {}
                for page_num in range(len(pdf_reader.pages)):
                    logger.debug(f"处理第 {page_num + 1} 页")
                    try:
                        text = pdf_reader.pages[page_num].extract_text()
                        if text.strip():
                            text_content[page_num + 1] = text
                            logger.debug(f"第 {page_num + 1} 页提取到文本，长度: {len(text)}")
                        else:
                            logger.warning(f"第 {page_num + 1} 页未提取到文本")
                    except Exception as e:
                        logger.error(f"处理第 {page_num + 1} 页时出错: {str(e)}")
                
                if text_content:
                    logger.info(f"成功提取 {len(text_content)} 页文本")
                    return text_content
                else:
                    logger.warning("未能提取到任何文本内容")
                    return None
                
        except Exception as e:
            logger.error(f"PyPDF2解析失败: {str(e)}")
            return None

    def parse_with_pdfplumber(self, pdf_path: Path) -> Optional[Dict[int, str]]:
        """
        使用pdfplumber解析PDF文件
        
        Args:
            pdf_path (Path): PDF文件路径
            
        Returns:
            Optional[Dict[int, str]]: 页码和对应的文本内容，解析失败返回None
        """
        logger.info(f"开始使用pdfplumber解析文件: {pdf_path}")
        self._log_pdf_info(pdf_path)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF页数: {len(pdf.pages)}")
                text_content = {}
                
                for page_num, page in enumerate(pdf.pages, 1):
                    logger.debug(f"处理第 {page_num} 页")
                    try:
                        text = page.extract_text()
                        if text.strip():
                            text_content[page_num] = text
                            logger.debug(f"第 {page_num} 页提取到文本，长度: {len(text)}")
                        else:
                            logger.warning(f"第 {page_num} 页未提取到文本")
                    except Exception as e:
                        logger.error(f"处理第 {page_num} 页时出错: {str(e)}")
                
                if text_content:
                    logger.info(f"成功提取 {len(text_content)} 页文本")
                    return text_content
                else:
                    logger.warning("未能提取到任何文本内容")
                    return None
                
        except Exception as e:
            logger.error(f"pdfplumber解析失败: {str(e)}")
            return None

    def parse_with_pymupdf_advanced(self, pdf_path: Path) -> Optional[Dict[int, str]]:
        """
        使用PyMuPDF的高级特性解析PDF文件
        
        Args:
            pdf_path (Path): PDF文件路径
            
        Returns:
            Optional[Dict[int, str]]: 页码和对应的文本内容，解析失败返回None
        """
        logger.info(f"开始使用PyMuPDF解析文件: {pdf_path}")
        self._log_pdf_info(pdf_path)
        
        try:
            doc = fitz.open(pdf_path)
            logger.info(f"PDF页数: {doc.page_count}")
            logger.info(f"PDF元数据: {doc.metadata}")
            
            text_content = {}
            for page_num in range(doc.page_count):
                logger.debug(f"处理第 {page_num + 1} 页")
                try:
                    page = doc[page_num]
                    
                    # 获取页面的文本块
                    blocks = page.get_text("dict")["blocks"]
                    logger.debug(f"第 {page_num + 1} 页找到 {len(blocks)} 个文本块")
                    
                    # 过滤掉图片块，只保留文本块
                    text_blocks = [b for b in blocks if b.get("type") == 0]
                    logger.debug(f"其中文本块数量: {len(text_blocks)}")
                    
                    if not text_blocks:
                        logger.warning(f"第 {page_num + 1} 页没有找到文本块")
                        continue
                    
                    # 对文本块进行排序
                    sorted_blocks = self.sort_blocks(text_blocks)
                    
                    # 提取并组合文本
                    page_text = []
                    for block in sorted_blocks:
                        if "lines" in block:
                            for line in block["lines"]:
                                if "spans" in line:
                                    for span in line["spans"]:
                                        if "text" in span and span["text"].strip():
                                            page_text.append(span["text"])
                    
                    # 使用适当的分隔符组合文本
                    text = " ".join(page_text)
                    if text.strip():
                        text_content[page_num + 1] = text
                        logger.debug(f"第 {page_num + 1} 页提取到文本，长度: {len(text)}")
                    else:
                        logger.warning(f"第 {page_num + 1} 页未提取到文本")
                
                except Exception as e:
                    logger.error(f"处理第 {page_num + 1} 页时出错: {str(e)}")
            
            doc.close()
            
            if text_content:
                logger.info(f"成功提取 {len(text_content)} 页文本")
                return text_content
            else:
                logger.warning("未能提取到任何文本内容")
                return None
            
        except Exception as e:
            logger.error(f"PyMuPDF解析失败: {str(e)}")
            return None

    def parse_with_marker_parallel(self, pdf_path: Path) -> Optional[Dict[int, str]]:
        """
        使用并行处理的marker库解析PDF文件
        
        Args:
            pdf_path (Path): PDF文件路径
            
        Returns:
            Optional[Dict[int, str]]: 页码和对应的文本内容，解析失败返回None
        """
        logger.info(f"开始使用并行Marker解析文件: {pdf_path}")
        self._log_pdf_info(pdf_path)
        
        try:
            # 获取PDF总页数
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            doc.close()
            
            # 检查缓存
            text_content = {}
            pages_to_process = []
            
            for page_num in range(1, total_pages + 1):
                cache_path = self._get_cache_path(pdf_path, page_num)
                if cache_path.exists():
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                        text_content[page_num] = cached_data['text']
                        logger.debug(f"使用缓存: 第 {page_num} 页")
                else:
                    pages_to_process.append(page_num)
            
            if not pages_to_process:
                logger.info("所有页面都已缓存")
                return text_content
            
            # 将页面分成批次
            cpu_count = multiprocessing.cpu_count()
            batch_size = max(1, total_pages // cpu_count)
            page_batches = []
            
            for i in range(0, len(pages_to_process), batch_size):
                batch_pages = pages_to_process[i:i + batch_size]
                page_batches.append((batch_pages[0], batch_pages[-1] + 1))
            
            # 并行处理页面
            with ProcessPoolExecutor(max_workers=cpu_count) as executor:
                future_to_batch = {
                    executor.submit(self._process_page, str(pdf_path), batch): batch
                    for batch in page_batches
                }
                
                for future in tqdm(as_completed(future_to_batch), total=len(page_batches), desc="处理页面"):
                    batch = future_to_batch[future]
                    try:
                        batch_result = future.result()
                        text_content.update(batch_result)
                        
                        # 保存到缓存
                        for page_num, text in batch_result.items():
                            cache_path = self._get_cache_path(pdf_path, page_num)
                            with open(cache_path, 'w', encoding='utf-8') as f:
                                json.dump({'text': text}, f, ensure_ascii=False)
                                
                    except Exception as e:
                        logger.error(f"处理批次 {batch} 失败: {str(e)}")
            
            if text_content:
                logger.info(f"成功提取 {len(text_content)} 页文本")
                return text_content
            else:
                logger.warning("未能提取到任何文本内容")
                return None
                
        except Exception as e:
            logger.error(f"并行Marker解析失败: {str(e)}")
            return None

    def parse_pdf(self, pdf_path: Path) -> Dict[int, str]:
        """
        使用多种方法尝试解析PDF文件
        
        Args:
            pdf_path (Path): PDF文件路径
            
        Returns:
            Dict[int, str]: 页码和对应的文本内容
        """
        logger.info(f"开始解析PDF文件: {pdf_path}")
        self._log_pdf_info(pdf_path)
        
        methods = [
            (self.parse_with_marker_parallel, "Marker Parallel"),  # 使用优化后的并行处理方法
            (self.parse_with_pymupdf_advanced, "PyMuPDF Advanced"),
            (self.parse_with_pdfplumber, "pdfplumber"),
            (self.parse_with_pypdf2, "PyPDF2")
        ]
        
        for parse_method, method_name in methods:
            logger.info(f"尝试使用 {method_name} 方法")
            result = parse_method(pdf_path)
            
            if result:
                logger.info(f"使用 {method_name} 成功解析文件")
                # 输出一些解析结果的示例
                for page_num in list(result.keys())[:1]:
                    text = result[page_num]
                    logger.debug(f"第 {page_num} 页内容示例: {text[:200]}...")
                return result
            else:
                logger.warning(f"{method_name} 解析失败，尝试下一个方法")
        
        logger.error(f"所有方法都无法解析文件 {pdf_path}")
        return {}

    def batch_process(self, output_dir: Optional[str] = None) -> Dict[str, List[Article]]:
        """
        批量处理文件夹中的所有PDF文件
        
        Args:
            output_dir: 可选的输出目录路径，如果提供则保存处理结果
            
        Returns:
            Dict[str, List[Article]]: 文件名和对应的文章列表
        """
        logger.info("开始批量处理PDF文件")
        results = {}
        pdf_files = self.get_pdf_files()
        
        for pdf_file in tqdm(pdf_files, desc="Processing PDF files"):
            # 解析PDF内容
            raw_content = self.parse_pdf(pdf_file)
            
            # 处理提取的内容
            articles = self.content_processor.process_content(raw_content)
            results[pdf_file.name] = articles
            
            # 如果提供了输出目录，保存处理结果
            if output_dir:
                pdf_output_dir = Path(output_dir) / pdf_file.stem
                self.content_processor.save_articles(articles, pdf_output_dir)
            
        logger.info("完成批量处理PDF文件")
        return results
