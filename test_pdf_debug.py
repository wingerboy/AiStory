import logging
from pathlib import Path
from backend.pdf_parser import PDFParser

def test_single_pdf(pdf_path: str):
    """
    测试单个PDF文件的解析
    
    Args:
        pdf_path: PDF文件的路径
    """
    # 获取PDF文件所在的目录
    pdf_file = Path(pdf_path)
    folder_path = pdf_file.parent
    
    # 创建解析器
    parser = PDFParser(str(folder_path))
    
    # 测试每种解析方法
    methods = [
        (parser.parse_with_pymupdf_advanced, "PyMuPDF Advanced"),
        (parser.parse_with_pdfplumber, "pdfplumber"),
        (parser.parse_with_pypdf2, "PyPDF2")
    ]
    
    print("\n" + "="*50)
    print(f"测试PDF文件: {pdf_file.name}")
    print("="*50)
    
    for method, name in methods:
        print(f"\n正在测试 {name} 方法...")
        result = method(pdf_file)
        
        if result:
            print(f"✓ {name} 成功解析文件")
            print(f"- 提取到 {len(result)} 页文本")
            # 显示第一页的部分内容作为示例
            first_page = min(result.keys())
            text_sample = result[first_page][:200]
            print(f"- 第 {first_page} 页内容示例:\n{text_sample}...")
        else:
            print(f"✗ {name} 解析失败")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 在这里输入要测试的PDF文件路径
    pdf_path = input("请输入要测试的PDF文件的完整路径: ").strip()
    
    if not Path(pdf_path).exists():
        print("错误：文件不存在！")
    else:
        test_single_pdf(pdf_path)
