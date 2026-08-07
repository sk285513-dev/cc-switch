import sys
import subprocess

try:
    import markdown
except ImportError:
    print('Installing markdown...')
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'markdown'], check=True)
    import markdown

import re
import os

input_file = r'C:\Users\temp\.gemini\antigravity\brain\8a6d8f31-3707-47f6-a39f-c53d88749feb\implementation_plan.md'
html_file = r'C:\Users\temp\Downloads\LexMind-Omni_Implementation_Plan.html'
pdf_file = r'C:\Users\temp\Downloads\LexMind-Omni_Implementation_Plan.pdf'

with open(input_file, 'r', encoding='utf-8') as f:
    text = f.read()

def mermaid_replacer(match):
    return '<div class="mermaid">\n' + match.group(1) + '\n</div>'

text = re.sub(r'```mermaid\n(.*?)\n```', mermaid_replacer, text, flags=re.DOTALL)

html_body = markdown.markdown(text, extensions=['tables', 'fenced_code'])

html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>LexMind-Omni 系統分析與修復計畫</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 4px; font-family: Consolas, monospace; }}
        pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; border: 1px solid #ddd; }}
        .mermaid {{ margin: 20px 0; display: flex; justify-content: center; }}
        blockquote {{ border-left: 4px solid #0366d6; padding-left: 15px; color: #6a737d; background: #f1f8ff; padding: 10px; margin-left: 0; }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
        }});
    </script>
</head>
<body>
    {html_body}
</body>
</html>
"""

with open(html_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f'HTML saved to: {html_file}')

# Convert to PDF using playwright
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('Installing playwright...')
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    from playwright.sync_api import sync_playwright

print('Generating PDF with Playwright...')
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f'file:///{html_file.replace(chr(92), "/")}')
    # Wait for mermaid svgs to render
    try:
        page.wait_for_selector('svg[aria-roledescription="mermaid"]', timeout=5000)
    except:
        pass # If no mermaid, it just times out and proceeds
    page.pdf(path=pdf_file, format="A4", print_background=True)
    browser.close()

print(f'PDF saved to: {pdf_file}')
