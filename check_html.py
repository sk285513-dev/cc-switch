import re
with open(r'c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

div_open = len(re.findall(r'<div\b', text))
div_close = len(re.findall(r'</div\b', text))
print(f'Open div: {div_open}, Close div: {div_close}')

span_open = len(re.findall(r'<span\b', text))
span_close = len(re.findall(r'</span\b', text))
print(f'Open span: {span_open}, Close span: {span_close}')
