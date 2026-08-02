import os
from pathlib import Path

count = 0
for p in Path('C:/LocalAI_Workstation/scripts').glob('**/*.py'):
    try:
        content = p.read_text(encoding='utf-8-sig')
        new_content = content.replace('encoding="utf-8-sig"', 'encoding="utf-8-sig"').replace("encoding='utf-8-sig'", "encoding='utf-8-sig'")
        if content != new_content:
            p.write_text(new_content, encoding='utf-8-sig')
            count += 1
    except Exception as e:
        pass
print(f'Replaced {count} files.')
