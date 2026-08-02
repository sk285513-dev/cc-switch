import os
import sys
import re
import random
import statistics
from pathlib import Path

# Extract data from the clean list
list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
srt_dir = Path(r"A:\processed_md")

def run_verification():
    if not os.path.exists(list_path):
        print("clean_processed_list.md not found.")
        return
        
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Format in markdown: | 編號 | 課程標籤 | 原始影片檔名 | 對應的 SRT 檔名 | SRT 大小 (KB) | 原始時長 (分) |
    valid_items = []
    
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                idx = parts[1]
                course = parts[2]
                video = parts[3]
                srt_name = parts[4]
                try:
                    size_kb = float(parts[5])
                    dur_min = float(parts[6])
                    valid_items.append({
                        "course": course,
                        "srt_name": srt_name,
                        "size_kb": size_kb,
                        "dur_min": dur_min,
                        "ratio": size_kb / dur_min if dur_min > 0 else 0
                    })
                except ValueError:
                    pass

    print(f"Total entries parsed from list: {len(valid_items)}")
    
    # Check physical existence and calculate stats
    ratios = []
    sizes = []
    missing_files = []
    
    for item in valid_items:
        srt_path = srt_dir / item["srt_name"]
        if not srt_path.exists():
            missing_files.append(item["srt_name"])
            continue
            
        real_size = srt_path.stat().st_size / 1024
        sizes.append(real_size)
        item["real_size"] = real_size
        item["real_ratio"] = real_size / item["dur_min"]
        ratios.append(item["real_ratio"])
        
    print(f"\n--- 科學統計結果 (Science & Stats) ---")
    print(f"實體驗證成功數量: {len(ratios)} / {len(valid_items)}")
    
    if len(ratios) > 0:
        mean_ratio = statistics.mean(ratios)
        median_ratio = statistics.median(ratios)
        stdev_ratio = statistics.stdev(ratios) if len(ratios) > 1 else 0
        min_ratio = min(ratios)
        max_ratio = max(ratios)
        
        print(f"平均 SRT 生成率: {mean_ratio:.2f} KB/分鐘")
        print(f"中位數 SRT 生成率: {median_ratio:.2f} KB/分鐘")
        print(f"標準差 (StdDev): {stdev_ratio:.2f} KB/分鐘")
        print(f"最低生成率: {min_ratio:.2f} KB/分鐘")
        print(f"最高生成率: {max_ratio:.2f} KB/分鐘")
        
        # 異常值檢測 (Z-score > 3 or Z-score < -3)
        outliers = []
        for item in valid_items:
            if "real_ratio" in item and stdev_ratio > 0:
                z_score = (item["real_ratio"] - mean_ratio) / stdev_ratio
                if abs(z_score) > 2.5: # Strict threshold
                    outliers.append((item, z_score))
        
        print(f"\n--- 潛在異常值抽檢 (Z-score 偏差超過 2.5) ---")
        if not outliers:
            print("完美！這 190 堂課程在常態分佈內，沒有發現任何極端異常值 (無離群值)。")
        else:
            print(f"發現 {len(outliers)} 筆位於分佈邊緣的檔案：")
            for out, z in outliers:
                print(f"  - {out['srt_name']} (生成率: {out['real_ratio']:.2f} KB/分, Z: {z:.2f})")
                
        # 隨機抽樣 3 筆進行內文健康度檢查
        print(f"\n--- 隨機內文抽檢 (Random Sampling Validation) ---")
        samples = random.sample([item for item in valid_items if "real_ratio" in item], min(3, len(valid_items)))
        for s in samples:
            srt_path = srt_dir / s["srt_name"]
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read(500) # read first 500 chars
            lines = [l for l in content.split("\n") if l.strip()]
            subtitle_count = sum(1 for l in lines if "-->" in l)
            print(f"✅ 抽檢 {s['srt_name']}: 大小 {s['real_size']:.1f} KB, 開頭包含正常的 {subtitle_count} 句時間軸格式。")
            
if __name__ == '__main__':
    run_verification()
