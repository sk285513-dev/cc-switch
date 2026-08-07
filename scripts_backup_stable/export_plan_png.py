import sys
import subprocess

try:
    import markdown
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'markdown'], check=True)
    import markdown

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    from playwright.sync_api import sync_playwright

import re
import os
import base64
import time

input_file = r'C:\Users\temp\.gemini\antigravity\brain\8a6d8f31-3707-47f6-a39f-c53d88749feb\implementation_plan.md'
html_file = r'C:\Users\temp\Downloads\LexMind-Omni_Implementation_Plan_Static.html'
png_file = r'C:\Users\temp\Downloads\LexMind-Omni_Architecture.png'

with open(input_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Extract mermaid block
mermaid_match = re.search(r'```mermaid\n(.*?)\n```', text, flags=re.DOTALL)
mermaid_code = mermaid_match.group(1) if mermaid_match else ""

# Create a temporary HTML file to render the mermaid diagram
temp_mermaid_html = r'C:\Users\temp\Downloads\temp_mermaid.html'
with open(temp_mermaid_html, 'w', encoding='utf-8') as f:
    f.write(f"""<!DOCTYPE html>
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
    <div class="mermaid" id="diagram">
{mermaid_code}
    </div>
</body>
</html>
""")

print("Rendering Mermaid to PNG using Playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f'file:///{temp_mermaid_html.replace(chr(92), "/")}')
    # Wait for the SVG to be generated
    svg_element = page.wait_for_selector('svg[aria-roledescription="mermaid"]', timeout=10000)
    # Give it a tiny bit of time to finish rendering text
    time.sleep(1)
    svg_element.screenshot(path=png_file, omit_background=True)
    browser.close()

# Clean up temp html
if os.path.exists(temp_mermaid_html):
    os.remove(temp_mermaid_html)

print("PNG saved to:", png_file)

# Encode PNG to base64
with open(png_file, "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

img_tag = f'<img src="data:image/png;base64,{encoded_string}" alt="System Architecture Visual" style="max-width: 100%; height: auto; border: 1px solid #ddd; padding: 10px; background: white;" />'

# Replace mermaid block in markdown text with the img tag (for the HTML generation)
text_for_html = re.sub(r'```mermaid\n.*?\n```', img_tag, text, flags=re.DOTALL)

# Convert to HTML
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
