import os
import sys
from collections import defaultdict

workspace_root = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站"
sys.path.append(os.path.join(workspace_root, "scripts_v6"))

from auto_ingest_bot import scan_drives, is_file_content_legal, SUPPORTED_EXTS, load_ingested_history, is_file_already_ingested, get_processed_stems

history = load_ingested_history()
processed_stems = get_processed_stems()

print(f"快取中已處理完成的課程數量: {len(processed_stems)} 堂")

target_drives = ["H:\\", "J:\\"]
all_courses = []
processed_count = 0
unprocessed_count = 0

print("\n開始掃描 H: 與 J: 磁碟...")

for drive in target_drives:
    if not os.path.exists(drive):
        print(f"磁碟 {drive} 不存在，跳過。")
        continue
    
    # 使用新版雙重驗證機制的掃描器
    valid_folders = scan_drives(drive)
    print(f"在 {drive} 找到 {len(valid_folders)} 個符合雙重特徵 (科目+課程) 的資料夾")
    
    for folder in valid_folders:
        try:
            for f in os.listdir(folder):
                f_path = os.path.join(folder, f)
                if os.path.isfile(f_path) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
                    if is_file_content_legal(f_path):
                        is_processed = is_file_already_ingested(f_path, history)
                        all_courses.append({
                            "path": f_path,
                            "name": f,
                            "processed": is_processed
                        })
                        if is_processed:
                            processed_count += 1
                        else:
                            unprocessed_count += 1
        except Exception as e:
            print(f"讀取資料夾錯誤 {folder}: {e}")

print("\n=== 掃描統計報告 ===")
print(f"總計發現合法課程數: {len(all_courses)}")
print(f"✅ 已處理 (已註記/備份): {processed_count}")
print(f"⏳ 待處理 (可進入管線): {unprocessed_count}")

print("\n=== 前 10 筆待處理清單 (Sample) ===")
sampled = 0
for c in all_courses:
    if not c["processed"]:
        print(f"⏳ [待處理] {c['name']}")
        sampled += 1
        if sampled >= 10:
            break

print("\n=== 前 10 筆已處理清單 (Sample) ===")
sampled = 0
for c in all_courses:
    if c["processed"]:
        print(f"✅ [已處理] {c['name']}")
        sampled += 1
        if sampled >= 10:
            break
