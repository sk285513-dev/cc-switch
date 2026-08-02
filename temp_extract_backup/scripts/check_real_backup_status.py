import os
import re
from pathlib import Path

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
log_path = r"A:\logs\workflow.log"

def check():
    if not os.path.exists(list_path):
        return
        
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    valid_srt_names = set()
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                valid_srt_names.add(parts[4])

    print(f"Total healthy files to check: {len(valid_srt_names)}")
    
    # Parse workflow.log to build a map of {srt_name: task_id}
    # Look for patterns like: 
    # Markdown Formatter: Saved SRT subtitle to A:\processed_md\[Course]_[Video].srt
    # and shortly after: Completed task task_20260707013259_1007
    
    current_srt = None
    srt_to_task = {}
    
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "Saved SRT subtitle to" in line:
                    match = re.search(r'A:\\processed_md\\([^\\]+\.srt)', line)
                    if match:
                        current_srt = match.group(1)
                elif "Completed task" in line and current_srt:
                    match = re.search(r'Completed task (task_[a-zA-Z0-9_]+)', line)
                    if match:
                        task_id = match.group(1)
                        srt_to_task[current_srt] = task_id
                        current_srt = None

    print(f"Parsed {len(srt_to_task)} mappings from workflow.log")

    backup_dirs = [Path(r"F:\chunks_backup"), Path(r"E:\chunks_backup"), Path(r"A:\chunks")]
    
    # Collect all available backup task IDs
    available_backups = set()
    for bdir in backup_dirs:
        if not bdir.exists(): continue
        for d in bdir.iterdir():
            if d.is_dir() and d.name.startswith("task_"):
                available_backups.add(d.name)
                
    print(f"Found {len(available_backups)} backup task folders on disk.")

    has_backup_count = 0
    missing_mapping_count = 0
    
    for srt in valid_srt_names:
        task_id = srt_to_task.get(srt)
        if task_id:
            if task_id in available_backups:
                has_backup_count += 1
        else:
            missing_mapping_count += 1

    print(f"\nResult:")
    print(f"Healthy Courses: 190")
    print(f"Successfully Backed Up: {has_backup_count} 堂")
    print(f"No Backup Found (or missing logs): {190 - has_backup_count} 堂 (其中 {missing_mapping_count} 堂在日誌中找不到 Task ID)")

if __name__ == '__main__':
    check()
