import os
from pathlib import Path
from datetime import datetime

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
md_dir = Path(r"A:\processed_md")

def check():
    if not os.path.exists(list_path): return
    with open(list_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        
    old_items = []
    new_items = []
    cutoff = datetime(2026, 7, 14)
    
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                md_name = parts[4].replace('.srt', '.md')
                p = md_dir / md_name
                if p.exists():
                    ctime = datetime.fromtimestamp(p.stat().st_ctime)
                    if ctime < cutoff:
                        old_items.append(md_name)
                    else:
                        new_items.append(md_name)

    print(f"Old items (< 7/14): {len(old_items)}")
    print(f"New items (>= 7/14): {len(new_items)}")

if __name__ == '__main__':
    check()
