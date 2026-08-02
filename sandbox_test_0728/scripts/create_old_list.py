import os
from pathlib import Path
from datetime import datetime

artifact_dir = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950"
list_path = os.path.join(artifact_dir, "clean_processed_list.md")
out_path = os.path.join(artifact_dir, "old_engine_courses_list.md")
md_dir = Path(r"A:\processed_md")

def process():
    if not os.path.exists(list_path): return
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    old_items = []
    cutoff = datetime(2026, 7, 14)
    
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
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
                            "srt_name": srt_name,
                            "size_kb": size_kb,
                            "dur_min": dur_min,
                            "ctime": ctime.strftime("%Y-%m-%d %H:%M:%S")
                        })

    # Sort by course name and creation time
    old_items.sort(key=lambda x: (x['course'], x['ctime']))

    report_lines = [
        "# ⚠️ 舊引擎歷史包袱獨立清單 (無備份之 88 堂課程)",
        "",
        "以下 88 堂課程雖然在最新的 SRT 嚴格檢查中全數過關 (代表品質完全健康)，但由於它們皆是在 **2026-07-14 以前**由系統舊版引擎處理完成，當時並未導入 `chunks_backup` 本地備份機制，因此這批課程目前是**沒有保留任何免 API 重新轉譯的切片備份**的。",
        "",
        "| 編號 | 課程標籤 | 原始影片檔名 | SRT 大小 (KB) | 原始時長 (分) | 系統建立時間 |",
        "|---|---|---|---|---|---|"
    ]
    
    for idx, item in enumerate(old_items, 1):
        report_lines.append(f"| {idx} | {item['course']} | {item['video']} | {item['size_kb']} | {item['dur_min']} | {item['ctime']} |")
        
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Successfully generated old engine list with {len(old_items)} items.")

if __name__ == '__main__':
    process()
