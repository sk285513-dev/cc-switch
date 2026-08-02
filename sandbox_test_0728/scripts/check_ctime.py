import os
import re
from pathlib import Path
from datetime import datetime

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
md_dir = Path(r"A:\processed_md")

def check():
    if not os.path.exists(list_path): return
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    valid_items = []
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                valid_items.append(parts[4].replace('.srt', '.md'))

    c_before = 0
    c_after = 0
    cutoff = datetime(2026, 7, 14)
    
    for md_name in valid_items:
        p = md_dir / md_name
        if p.exists():
            ctime = datetime.fromtimestamp(p.stat().st_ctime)
            if ctime < cutoff:
                c_before += 1
            else:
                c_after += 1

    print(f"By File Creation Time (st_ctime):")
    print(f"Before 7/14: {c_before}")
    print(f"After 7/14: {c_after}")

if __name__ == '__main__':
    check()
