import os
import datetime
from pathlib import Path

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
srt_dir = Path(r"A:\processed_md")

def check_status():
    if not os.path.exists(list_path):
        return
        
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    valid_items = []
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                valid_items.append({
                    "course": parts[2],
                    "video": parts[3],
                    "srt_name": parts[4]
                })

    after_714_count = 0
    has_backup_count = 0
    
    cutoff_date = datetime.datetime(2026, 7, 14, 0, 0, 0)
    
    backup_dirs = [Path(r"F:\chunks_backup"), Path(r"E:\chunks_backup"), Path(r"A:\chunks")]
    
    for item in valid_items:
        srt_path = srt_dir / item["srt_name"]
        if not srt_path.exists():
            continue
            
        # Check date
        mtime = datetime.datetime.fromtimestamp(srt_path.stat().st_mtime)
        if mtime >= cutoff_date:
            after_714_count += 1
            
        # Check backup
        stem = srt_path.stem
        # chunk backup could be a folder named like stem
        # let's look for any folder in backup dirs that contains the stem
        found_backup = False
        for bdir in backup_dirs:
            if not bdir.exists():
                continue
            # The backup folder is usually named same as the video stem or has it inside
            # Let's check if there is a directory matching the exact stem
            possible_target = bdir / stem
            if possible_target.exists() and possible_target.is_dir():
                found_backup = True
                break
                
            # sometimes it's stem + "_chunks"
            possible_target2 = bdir / f"{stem}_chunks"
            if possible_target2.exists() and possible_target2.is_dir():
                found_backup = True
                break
                
        if found_backup:
            has_backup_count += 1

    print(f"Total: {len(valid_items)}")
    print(f"After 7/14: {after_714_count}")
    print(f"Has Backup: {has_backup_count}")
    
if __name__ == '__main__':
    check_status()
