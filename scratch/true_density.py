import os
import glob
import subprocess

# Add scripts path so we can import the helper
import sys
sys.path.append(r'C:\LocalAI_Workstation\scripts')
try:
    from auto_ingest_bot import get_video_duration_and_size
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

transcript_dir = r"C:\LocalAI_Workstation\Transcripts"
raw_dirs = [r"C:\LocalAI_Workstation\raw_data", r"J:", r"H:"]

txt_files = glob.glob(os.path.join(transcript_dir, "*_逐字稿.txt"))
results = []

def find_raw_media(base_name):
    for d in raw_dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if f.startswith(base_name) and f.lower().endswith(('.mp4', '.mp3', '.wav')):
                    return os.path.join(root, f)
    return None

import re

count = 0
for txt in txt_files:
    if count > 20: # Just take a sample of 20 as requested by the user
        break
    
    # name looks like: 預設課程_processed_md_[民法B_ch30]_預約 30 2025-04-17 20-50-00-678_逐字稿.txt
    # extract the core filename: 預約 30 2025-04-17 20-50-00-678
    m = re.search(r'\]_(.*)_逐字稿\.txt$', txt)
    if not m:
        m = re.search(r'\]_(.*)\.md$', txt)
    if not m:
        continue
        
    core_name = m.group(1)
    
    raw_path = find_raw_media(core_name)
    if not raw_path:
        continue
        
    try:
        dur, _, _ = get_video_duration_and_size(raw_path)
        if dur > 20:
            size_kb = os.path.getsize(txt) / 1024
            ratio = size_kb / dur
            results.append((core_name, size_kb, dur, ratio))
            count += 1
    except:
        pass

if not results:
    print("找不到足夠的有效檔案進行統計。")
else:
    results.sort(key=lambda x: x[3])
    print(f"{'檔案名稱':<40} | {'體積(KB)':<10} | {'長度(分)':<10} | {'KB/分':<10}")
    print("-" * 80)
    total_ratio = 0
    for name, size, dur, ratio in results:
        print(f"{name[:38]:<40} | {size:<10.1f} | {dur:<10.1f} | {ratio:<10.2f}")
        total_ratio += ratio
        
    print("-" * 80)
    print(f"總共統計: {len(results)} 個檔案")
    avg = total_ratio / len(results)
    print(f"平均密度: {avg:.2f} KB/分")
    print(f"最低密度: {results[0][3]:.2f} KB/分")
    print(f"最高密度: {results[-1][3]:.2f} KB/分")
