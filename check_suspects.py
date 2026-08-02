import json
import os
from pathlib import Path

manifest_dir = Path('A:/manifests')
suspect_tasks = []

if manifest_dir.exists():
    for json_file in manifest_dir.glob('task_*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                name = data.get('name', '')
                if '預約' in name and not name.startswith('['):
                    suspect_tasks.append((json_file.name, data))
        except Exception:
            pass

print(f"Found {len(suspect_tasks)} suspect tasks.")
for fname, t in suspect_tasks[:10]:
    print(f"Task Name: {t.get('name')}")
    print(f"  Source: {t.get('source_file')}")
    print(f"  Status: {t.get('status')}")
    print(f"  n_chunks: {t.get('n_chunks')}")
