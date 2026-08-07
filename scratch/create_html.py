import os
import markdown
import re

input_file = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/PIPELINE_DEPENDENCIES.md"
output_file = "C:/Users/temp/Downloads/LexMind-Omni_系統依賴地圖.html"

with open(input_file, 'r', encoding='utf-8') as f:
    md_content = f.read()

# We need to replace `mermaid block ` with <div class="mermaid"> block </div>
def replace_mermaid(match):
    code = match.group(1)
    return f'<div class="mermaid">\n{code}\n</div>'

md_content_modified = re.sub(r'`mermaid\n(.*?)`', replace_mermaid, md_content, flags=re.DOTALL)

# Convert remaining markdown to HTML
html_body = markdown.markdown(md_content_modified, extensions=['tables', 'fenced_code'])

html_template = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>LexMind-Omni 系統依賴地圖</title>
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
        blockquote {{
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
            background-color: #fffbdd;
            margin: 0;
            padding: 10px;
            border-radius: 5px;
        }}
        code {{
            background-color: #f6f8fa;
            border-radius: 3px;
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            padding: 0.2em 0.4em;
            font-size: 85%;
        }}
        .mermaid {{
            text-align: center;
            margin: 20px 0;
            background-color: #fff;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
    </style>
    <!-- Include Mermaid.js -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'default'
            }});
        }});
    </script>
</head>
<body>
    <div class="markdown-body">
        {html_body}
    </div>
</body>
</html>'''

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"Successfully generated HTML at: {output_file}")
