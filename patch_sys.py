lines = open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8').readlines()
for i, line in enumerate(lines):
    if 'def load_from_disk(cls):' in line:
        lines.insert(i + 4, '            import sys\n')
        lines.insert(i + 5, '            if sys.stdout is None or getattr(sys.stdout, "closed", False):\n')
        lines.insert(i + 6, '                return False\n')
        break

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
