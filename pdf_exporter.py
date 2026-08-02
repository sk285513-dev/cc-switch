import os
import markdown
from playwright.sync_api import sync_playwright

# LexMind-Omni 專屬講義 CSS 樣式
CSS_TEMPLATE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');
    
    body {
        font-family: 'Microsoft JhengHei', 'PingFang TC', 'Noto Sans TC', sans-serif;
        line-height: 1.6;
        color: #333333;
        margin: 0;
        padding: 0;
        background-color: #ffffff;
    }
    
    h1 {
        color: #1a365d;
        border-bottom: 2px solid #2b6cb0;
        padding-bottom: 10px;
        font-size: 24pt;
        margin-top: 0;
    }
    
    h2 {
        color: #2b6cb0;
        font-size: 18pt;
        margin-top: 30px;
    }
    
    h3 {
        color: #2c5282;
        font-size: 14pt;
    }
    
    p {
        font-size: 12pt;
        margin-bottom: 15px;
        text-align: justify;
    }
    
    strong {
        color: #c53030;
        font-weight: 700;
    }
    
    ul, ol {
        font-size: 12pt;
        margin-bottom: 15px;
        padding-left: 30px;
    }
    
    li {
        margin-bottom: 5px;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        font-size: 11pt;
    }
    
    th, td {
        border: 1px solid #cbd5e0;
        padding: 12px;
        text-align: left;
    }
    
    th {
        background-color: #edf2f7;
        color: #2d3748;
        font-weight: bold;
    }
    
    tr:nth-child(even) {
        background-color: #f7fafc;
    }
    
    blockquote {
        border-left: 4px solid #4299e1;
        padding-left: 15px;
        color: #4a5568;
        background-color: #ebf8ff;
        padding: 10px 15px;
        margin: 20px 0;
        border-radius: 0 4px 4px 0;
    }
    
    code {
        font-family: 'Consolas', 'Courier New', monospace;
        background-color: #f1f5f9;
        padding: 2px 5px;
        border-radius: 3px;
        font-size: 11pt;
    }
    
    pre code {
        display: block;
        padding: 15px;
        overflow-x: auto;
        background-color: #1e293b;
        color: #f8fafc;
        border-radius: 5px;
    }
    
    .page-break {
        page-break-after: always;
    }
</style>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    {css}
</head>
<body>
    {content}
</body>
</html>
"""

def markdown_to_pdf_bytes(md_text: str) -> bytes:
    """
    將 Markdown 文字轉換為排版精美的 PDF 位元組流。
    使用 Playwright 驅動無頭瀏覽器，完美保留 HTML/CSS 樣式與表格。
    """
    # 轉換 Markdown 為 HTML (啟用表格與各種延伸語法)
    html_content = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'nl2br'])
    
    # 組合完整的 HTML 檔
    full_html = HTML_TEMPLATE.format(css=CSS_TEMPLATE, content=html_content)
    
    pdf_bytes = b""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(full_html, wait_until="networkidle")
            
            # 產生 PDF
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"},
                display_header_footer=True,
                header_template="<span></span>",
                footer_template="""
                    <div style='font-size: 9px; text-align: center; width: 100%; color: #718096; font-family: sans-serif;'>
                        LexMind-Omni 法律實務工作站 自動生成 - 頁次 <span class='pageNumber'></span> / <span class='totalPages'></span>
                    </div>
                """
            )
            browser.close()
    except Exception as e:
        print(f"PDF 渲染失敗: {e}")
        # 若 Playwright 失效，拋出錯誤
        raise RuntimeError(f"Playwright PDF 渲染失敗: {e}")
        
    return pdf_bytes
