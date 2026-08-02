lines = open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8').readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if 'import sys' in line and 'if sys.stdout is None or getattr(sys.stdout, "closed", False):' in lines[i+1]:
        skip = True
        continue
    if skip and 'return False' in line:
        skip = False
        continue
    if not skip:
        new_lines.append(line)

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
