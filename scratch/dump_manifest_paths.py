import json
from pathlib import Path

MANIFESTS = Path('A:/manifests')
paths = []
for mf in MANIFESTS.glob("task_*.json"):
    if "_chunks" in mf.name: continue
    try:
        data = json.loads(mf.read_text(encoding='utf-8'))
        paths.append(data.get('source_path', ''))
    except Exception:
        pass

with open('C:/LocalAI_Workstation/scratch/manifest_paths.txt', 'w', encoding='utf-8') as f:
    for p in sorted(paths):
        f.write(p + '\n')
print(f"Total manifests: {len(paths)}")
