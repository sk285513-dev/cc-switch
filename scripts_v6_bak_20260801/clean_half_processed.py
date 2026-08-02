import os
from pathlib import Path

def scan_and_clean_half_processed(dry_run=True):
    # Only scan the known course drives to avoid wasting time on C:\ or system drives
    drives = ['H:\\', 'J:\\']
    print(f"Scanning targeted course drives: {drives}", flush=True)
    
    half_processed_folders = []
    
    for drive in drives:
        if not os.path.exists(drive):
            continue
        print(f"Scanning {drive} ...", flush=True)
        for root, dirs, files in os.walk(drive):
            # Skip some obvious system folders
            if any(skip in root.lower() for skip in ['$recycle.bin', 'system volume information']):
                continue
                
            mp4_files = [f for f in files if f.lower().endswith('.mp4')]
            if not mp4_files:
                continue
                
            md_files = [f for f in files if f.lower().endswith('.md')]
            srt_files = [f for f in files if f.lower().endswith('.srt')]
            
            if not md_files:
                continue
                
            valid_srt = False
            for srt in srt_files:
                srt_path = os.path.join(root, srt)
                if os.path.getsize(srt_path) > 1024:
                    valid_srt = True
                    break
            
            if not valid_srt:
                half_processed_folders.append((root, files))

    print("\n" + "="*80, flush=True)
    print(f"找到 {len(half_processed_folders)} 個「半殘缺」資料夾 (包含 .md 但缺少有效 .srt)", flush=True)
    print("="*80, flush=True)
    
    deleted_count = 0
    for folder, files in half_processed_folders:
        print(f"\n[半殘資料夾] {folder}", flush=True)
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.md', '.srt', '.vtt', '.txt', '.json']:
                file_path = os.path.join(folder, file)
                if dry_run:
                    print(f"  [DRY RUN - WOULD DELETE] {file}", flush=True)
                else:
                    try:
                        os.remove(file_path)
                        print(f"  [DELETED] {file}", flush=True)
                        deleted_count += 1
                    except Exception as e:
                        print(f"  [ERROR] Could not delete {file}: {e}", flush=True)

    if dry_run:
        print(f"\n(Dry run complete. Found {len(half_processed_folders)} folders with files to clean.)", flush=True)
    else:
        print(f"\n(Clean complete. Deleted {deleted_count} files across {len(half_processed_folders)} folders.)", flush=True)

if __name__ == '__main__':
    # Run in ACTUAL DELETE mode to clean them instantly since the user asked!
    scan_and_clean_half_processed(dry_run=False)
