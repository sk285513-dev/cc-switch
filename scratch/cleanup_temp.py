import json
import os
from pathlib import Path

MANIFESTS = Path('A:/manifests')
deleted_count = 0

for mf in MANIFESTS.glob("task_*.json"):
    if "_chunks" in mf.name:
        continue
    try:
        data = json.loads(mf.read_text(encoding='utf-8'))
        src = data.get('source_path', '').lower()
        if 'temp_extract_' in src or 'bandicam' in src:
            print(f"Deleting temp/bandicam task: {src}")
            os.remove(mf)
            chunk_mf = str(mf).replace('.json', '_chunks.json')
            if os.path.exists(chunk_mf):
                os.remove(chunk_mf)
            deleted_count += 1
    except Exception:
        pass

print(f"\nTotal invalid temp/bandicam tasks deleted: {deleted_count}")
