import json
from pathlib import Path

MANIFESTS = Path('A:/manifests')
tasks = []
for mf in MANIFESTS.glob("task_*.json"):
    if "_chunks" in mf.name:
        continue
    try:
        data = json.loads(mf.read_text(encoding='utf-8'))
        tasks.append((str(mf), data.get('source_path', ''), data.get('status')))
    except Exception:
        pass

# Print tasks that look like temp_extract or don't match typical legal video naming
for mf_path, src, status in tasks:
    if "temp_extract" in src or "bandicam" in src.lower() or "mock" in src.lower() or "test" in src.lower() or "2024-10-13 17-30-31" in src:
        print(f"Suspicious task: {src} -> {mf_path}")
