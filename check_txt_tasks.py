import json
import os
from pathlib import Path

manifest_dir = Path('A:/manifests')
txt_tasks = []

if manifest_dir.exists():
    for json_file in manifest_dir.glob('task_*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                source_file = data.get('source_file', '')
                if source_file.lower().endswith('.txt'):
                    txt_tasks.append(data)
        except Exception:
            pass

print(f"Found {len(txt_tasks)} tasks that are tracking .txt files.")
for i, t in enumerate(txt_tasks[:10]):
    print(f"Task {t.get('task_id')}: {t.get('source_file')} -> Status: {t.get('status')}")
