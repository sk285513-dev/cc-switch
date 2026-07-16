import os
import glob
import re

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

def detect_loop(content):
    # Very simple loop detection: look for a substring of length 30 repeating at least 5 times sequentially
    match = re.search(r'(.{30,100}?)\1{4,}', content)
    if match:
        return True, match.group(1)[:50] + "..."
    return False, ""

print("開始掃描並配對全部 241 個檔案 (這可能需要幾分鐘)...")

analyzed_count = 0
too_short = []
too_long = []
normal = []

# To speed up, we'll only scan the first 50 files for this test, or we can do all if it's fast enough.
# Actually, let's try to do all of them, but we'll print progress.

for idx, txt in enumerate(txt_files):
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
            
            with open(txt, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                has_loop, loop_text = detect_loop(content)
                
            file_info = {
                'name': core_name,
                'kb': size_kb,
                'dur': dur,
                'ratio': ratio,
                'has_loop': has_loop,
                'loop_text': loop_text
            }
            
            analyzed_count += 1
            if ratio < 0.6:
                too_short.append(file_info)
            elif ratio > 1.5:
                too_long.append(file_info)
            else:
                normal.append(file_info)
    except Exception as e:
        pass

print("-" * 80)
print(f"分析完成！共成功配對並分析了 {analyzed_count} 個有效檔案。")
print(f"✅ 正常範圍 (0.6 ~ 1.5): {len(normal)} 個檔案")
print(f"⚠️ 低於 0.6 (疑似漏轉): {len(too_short)} 個檔案")
print(f"🚨 高於 1.5 (疑似幻覺): {len(too_long)} 個檔案")
print("-" * 80)

if too_short:
    print("【低於 0.6 檔案清單】:")
    for x in sorted(too_short, key=lambda i: i['ratio']):
        print(f" - {x['name'][:30]:<30} | {x['kb']:<6.1f} KB | {x['dur']:<6.1f} 分 | 密度: {x['ratio']:.2f}")

if too_long:
    print("\n【高於 1.5 檔案清單】:")
    for x in sorted(too_long, key=lambda i: i['ratio'], reverse=True):
        loop_mark = "🔥發現無限迴圈!" if x['has_loop'] else "無明顯迴圈"
        print(f" - {x['name'][:30]:<30} | {x['kb']:<6.1f} KB | {x['dur']:<6.1f} 分 | 密度: {x['ratio']:.2f} | {loop_mark}")

