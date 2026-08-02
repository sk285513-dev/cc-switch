import codecs
import re
path = r'C:\Users\temp\.gemini\antigravity\brain\e6fcb001-67fa-4006-bd69-8e5649678c85\LexMind_Omni_v5.1_Plan_Reviewed.md'
with codecs.open(path, 'r', 'utf-8') as f:
    lines = f.read().split('\n')
out_lines = []
in_code_block = False
for line in lines:
    sline = line.strip()
    is_marker = sline.startswith('* **修改前') or sline.startswith('* **修改後') or sline.startswith('* [ ]') or sline.startswith('* [x]') or sline.startswith('* *(已修復)*')
    if is_marker and in_code_block:
        out_lines.append('`')
        in_code_block = False
    
    if sline.startswith('`'):
        if 'python' in sline or 'diff' in sline or 'typescript' in sline or 'bash' in sline:
            line = '`' + sline.lstrip('')
            if not in_code_block: in_code_block = True
            else: in_code_block = False
        else:
            line = '`'
            in_code_block = not in_code_block
    
    if is_marker:
        line = sline
    out_lines.append(line)

if in_code_block:
    out_lines.append('`')

with codecs.open(path, 'w', 'utf-8') as f:
    f.write('\n'.join(out_lines))
print('Markdown rigidly formatted.')

