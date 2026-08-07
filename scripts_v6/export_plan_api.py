# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 7: 系統圖表與報告匯出 (Export & Visualization)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 7】。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import sys
import subprocess

try:
    import markdown
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'markdown'], check=True)
    import markdown

try:
    import requests
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'], check=True)
    import requests

import re
import os
import base64

input_file = r'C:\Users\temp\.gemini\antigravity\brain\8a6d8f31-3707-47f6-a39f-c53d88749feb\implementation_plan.md'
html_file = r'C:\Users\temp\Downloads\LexMind-Omni_Implementation_Plan.html'

with open(input_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Extract mermaid blocks
def mermaid_to_img(match):
    code = match.group(1).strip()
    
    # We must use base64 urlsafe encoding for mermaid.ink
    # Note: For mermaid.ink, the state can be passed as base64 string
    # A safer way for mermaid API is using string encoding
    b64 = base64.urlsafe_b64encode(code.encode('utf-8')).decode('utf-8')
    url = f"https://mermaid.ink/img/{b64}"
    
    print("Fetching diagram from:", url)
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img_b64 = base64.b64encode(response.content).decode('utf-8')
        print("Diagram fetched successfully!")
        return f'<img src="data:image/png;base64,{img_b64}" alt="System Architecture Visual" style="max-width: 100%; border: 1px solid #ddd; padding: 10px; background: white;" />'
    except Exception as e:
        print("Failed to fetch image:", e)
        # fallback to regular url
        return f'<img src="{url}" alt="System Architecture Visual" style="max-width: 100%; border: 1px solid #ddd; padding: 10px; background: white;" />'

text_for_html = re.sub(r'```mermaid\n(.*?)\n```', mermaid_to_img, text, flags=re.DOTALL)

html_body = markdown.markdown(text_for_html, extensions=['tables', 'fenced_code'])

html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>LexMind-Omni 系統分析與修復計畫</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 40px; color: #333; background: #fff; }}
        h1, h2, h3 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 4px; font-family: Consolas, monospace; }}
        pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; border: 1px solid #ddd; }}
        blockquote {{ border-left: 4px solid #0366d6; padding-left: 15px; color: #6a737d; background: #f1f8ff; padding: 10px; margin-left: 0; }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""

with open(html_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print("HTML with embedded static PNG saved to:", html_file)

