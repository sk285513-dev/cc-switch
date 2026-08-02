try:
    import json
except ImportError:
    import json
import os
import json
from pathlib import Path

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"

def check():
    if not os.path.exists(list_path):
        return
        
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    valid_videos = set()
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                valid_videos.add(parts[3])

    backup_dirs = [Path(r"F:\chunks_backup"), Path(r"E:\chunks_backup"), Path(r"A:\chunks")]
    
    backed_up_videos = set()
    total_backup_folders = 0
    
    for bdir in backup_dirs:
        if not bdir.exists(): continue
        for d in bdir.iterdir():
            if d.is_dir():
                total_backup_folders += 1
                manifest_path = d / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            video_name = data.get("original_video_name") or data.get("original_video")
                            if video_name:
                                backed_up_videos.add(os.path.basename(video_name))
                    except:
                        pass

    # Count how many of the 190 valid videos have a backup
    has_backup_count = 0
    for v in valid_videos:
        if v in backed_up_videos:
            has_backup_count += 1
            
    print(f"Total backup folders scanned: {total_backup_folders}")
    print(f"Number of 190 healthy courses with local chunk backup: {has_backup_count} / {len(valid_videos)}")

if __name__ == '__main__':
    check()
