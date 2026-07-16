import os
import re
import glob

transcript_dir = r"C:\LocalAI_Workstation\Transcripts"
files = glob.glob(os.path.join(transcript_dir, "*_逐字稿.txt")) + glob.glob(r"A:\processed_md\*.md")

results = []
timestamp_pattern = re.compile(r'\[(\d{1,2}):(\d{2}):(\d{2})')

for f in files:
    try:
        size_kb = os.path.getsize(f) / 1024
        with open(f, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            matches = timestamp_pattern.findall(content)
            if len(matches) < 2:
                continue
            
            first_match = matches[0]
            last_match = matches[-1]
            
            h1, m1, s1 = map(int, first_match)
            h2, m2, s2 = map(int, last_match)
            
            t1 = h1 * 60 + m1 + s1 / 60.0
            t2 = h2 * 60 + m2 + s2 / 60.0
            
            # handle midnight rollover if t2 < t1
            if t2 < t1:
                t2 += 24 * 60
                
            duration_mins = t2 - t1
            
            if duration_mins > 20:
                ratio = size_kb / duration_mins
                results.append((os.path.basename(f), size_kb, duration_mins, ratio))
    except Exception as e:
        print(f"Error {f}: {e}")

if not results:
    print("找不到足夠的有效檔案進行統計。")
else:
    results.sort(key=lambda x: x[3])
    print(f"{'檔案名稱':<50} | {'體積(KB)':<10} | {'長度(分)':<10} | {'KB/分':<10}")
    print("-" * 90)
    total_ratio = 0
    for name, size, dur, ratio in results:
        print(f"{name[:48]:<50} | {size:<10.1f} | {dur:<10.1f} | {ratio:<10.2f}")
        total_ratio += ratio
        
    print("-" * 90)
    print(f"總共統計: {len(results)} 個檔案")
    print(f"平均密度: {total_ratio / len(results):.2f} KB/分")
    print(f"最低密度: {results[0][3]:.2f} KB/分")
    print(f"最高密度: {results[-1][3]:.2f} KB/分")
