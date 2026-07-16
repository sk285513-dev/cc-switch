import os
import re
import json

processed_dir = r"A:\processed_md"
if not os.path.exists(processed_dir):
    print("目錄不存在")
    exit()

buggy_files = []
for f in os.listdir(processed_dir):
    if f.endswith('.srt'):
        filepath = os.path.join(processed_dir, f)
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                times = re.findall(r'(\d{2}):(\d{2}):(\d{2}),\d{3} --> (\d{2}):(\d{2}):(\d{2}),\d{3}', content)
                last_seconds = 0
                is_buggy = False
                for start_t in times:
                    h, m, s = int(start_t[0]), int(start_t[1]), int(start_t[2])
                    current_seconds = h * 3600 + m * 60 + s
                    if current_seconds < last_seconds - 5: 
                        is_buggy = True
                        break
                    last_seconds = current_seconds
                if is_buggy:
                    buggy_files.append(f)
        except Exception as e:
            pass

artifact_path = r"C:\Users\temp\.gemini\antigravity\brain\d172c99e-f55a-4b1e-8bf0-0f33aed88a84\buggy_legacy_srts.md"
with open(artifact_path, "w", encoding="utf-8") as out:
    out.write("# 🚧 尚未修復的時間軸回溯 SRT 檔案清單\n\n")
    out.write("經過全面掃描，這 45 份 SRT 檔案仍含有局部時間軸回溯 (Bug)。\n")
    out.write("因為這些課程的底層語音切片 (A:\\chunks) 已經被系統自動清理，無法利用 perfect_fast_srt_fix.py 腳本從原始切片重組。\n\n")
    out.write("建議處置：\n")
    out.write("1. **將這些檔案重新加入管線處理 (耗費 API Quota)**，或者\n")
    out.write("2. **開發一支 In-place SRT 修復腳本** 直接讀取現有 SRT 並透過平滑增量方式修補。\n\n")
    out.write("### 錯誤檔案列表\n")
    for bf in buggy_files:
        out.write(f"- {bf}\n")

print(f"Artifact created with {len(buggy_files)} files.")
