import os
import re
import sys

workspace_root = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站"
sys.path.append(os.path.join(workspace_root, "scripts_v6"))
from auto_ingest_bot import scan_drives, is_file_content_legal, SUPPORTED_EXTS

target_drives = ["H:\\", "J:\\"]
mismatches = []

for drive in target_drives:
    if not os.path.exists(drive):
        continue
    valid_folders = scan_drives(drive)
    for folder in valid_folders:
        folder_name = os.path.basename(folder)
        # Extract ch number, e.g., 'ch32' -> 32
        folder_match = re.search(r'ch(\d+)', folder_name, re.IGNORECASE)
        if not folder_match:
            continue
        folder_num = int(folder_match.group(1))
        
        try:
            for f in os.listdir(folder):
                f_path = os.path.join(folder, f)
                if os.path.isfile(f_path) and os.path.splitext(f)[1].lower() == '.mp4':
                    # Extract 預約 number, e.g., '預約 4 2024-09-03...' -> 4, '預約 12-1' -> 12
                    file_match = re.search(r'預約\s*(\d+)', f, re.IGNORECASE)
                    if file_match:
                        file_num = int(file_match.group(1))
                        if file_num != folder_num:
                            mismatches.append({
                                "file": f_path,
                                "file_num": file_num,
                                "folder_num": folder_num,
                                "parent_dir": os.path.dirname(folder) # e.g. J:\行政法A
                            })
        except Exception:
            pass

print(f"Found {len(mismatches)} mismatches.")
for m in mismatches:
    print(f"File: {m['file']}")
    print(f"  -> Belongs in ch{m['file_num']}, currently in ch{m['folder_num']}")
