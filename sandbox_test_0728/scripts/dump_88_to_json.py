import json
import os
from pathlib import Path
from datetime import datetime

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
md_dir = Path(r"A:\processed_md_v4_backup")

def dump():
    cutoff = datetime(2026, 7, 14)
    old_bases = []
    
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                srt_name = parts[4]
                md_name = srt_name.replace('.srt', '.md')
                p = md_dir / md_name
                if p.exists():
                    ctime = datetime.fromtimestamp(p.stat().st_ctime)
                    if ctime < cutoff:
                        old_bases.append(srt_name.replace('.srt', ''))
                        
    out_path = r"C:\LocalAI_Workstation\old_engine_courses.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(old_bases, f, ensure_ascii=False, indent=2)
    print(f"Dumped {len(old_bases)} items to {out_path}")

if __name__ == '__main__':
    dump()
