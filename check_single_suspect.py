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
                if data.get('n_chunks') == 0 or data.get('n_chunks') is None:
                    suspect_tasks.append((json_file.name, data))
        except Exception:
            pass

print(json.dumps(suspect_tasks[0], ensure_ascii=False, indent=2))
