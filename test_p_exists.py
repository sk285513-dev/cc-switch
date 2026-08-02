import os
import sys
from pathlib import Path

SUPPORTED_INGEST_EXTS = ['.mp4', '.mp3', '.wav', '.pdf', '.md', '.txt', '.png', '.jpg', '.jpeg', '.webp']
batch_paths = ["J:\\公司法B115\\ch17"]

seen_paths = set()
valid_files_info = []

for p_str in batch_paths:
    p = Path(p_str)
    print(f"Checking {p}")
    if not p.exists():
        print("Does not exist!")
        continue
    # ... rest of the logic ...
