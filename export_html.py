import markdown
import codecs
import re

input_file = r'C:\LocalAI_Workstation\LexMind_Omni_金鑰調度架構與前端重構演進計畫_v5.1_Reviewed.md'
output_file = r'C:\LocalAI_Workstation\LexMind_Omni_金鑰調度架構與前端重構演進計畫_v5.1_Reviewed.html'

with codecs.open(input_file, mode='r', encoding='utf-8') as f:
    text = f.read()

# Replace graph TD blocks so mermaid works in HTML
text = re.sub(r'`mermaid\s*(.*?)\s*`', r'<div class="mermaid">\1</div>', text, flags=re.DOTALL)

html_body = markdown.markdown(text, extensions=['fenced_code', 'tables'])

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>LexMind-Omni Implementation Plan v5.1 (Reviewed)</title>
<style>
    body {{ font-family: "Microsoft JhengHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; padding: 2em; max-width: 1000px; margin: 0 auto; color: #333; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; }}
    th {{ background-color: #f2f2f2; text-align: left; }}
    pre {{ background-color: #f6f8fa; padding: 16px; border-radius: 3px; overflow: auto; }}
    code {{ font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; font-size: 85%; background-color: rgba(27,31,35,.05); padding: .2em .4em; border-radius: 3px; }}
    pre code {{ background-color: transparent; padding: 0; }}
    img {{ max-width: 100%; height: auto; display: block; margin: 20px auto; }}
    h1, h2, h3 {{ border-bottom: 1px solid #eaecef; padding-bottom: .3em; }}
    blockquote {{ border-left: 4px solid #dfe2e5; padding: 0 1em; color: #6a737d; }}
</style>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true }});
</script>
</head>
<body>
{html_body}
</body>
</html>
'''

with codecs.open(output_file, mode='w', encoding='utf-8') as f:
    f.write(html)
print('HTML conversion complete.')
