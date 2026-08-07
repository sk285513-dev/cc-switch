import os
from pathlib import Path
import datetime

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
md_dir = Path(r"A:\processed_md")

def check():
    if not os.path.exists(list_path): return
    with open(list_path, "r", encoding="utf-8-sig") as f:
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

    # Collect backup task times
    backup_dirs = [Path(r"F:\chunks_backup"), Path(r"E:\chunks_backup"), Path(r"A:\chunks")]
    task_times = []
    
    for bdir in backup_dirs:
        if not bdir.exists(): continue
        for d in bdir.iterdir():
            if d.is_dir() and d.name.startswith("task_"):
                # Find the latest file inside the task folder to represent its completion time
                latest_time = 0
                for f in d.rglob("*"):
                    if f.is_file():
                        mtime = f.stat().st_mtime
                        if mtime > latest_time:
                            latest_time = mtime
                if latest_time > 0:
                    task_times.append((d.name, latest_time))

    print(f"Loaded {len(task_times)} backup tasks with timestamps.")
    
    # Match with SRT files
    has_backup = []
    no_backup = []
    
    for item in valid_items:
        srt_path = md_dir / item["srt_name"]
        if not srt_path.exists():
            continue
            
        srt_time = srt_path.stat().st_mtime
        
        # Find if any backup task completed within 60 seconds of this SRT file
        matched = False
        for task_name, t_time in task_times:
            if abs(t_time - srt_time) < 180: # within 3 minutes
                has_backup.append(item)
                matched = True
                break
                
        if not matched:
            no_backup.append(item)

    print(f"\n--- 依據時間戳記精準配對 (Time-Based Matching) ---")
    print(f"總計健康課程: {len(valid_items)} 堂")
    print(f"✅ 成功配對到實體備份切片: {len(has_backup)} 堂")
    print(f"❌ 無本地備份 (舊版引擎產物): {len(no_backup)} 堂")

if __name__ == '__main__':
    check()
