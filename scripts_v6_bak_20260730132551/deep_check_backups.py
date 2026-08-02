import os
import re
from pathlib import Path

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"

def run():
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

    backup_dirs = [Path(r"F:\chunks_backup"), Path(r"E:\chunks_backup"), Path(r"A:\chunks")]
    task_folders = []
    
    for bdir in backup_dirs:
        if not bdir.exists(): continue
        for d in bdir.iterdir():
            if d.is_dir() and d.name.startswith("task_"):
                task_folders.append(d)

    print(f"Total backup folders: {len(task_folders)}")
    
    # Try to extract the first line of merged_summary.txt OR merged_cleaned_transcript.txt 
    # to see if we can match any text from the actual processed .txt files
    
    # Pre-load the first 100 chars of the actual processed TXT files for the 190 items
    md_dir = Path(r"A:\processed_md")
    item_signatures = {}
    
    for item in valid_items:
        txt_path = md_dir / item["srt_name"].replace('.srt', '.txt')
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read(500)
                # clean up
                content = re.sub(r'\s+', '', content)
                if len(content) > 50:
                    item_signatures[item["srt_name"]] = content[:50]
                    
    print(f"Loaded {len(item_signatures)} signatures from processed TXT files.")
    
    # Now check backup folders
    matched_tasks = set()
    mapped_srts = set()
    
    for folder in task_folders:
        # Check merged_full_transcript.txt or merged_cleaned_transcript.txt
        txt_file = folder / "merged_cleaned_transcript.txt"
        if not txt_file.exists():
            txt_file = folder / "merged_full_transcript.txt"
            
        if txt_file.exists():
            try:
                with open(txt_file, "r", encoding="utf-8-sig", errors="ignore") as f:
                    content = f.read(500)
                    content = re.sub(r'\s+', '', content)
                    if len(content) > 50:
                        sig = content[:50]
                        # find matching SRT
                        for srt, srt_sig in item_signatures.items():
                            if srt_sig in sig or sig in srt_sig:
                                matched_tasks.add(folder.name)
                                mapped_srts.add(srt)
                                break
            except:
                pass

    print(f"Successfully matched {len(mapped_srts)} processed files to their backup folders.")
    
    no_backup = [item["srt_name"] for item in valid_items if item["srt_name"] not in mapped_srts]
    print(f"No backup found for {len(no_backup)} courses.")
    
if __name__ == '__main__':
    run()
