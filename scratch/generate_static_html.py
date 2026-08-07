import os
import re
import base64
import urllib.request
import zlib
import markdown

input_file = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/PIPELINE_DEPENDENCIES.md"
output_file = "C:/Users/temp/Downloads/LexMind-Omni_系統依賴地圖.html"

with open(input_file, 'r', encoding='utf-8') as f:
    md_content = f.read()

def process_mermaid_block(match):
    mermaid_code = match.group(1).strip()
    
    # Kroki Base64 encoding
    data = mermaid_code.encode('utf-8')
    compressed = zlib.compress(data, 9)
    b64_code = base64.urlsafe_b64encode(compressed).decode('utf-8')
    url = f"https://kroki.io/mermaid/png/{b64_code}"
    
    try:
        print(f"Fetching from {url}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            img_data = response.read()
            img_b64 = base64.b64encode(img_data).decode('utf-8')
            return f'<img src="data:image/png;base64,{img_b64}" alt="Mermaid Diagram" style="max-width: 100%; height: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">'
    except Exception as e:
        print(f"Error fetching mermaid image: {e}")
        return f'<pre><code>{mermaid_code}</code></pre>'

md_content_modified = re.sub(r'`mermaid\n(.*?)`', process_mermaid_block, md_content, flags=re.DOTALL)

html_body = markdown.markdown(md_content_modified, extensions=['tables', 'fenced_code'])

html_template = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>LexMind-Omni 系統依賴地圖 (靜態圖表版)</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .markdown-body {{
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
            margin-top: 24px;
            margin-bottom: 16px;
        }}
        img {{
            display: block;
            margin: 20px auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            background-color: #fff;
        }}
        blockquote {{
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
            background-color: #fffbdd;
            margin: 0;
            padding: 10px;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="markdown-body">
        {html_body}
    </div>
</body>
</html>'''

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"Successfully generated Static HTML at: {output_file}")
