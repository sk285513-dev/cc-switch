import os
from pathlib import Path

def scan_and_clean_safe():
    drives = ['H:\\', 'J:\\']
    print(f"Scanning course drives: {drives}\n")
    
    half_processed_files = []
    
    for drive in drives:
        if not os.path.exists(drive):
            continue
        for root, dirs, files in os.walk(drive):
            if any(skip in root.lower() for skip in ['$recycle.bin', 'system volume information']):
                continue
            
            # Find all MP4s in the directory
            mp4_files = [f for f in files if f.lower().endswith('.mp4')]
            
            for mp4 in mp4_files:
                base_name = os.path.splitext(mp4)[0]
                
                md_name = f"{base_name}.md"
                srt_name = f"{base_name}.srt"
                
                # Check if the specific MD file exists
                if md_name in files:
                    srt_path = os.path.join(root, srt_name)
                    # If SRT doesn't exist, or is <= 1024 bytes, it's a half-processed file
                    if srt_name not in files or os.path.getsize(srt_path) <= 1024:
                        half_processed_files.append({
                            'root': root,
                            'base_name': base_name
                        })

    print("="*80)
    print(f"安全掃描完成：共找到 {len(half_processed_files)} 個半殘缺的課程檔")
    print("="*80)
    
    deleted_count = 0
    for item in half_processed_files:
        root = item['root']
        base = item['base_name']
        print(f"\n[半殘課程] {os.path.join(root, base + '.mp4')}")
        
        # We only delete the EXACT matching generated files
        for ext in ['.md', '.srt', '.vtt', '.txt', '.json']:
            target_file = os.path.join(root, f"{base}{ext}")
            if os.path.exists(target_file):
                try:
                    os.remove(target_file)
                    print(f"  [已清除] {base}{ext}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  [清除失敗] {base}{ext}: {e}")

    print(f"\n(清理完畢。共清除了 {deleted_count} 個周邊附屬檔案，MP4 原檔均已安全保留。)")

if __name__ == '__main__':
    scan_and_clean_safe()
