import json
from typing import List, Dict, Optional
from dataclasses import dataclass
import openai
import os
from pathlib import Path

@dataclass
class Article:
    """文章数据类"""
    title: str
    content: str
    type: str  # 'story' | 'joke' | 'other'
    tags: List[str]
    page_numbers: List[int]

class ContentProcessor:
    """内容处理器类，用于处理和分类文章内容"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化内容处理器
        
        Args:
            api_key: OpenAI API密钥，如果不提供则从环境变量获取
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供OpenAI API密钥")
        openai.api_key = self.api_key

    def _split_text(self, text_blocks: List[str], max_chars: int = 12000, overlap_block_size: int = 2) -> List[List[str]]:
        """
        将文本块列表分割成更小的块组，基于字符数限制来合并，基于块数来处理重叠
        
        Args:
            text_blocks: 文本块列表，每个元素可能是段落、行或页面
            max_chars: 每组文本的最大字符数限制
            overlap_block_size: 相邻组之间重叠的文本块数量
            
        Returns:
            List[List[str]]: 分组后的文本块列表，每组是一个文本块列表
        """
        if not text_blocks:
            return []
            
        chunks = []
        current_chunk = []
        current_length = 0
        
        def get_blocks_length(blocks: List[str]) -> int:
            """计算文本块列表的总字符数"""
            return sum(len(block) for block in blocks)
        
        def should_split_chunk(length: int, next_block_length: int) -> bool:
            """判断是否应该分割当前chunk"""
            return length + next_block_length > max_chars
        
        def debug_print(msg: str, length: int = None):
            """输出调试信息"""
            if length is not None:
                print(f"{msg} (current_length: {length}, max_chars: {max_chars})")
            else:
                print(msg)
            
        i = 0
        while i < len(text_blocks):
            block = text_blocks[i]
            block_length = len(block)
            
            # 处理超大块：如果单个块就超过最大限制
            if block_length > max_chars:
                debug_print(f"发现超大块: 长度 {block_length}", current_length)
                # 如果当前chunk不为空，先保存
                if current_chunk:
                    chunks.append(current_chunk)
                # 将大块单独作为一个chunk
                chunks.append([block])
                current_chunk = []
                current_length = 0
                i += 1
                continue
            
            # 检查添加当前块是否会超出限制
            if should_split_chunk(current_length, block_length):
                debug_print(f"当前块会导致超出限制: 块长度 {block_length}", current_length)
                # 保存当前chunk
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 从上一个chunk的最后overlap_block_size个块开始新的chunk
                if chunks and overlap_block_size > 0:
                    # 计算重叠块的总长度
                    last_chunk = chunks[-1]
                    overlap_start_idx = max(0, len(last_chunk) - overlap_block_size)
                    overlap_blocks = last_chunk[overlap_start_idx:]
                    overlap_length = get_blocks_length(overlap_blocks)
                    
                    # 如果重叠块的长度已经接近或超过限制，减少重叠块数量
                    while overlap_blocks and overlap_length > max_chars * 0.5:  # 使用50%作为安全阈值
                        overlap_blocks.pop(0)
                        overlap_length = get_blocks_length(overlap_blocks)
                    
                    debug_print(f"添加重叠块: {len(overlap_blocks)}个块, 长度 {overlap_length}")
                    current_chunk = overlap_blocks.copy()
                    current_length = overlap_length
                else:
                    current_chunk = []
                    current_length = 0
            
            # 添加当前块到chunk
            current_chunk.append(block)
            current_length += block_length
            debug_print(f"添加块 {i+1}/{len(text_blocks)}: 长度 {block_length}", current_length)
            i += 1
        
        # 处理最后剩余的块
        if current_chunk:
            chunks.append(current_chunk)
        
        # 输出每个chunk的统计信息和验证
        print("\n=== Chunks 统计信息 ===")
        for j, chunk in enumerate(chunks):
            total_chars = get_blocks_length(chunk)
            overlap_info = ""
            if j > 0 and overlap_block_size > 0:
                # 检查与前一个chunk的重叠情况
                prev_chunk = chunks[j-1]
                prev_end = prev_chunk[-min(overlap_block_size, len(prev_chunk)):]
                curr_start = chunk[:min(overlap_block_size, len(chunk))]
                if prev_end == curr_start:
                    overlap_info = f", 与前一个chunk重叠 {len(prev_end)} 个块"
            
            # 验证chunk大小
            if total_chars > max_chars:
                print(f"警告: Chunk {j+1} 超出大小限制: {total_chars} > {max_chars}")
            
            print(f"Chunk {j+1}: {len(chunk)} 个块, {total_chars} 字符{overlap_info}")
        
        return chunks

    def _extract_articles(self, text_blocks: List[str]) -> List[Dict]:
        """
        使用GPT模型识别和提取文章
        
        Args:
            text_blocks: 文本块列表，每个元素可能是段落、行或页面
            
        Returns:
            List[Dict]: 提取出的故事类文章列表
        """
        # 分割文本块
        chunks = self._split_text(text_blocks)
        all_articles = []
        
        for i, chunk in enumerate(chunks):
            # 将文本块列表转换为带编号的文本
            numbered_text = "\n".join(f"[Block {j+1}] {block}" for j, block in enumerate(chunk))
            
            prompt = f"""
            请分析以下编号文本块，这些文本块来自PDF文档，可能是段落、单行文本或整页内容。
            请仔细分析这些文本块之间的关系，将相关的块组合成完整的故事。

            1. 识别内容类型，可能的类型包括：
               - story: 故事（包括小说、童话、寓言等叙事性内容）
               - news: 新闻报道
               - ad: 广告
               - notice: 通知、公告、寻人启事等
               - joke: 笑话、段子
               - other: 其他类型
            
            2. 对于故事类型的内容：
               - 分析文本块之间的连续性和关联性
               - 将相关的文本块组合成完整的故事
               - 提供合适的标题
               - 提取关键词标签（如：悬疑、励志、童话等）
               - 确保故事的完整性
               - 标注故事的主题和情感基调
            
            3. 严格的过滤标准：
               - 只保留确定是故事类型的内容
               - 故事必须有完整的情节发展
               - 排除新闻报道、广告、通知等非故事内容
               - 排除不完整或片段的故事
               - 排除低质量或无意义的内容
            
            这是第 {i+1}/{len(chunks)} 组文本块，{'如果故事不完整，请标注待续' if i < len(chunks)-1 else '这是最后一组'}。
            
            在返回的内容中，请标注使用了哪些文本块来构建故事（使用块编号）。

            请以JSON格式返回结果，格式如下：
            [
                {{
                    "title": "故事标题",
                    "content": "故事内容",
                    "type": "story",
                    "tags": ["标签1", "标签2"],
                    "theme": "故事主题",
                    "tone": "情感基调",
                    "complete": true/false,
                    "quality_score": 0-10,  # 内容质量评分
                    "used_blocks": [1, 2, 4]  # 使用的文本块编号
                }},
                ...
            ]

            只返回类型为"story"且quality_score >= 7的内容。

            待分析文本：
            {numbered_text}
            """

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4-32k",
                    messages=[
                        {"role": "system", "content": "你是一个专业的故事分析助手，擅长从PDF提取的文本块中识别和重构完整的故事。你能够理解文本块之间的关系，并将相关的块组合成连贯的故事。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4000
                )
                
                chunk_articles = json.loads(response.choices[0].message.content)
                
                # 过滤非故事内容和低质量内容
                chunk_articles = [
                    article for article in chunk_articles 
                    if article.get('type') == 'story' 
                    and article.get('quality_score', 0) >= 7
                ]
                
                # 处理分块的故事
                if i > 0 and chunk_articles and all_articles:
                    # 如果前一个块的最后一篇故事未完成，与当前块的第一篇合并
                    if not all_articles[-1].get('complete', True):
                        if chunk_articles:
                            all_articles[-1]['content'] += '\n' + chunk_articles[0]['content']
                            all_articles[-1]['complete'] = chunk_articles[0].get('complete', True)
                            # 合并标签和使用的块编号
                            all_articles[-1]['tags'] = list(set(all_articles[-1]['tags'] + chunk_articles[0]['tags']))
                            all_articles[-1]['used_blocks'].extend(chunk_articles[0].get('used_blocks', []))
                            chunk_articles = chunk_articles[1:]
                
                all_articles.extend(chunk_articles)
                
            except Exception as e:
                print(f"处理第 {i+1} 组文本块时发生错误: {str(e)}")
                continue
            
        # 清理中间状态标记和质量评分
        for article in all_articles:
            article.pop('complete', None)
            article.pop('quality_score', None)
            article.pop('used_blocks', None)
            
        return all_articles

    def _merge_continuous_content(self, pages_content: Dict[int, str]) -> List[Dict]:
        """
        合并跨页的内容
        
        Args:
            pages_content: 页码和对应的内容字典
            
        Returns:
            List[Dict]: 合并后的内容列表，包含页码信息
        """
        merged_contents = []
        current_content = []
        current_pages = []
        
        for page_num in sorted(pages_content.keys()):
            lines = pages_content[page_num].split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 如果遇到疑似标题的行，且当前已有内容，则保存当前内容
                if self._is_title_line(line) and current_content:
                    merged_contents.append({
                        'content': '\n'.join(current_content),
                        'pages': current_pages
                    })
                    current_content = []
                    current_pages = []
                
                current_content.append(line)
                if page_num not in current_pages:
                    current_pages.append(page_num)
        
        # 添加最后一段内容
        if current_content:
            merged_contents.append({
                'content': '\n'.join(current_content),
                'pages': current_pages
            })
            
        return merged_contents

    def process_content(self, pages_content: Dict[int, str]) -> List[Article]:
        """
        处理PDF内容，提取和分类文章
        
        Args:
            pages_content: 页码和对应的内容字典
            
        Returns:
            List[Article]: 处理后的文章列表
        """
        # 首先合并跨页的内容
        merged_contents = self._merge_continuous_content(pages_content)
        
        articles = []
        # 分批处理合并后的内容，避免超出API限制
        batch_size = 5
        
        for i in range(0, len(merged_contents), batch_size):
            batch = merged_contents[i:i + batch_size]
            batch_text = "\n===文章分隔线===\n".join(item['content'] for item in batch)
            
            # 使用GPT处理这批内容
            processed_articles = self._extract_articles([batch_text])
            
            # 添加页码信息并创建Article对象
            for j, article_dict in enumerate(processed_articles):
                article = Article(
                    title=article_dict['title'],
                    content=article_dict['content'],
                    type=article_dict['type'],
                    tags=article_dict['tags'],
                    page_numbers=batch[j]['pages']
                )
                articles.append(article)
        
        return articles

    def save_articles(self, articles: List[Article], output_dir: str):
        """
        将文章保存到指定目录
        
        Args:
            articles: 文章列表
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 按类型分类保存
        for article in articles:
            type_dir = output_path / article.type
            type_dir.mkdir(exist_ok=True)
            
            # 创建安全的文件名
            safe_title = "".join(c for c in article.title if c.isalnum() or c in (' ', '-', '_')).strip()
            file_path = type_dir / f"{safe_title}.json"
            
            # 保存为JSON格式
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': article.title,
                    'content': article.content,
                    'type': article.type,
                    'tags': article.tags,
                    'page_numbers': article.page_numbers
                }, f, ensure_ascii=False, indent=2)

    def _is_title_line(self, text: str) -> bool:
        """
        判断一行文本是否可能是标题
        
        Args:
            text: 待判断的文本行
            
        Returns:
            bool: 是否是标题
        """
        # 标题通常较短且不以常见的连接词开始
        if len(text) > 30 or len(text) < 2:
            return False
            
        # 标题通常不会以特定字符开始
        invalid_starts = ['，', '。', '、', '：', '；', '"', "'", '（']
        if any(text.startswith(char) for char in invalid_starts):
            return False
            
        return True
