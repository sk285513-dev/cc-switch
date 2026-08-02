import markdown
import sys
import os

input_file = r'C:\LocalAI_Workstation\Formatted.md'
output_file = r'C:\LocalAI_Workstation\LexMind_Omni_計畫書_正式版.html'

if not os.path.exists(input_file):
    print(f"Error: {input_file} does not exist.")
    sys.exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    text = f.read()

html_content = markdown.markdown(text, extensions=['extra', 'tables', 'toc'])

full_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LexMind Omni 計畫書</title>
<style>
    body {{
        font-family: 'Segoe UI', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
        line-height: 1.6;
        margin: 2em auto;
        max-width: 900px;
        padding: 0 1.5em;
        color: #333;
        background-color: #fcfcfc;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: #2c3e50;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }}
    h1 {{
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.3em;
        text-align: center;
    }}
    h2 {{
        border-bottom: 1px solid #eee;
        padding-bottom: 0.3em;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 1.5em 0;
        font-size: 0.95em;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    th, td {{
        border: 1px solid #ddd;
        padding: 12px 15px;
        text-align: left;
    }}
    th {{
        background-color: #f4f6f8;
        color: #333;
        font-weight: 600;
    }}
    tr:nth-child(even) {{
        background-color: #f9f9f9;
    }}
    pre {{
        background-color: #f8f9fa;
        padding: 1.2em;
        overflow-x: auto;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        font-size: 0.9em;
    }}
    code {{
        font-family: 'Consolas', 'Courier New', monospace;
        background-color: #f1f3f5;
        padding: 0.2em 0.4em;
        border-radius: 3px;
        color: #d63384;
    }}
    pre code {{
        background-color: transparent;
        padding: 0;
        color: inherit;
    }}
    blockquote {{
        margin: 1.5em 0;
        padding: 0.5em 1.5em;
        border-left: 5px solid #3498db;
        background-color: #f8f9fa;
        color: #555;
    }}
    a {{
        color: #3498db;
        text-decoration: none;
    }}
    a:hover {{
        text-decoration: underline;
    }}
    ul, ol {{
        padding-left: 2em;
    }}
    li {{
        margin-bottom: 0.5em;
    }}
</style>
</head>
<body>
{html_content}
</body>
</html>
"""

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(full_html)

print("HTML generated successfully.")
