import os
import re
import json
from pathlib import Path
from datetime import datetime

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
md_dir = Path(r"A:\processed_md")

def check():
    if not os.path.exists(list_path):
        print("List not found")
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
                    "srt_name": parts[4],
                    "md_name": parts[4].replace('.srt', '.md')
                })

    print(f"Total valid items: {len(valid_items)}")
    
    # 1. Parse MD files to get the true Analysis Date
    after_714_count = 0
    before_714_count = 0
    missing_md_count = 0
    
    cutoff_date = datetime(2026, 7, 14, 0, 0, 0)
    
    # Store original video names for backup matching
    md_to_video = {}
    
    for item in valid_items:
        md_path = md_dir / item["md_name"]
        if not md_path.exists():
            missing_md_count += 1
            continue
            
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read(2048) # Read first 2KB
            
        # Extract date
        date_match = re.search(r'- \*\*分析日期\*\*：(\d{4}-\d{2}-\d{2})', content)
        if date_match:
            date_str = date_match.group(1)
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                if dt >= cutoff_date:
                    after_714_count += 1
                else:
                    before_714_count += 1
            except ValueError:
                pass
                
        # Extract original video name
        video_match = re.search(r'- \*\*原始檔名\*\*：(.*\.mp4)', content)
        if video_match:
            md_to_video[item["md_name"]] = video_match.group(1).strip()
        else:
            md_to_video[item["md_name"]] = item["video"] # Fallback

    print(f"\n--- 處理時間統計 (根據 MD 內文的分析日期) ---")
    print(f"7/14 (含) 之後處理: {after_714_count} 堂")
    print(f"7/14 之前處理 (舊版本): {before_714_count} 堂")
    print(f"找不到 MD 檔或無日期: {len(valid_items) - after_714_count - before_714_count} 堂")
    
    # 2. Match with Backup Manifests
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
                            # manifest might have 'original_video' or 'original_video_name'
                            # e.g. "J:\\民法B\\ch15\\[民法B_ch15]_預約 15 2025-04-14 19-23-41-725.mp4"
                            video_path = data.get("original_video") or data.get("original_video_name", "")
                            if video_path:
                                v_name = os.path.basename(video_path)
                                backed_up_videos.add(v_name)
                    except:
                        pass
                        
    print(f"\n--- 切片備份統計 (Scan Backup Manifests) ---")
    print(f"找到的備份資料夾總數: {total_backup_folders}")
    
    has_backup_count = 0
    no_backup_list = []
    
    for item in valid_items:
        orig_video = md_to_video.get(item["md_name"], item["video"])
        # Match exactly or if the stem is in the backed up videos
        found = False
        for bv in backed_up_videos:
            if orig_video in bv or bv in orig_video:
                found = True
                break
                
        if found:
            has_backup_count += 1
        else:
            no_backup_list.append(item["course"] + " " + item["video"])
            
    print(f"這 190 堂課中，成功對應到本地切片備份的數量: {has_backup_count} 堂")
    print(f"沒有本地備份 (舊版上傳無備份機制): {len(valid_items) - has_backup_count} 堂")

if __name__ == '__main__':
    check()
