import os
import re

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
                
                # Extract all timestamps like 00:11:11,000
                times = re.findall(r'(\d{2}):(\d{2}):(\d{2}),\d{3} --> (\d{2}):(\d{2}):(\d{2}),\d{3}', content)
                
                last_seconds = 0
                is_buggy = False
                for start_t in times:
                    h, m, s = int(start_t[0]), int(start_t[1]), int(start_t[2])
                    current_seconds = h * 3600 + m * 60 + s
                    
                    if current_seconds < last_seconds - 5: # sudden drop backwards
                        is_buggy = True
                        break
                    last_seconds = current_seconds
                
                if is_buggy:
                    buggy_files.append(f)
        except Exception as e:
            pass

print(f"掃描完畢。發現 {len(buggy_files)} 個有時間軸回溯錯誤的 SRT 檔案。")
if buggy_files:
    for bf in buggy_files:
        print(f" - {bf}")
