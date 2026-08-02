import markdown
import codecs

path = r'C:\LocalAI_Workstation\Formatted.md'
out_path = r'C:\LocalAI_Workstation\LexMind_Omni_計畫書_正式版.html'

with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

# Convert to HTML with extensions
html_content = markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br'])

# Beautiful CSS
css = """
<style>
    body { font-family: "Microsoft JhengHei", sans-serif; line-height: 1.6; padding: 40px; }
    h1, h2, h3 { color: #2c3e50; }
    code { background-color: #e8e8e8; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; }
    pre { background-color: #2d3436; padding: 15px; border-radius: 8px; color: #f8f8f2; }
    table { width: 100%; border-collapse: collapse; margin: 1.5em 0; }
    th, td { border: 1px solid #ddd; padding: 12px; }
    th { background-color: #3498db; color: white; }
</style>
"""

full_html = f"<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n<title>LexMind-Omni 計畫書正式版</title>\n{css}\n</head>\n<body>\n{html_content}\n</body>\n</html>"

with codecs.open(out_path, 'w', 'utf-8') as f:
    f.write(full_html)
print("HTML Generated successfully.")
