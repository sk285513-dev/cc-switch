import os
import re

input_file = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/PIPELINE_DEPENDENCIES.md"

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

def remove_colons_in_mermaid(match):
    code = match.group(1)
    code = code.replace(':', '-')
    return f'`mermaid\n{code}\n`'

content = re.sub(r'`mermaid\n(.*?)\n`', remove_colons_in_mermaid, content, flags=re.DOTALL)

with open(input_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Colons replaced with hyphens in mermaid blocks!")
