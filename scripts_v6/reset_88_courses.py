import os
import shutil
from pathlib import Path
from datetime import datetime

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
md_dir = Path(r"A:\processed_md")
backup_dir = Path(r"A:\processed_md_v4_backup")

def reset_courses():
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        
    if not os.path.exists(list_path):
        print("List not found!")
        return
        
    with open(list_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
        
    cutoff = datetime(2026, 7, 14)
    moved_count = 0
    base_count = 0
    
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
                        base_count += 1
                        base = srt_name.replace('.srt', '')
                        exts = ['.md', '.srt', '.vtt', '.txt', '_index.json']
                        for ext in exts:
                            src = md_dir / f"{base}{ext}"
                            dst = backup_dir / f"{base}{ext}"
                            if src.exists():
                                shutil.move(str(src), str(dst))
                                moved_count += 1
                                
    print(f"Successfully processed {base_count} old courses, moved {moved_count} files to {backup_dir}")

if __name__ == '__main__':
    reset_courses()
