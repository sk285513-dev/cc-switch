import sys
import os
import re
import base64
import time
from playwright.sync_api import sync_playwright
import markdown

input_file = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/PIPELINE_DEPENDENCIES.md"
html_file = "C:/Users/temp/Downloads/LexMind-Omni_系統依賴地圖.html"

with open(input_file, 'r', encoding='utf-8') as f:
    text = f.read()

mermaid_blocks = re.findall(r'`mermaid\n(.*?)\n`', text, flags=re.DOTALL)
img_tags = []

print(f"Found {len(mermaid_blocks)} Mermaid blocks.")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Page Error: {err.message}"))
    
    for i, code in enumerate(mermaid_blocks):
        temp_html = f"C:/Users/temp/Downloads/temp_mermaid_{i}.html"
        png_path = f"C:/Users/temp/Downloads/temp_mermaid_{i}.png"
        
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(f'''<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
        }});
    </script>
</head>
<body>
    <div class="mermaid" id="diagram">{code}</div>
</body>
</html>''')
        
        print(f"Rendering block {i+1}...")
        page.goto(f"file:///{temp_html}")
        try:
            svg_element = page.wait_for_selector('svg', timeout=10000)
            time.sleep(1)
            svg_element.screenshot(path=png_path, omit_background=True)
            
            with open(png_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            img_tag = f'\n\n<img src="data:image/png;base64,{encoded_string}" alt="Mermaid Chart {i+1}" style="max-width: 100%; height: auto; border: 1px solid #ddd; padding: 10px; background: white; margin: 20px auto; display: block;" />\n\n'
            img_tags.append(img_tag)
        except Exception as e:
            print(f"Failed to render block {i+1}: {e}")
            img_tags.append(f'<pre><code>{code}</code></pre>')
        
        if os.path.exists(temp_html): os.remove(temp_html)
        if os.path.exists(png_path): os.remove(png_path)
        
    browser.close()

for img_tag in img_tags:
    text = re.sub(r'`mermaid\n.*?\n`', img_tag, text, count=1, flags=re.DOTALL)

print("Converting to HTML...")
html_body = markdown.markdown(text, extensions=['tables', 'fenced_code'])
html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>LexMind-Omni 系統全域依賴關係與防呆地圖</title>
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
'''
with open(html_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"HTML generated successfully: {html_file}")
