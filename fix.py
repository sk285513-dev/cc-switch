import os

fp = r'C:\Users\temp\.gemini\antigravity\brain\eb79f8e8-2bb0-4444-8d10-8f28ae6fdf6f\implementation_plan.md'
with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_code = False

for line in lines:
    stripped = line.strip()
    
    if stripped == '`mermaid':
        new_lines.append('  ```mermaid\n')
        in_code = True
    elif stripped == '``python' or stripped == '`python':
        new_lines.append('  ```python\n')
        in_code = True
    elif stripped == '``vbscript' or stripped == '`vbscript':
        new_lines.append('  ```vbscript\n')
        in_code = True
    elif stripped == '```python' or stripped == '```vbscript' or stripped == '```mermaid':
        new_lines.append(line)
        in_code = True
    elif stripped == '```':
        new_lines.append(line)
        in_code = False
    elif stripped == '`' or stripped == '``':
        if in_code:
            new_lines.append('  ```\n')
            in_code = False
        else:
            new_lines.append('\n')
    else:
        new_lines.append(line)

with open(r'C:\LocalAI_Workstation\fixed_plan.md', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Done sanitizing!')
