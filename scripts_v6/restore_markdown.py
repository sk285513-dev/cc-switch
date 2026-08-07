import sys, os

with open('C:/LocalAI_Workstation/LexMind_V6_Source_Code_Mirror.txt', 'r', encoding='utf-8') as f:
    content = f.read()

parts = content.split('=========================================\nFILE: ')
for p in parts:
    if p.startswith('markdown_formatter.py'):
        lines = p.split('\n', 2)
        code = lines[2]
        with open('C:/LocalAI_Workstation/scripts_v6/markdown_formatter.py', 'w', encoding='utf-8-sig') as out_f:
            out_f.write(code.strip() + '\n')
        break

