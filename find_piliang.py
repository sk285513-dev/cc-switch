import os
for root, dirs, files in os.walk(r'C:\LocalAI_Workstation'):
    if '.git' in root or '.venv' in root: continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8-sig') as file:
                    content = file.read()
                    if '批量' in content:
                        print(f"Found '批量' in {path}")
            except: pass
