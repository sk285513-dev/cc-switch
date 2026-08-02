import os
import sys
import json
from pathlib import Path

# Mock st and session_state
SUPPORTED_INGEST_EXTS = ['.mp4', '.mp3', '.wav']
buffer_file = "C:\\LocalAI_Workstation\\buffer_paths.json"

if os.path.exists(buffer_file):
    with open(buffer_file, 'r', encoding='utf-8-sig') as f:
        batch_paths = json.load(f)
else:
    print("buffer_paths.json not found")
    batch_paths = []

print(f"Loaded {len(batch_paths)} paths from buffer")
if batch_paths:
    print(f"Sample: {batch_paths[0]}")

seen_paths = set()
valid_files_info = []

for p_str in batch_paths:
    p = Path(p_str)
    if not p.exists():
        print(f"Path does not exist: {p_str}")
        continue
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_INGEST_EXTS:
            abs_p = str(p.resolve())
            if abs_p not in seen_paths:
                seen_paths.add(abs_p)
                # simulate duplicate guard
                from scripts.duplicate_guard import check_name_duplicate
                if check_name_duplicate(abs_p):
                    valid_files_info.append((p.name, str(p), "local"))
                    continue
                valid_files_info.append((p.name, str(p), "local"))
    elif p.is_dir():
        files = list(p.rglob("*"))
        for f in files:
            if f.is_file() and f.suffix.lower() in SUPPORTED_INGEST_EXTS:
                abs_p = str(f.resolve())
                if abs_p not in seen_paths:
                    seen_paths.add(abs_p)
                    from scripts.duplicate_guard import check_name_duplicate
                    if check_name_duplicate(abs_p):
                        valid_files_info.append((f.name, str(f), "local"))
                        continue
                    valid_files_info.append((f.name, str(f), "local"))

print(f"Final valid_files_info count: {len(valid_files_info)}")
if not valid_files_info:
    print("Warning: valid_files_info is EMPTY!")
else:
    print("Success: files are ready.")

