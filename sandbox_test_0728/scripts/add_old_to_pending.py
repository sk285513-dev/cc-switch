import os
import re
from pathlib import Path
from datetime import datetime

artifact_dir = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950"
processed_list_path = os.path.join(artifact_dir, "clean_processed_list.md")
pending_list_path = os.path.join(artifact_dir, "clean_pending_list_final.md")
md_dir = Path(r"A:\processed_md")

def process():
    if not os.path.exists(processed_list_path):
        print("Processed list not found")
        return
        
    with open(processed_list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    old_items = []
    cutoff = datetime(2026, 7, 14)
    
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                idx = parts[1]
                course = parts[2]
                video = parts[3]
                srt_name = parts[4]
                md_name = srt_name.replace('.srt', '.md')
                size_kb = parts[5]
                dur_min = parts[6]
                
                p = md_dir / md_name
                if p.exists():
                    ctime = datetime.fromtimestamp(p.stat().st_ctime)
                    if ctime < cutoff:
                        old_items.append({
                            "course": course,
                            "video": video,
                            "dur_min": dur_min,
                            "reason": "舊版引擎產物 (無本地切片備份)"
                        })

    print(f"Found {len(old_items)} old items.")
    
    # Generate the appended markdown for the pending list
    append_lines = [
        "",
        "---",
        "",
        "## ⚠️ 舊引擎歷史包袱 (強制重置以補足 v5.1 備份機制)",
        "以下 102 堂課程雖然在舊版 SRT 驗證中過關，但因為是 7/14 前使用舊引擎處理的產物，**完全沒有本地切片備份**。為了符合 v5.1 最高標準並確保未來具備免 API 重做能力，已將其強制降級加入待處理佇列中重新回爐：",
        "",
        "| 編號 | 課程標籤 | 原始影片檔名 | 原始時長 (分) | 降級原因 |",
        "|---|---|---|---|---|"
    ]
    
    # Try to find the highest ID in pending list to continue numbering
    start_idx = 1000 # default
    if os.path.exists(pending_list_path):
        with open(pending_list_path, "r", encoding="utf-8") as f:
            p_content = f.read()
            matches = re.findall(r'\| (\d+) \|', p_content)
            if matches:
                start_idx = max([int(m) for m in matches]) + 1
    
    for i, item in enumerate(old_items):
        append_lines.append(f"| {start_idx + i} | {item['course']} | {item['video']} | {item['dur_min']} | {item['reason']} |")
        
    append_str = "\n".join(append_lines)
    
    if os.path.exists(pending_list_path):
        with open(pending_list_path, "a", encoding="utf-8") as f:
            f.write("\n" + append_str + "\n")
        print("Successfully appended to pending list!")
    else:
        print(f"Pending list not found at {pending_list_path}")

if __name__ == '__main__':
    process()
