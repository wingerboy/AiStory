import gradio as gr
import sys
import os
from pathlib import Path
from typing import Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pdf_parser import PDFParser
from backend.content_processor import Article

def process_folder(folder_path: str, api_key: str, output_dir: str) -> Dict[str, str]:
    """
    处理文件夹中的PDF文件
    
    Args:
        folder_path: 文件夹路径
        api_key: OpenAI API密钥
        output_dir: 输出目录路径
        
    Returns:
        Dict[str, str]: 处理结果的摘要信息
    """
    if not os.path.exists(folder_path):
        return {"error": "错误：文件夹不存在！"}
        
    if not api_key:
        return {"error": "错误：需要提供OpenAI API密钥！"}
        
    try:
        parser = PDFParser(folder_path, api_key)
        results = parser.batch_process(output_dir)
        
        # 生成摘要报告
        summary = {}
        
        for filename, articles in results.items():
            # 按类型统计文章
            type_count = {}
            for article in articles:
                type_count[article.type] = type_count.get(article.type, 0) + 1
            
            # 生成文件摘要
            file_summary = [f"文件：{filename}"]
            file_summary.append(f"共提取 {len(articles)} 篇文章：")
            for article_type, count in type_count.items():
                file_summary.append(f"- {article_type}: {count} 篇")
            
            # 添加部分文章标题预览
            file_summary.append("\n文章预览：")
            for article in articles[:5]:  # 只显示前5篇
                file_summary.append(f"- [{article.type}] {article.title}")
            
            summary[filename] = "\n".join(file_summary)
        
        return summary
        
    except Exception as e:
        return {"error": f"处理过程中出错：{str(e)}"}

# 创建Gradio界面
with gr.Blocks(title="故事会PDF解析系统") as demo:
    gr.Markdown("# 故事会PDF解析系统")
    gr.Markdown("本系统可以自动识别和分类故事会PDF中的不同类型文章，包括故事、笑话等。")
    
    with gr.Row():
        with gr.Column():
            folder_input = gr.Textbox(
                label="PDF文件夹路径",
                placeholder="请输入包含PDF文件的文件夹路径"
            )
            api_key_input = gr.Textbox(
                label="OpenAI API密钥",
                placeholder="请输入你的OpenAI API密钥",
                type="password"
            )
            output_dir_input = gr.Textbox(
                label="输出目录路径",
                placeholder="请输入处理结果的保存路径"
            )
            process_btn = gr.Button("开始处理")
        
        with gr.Column():
            output_json = gr.JSON(
                label="处理结果",
                show_label=True
            )
    
    process_btn.click(
        fn=process_folder,
        inputs=[folder_input, api_key_input, output_dir_input],
        outputs=[output_json]
    )
    
    gr.Markdown("""
    ## 使用说明
    1. 输入包含PDF文件的文件夹路径
    2. 提供OpenAI API密钥（用于内容识别和分类）
    3. 指定输出目录，用于保存处理后的文章
    4. 点击"开始处理"按钮
    
    ## 功能特点
    - 自动识别文章类型（故事、笑话等）
    - 提取文章标题和内容
    - 生成文章标签
    - 保持文章完整性
    - 支持批量处理
    """)

if __name__ == "__main__":
    demo.launch(share=False)
