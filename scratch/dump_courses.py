import os
import sys

workspace_root = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站"
sys.path.append(os.path.join(workspace_root, "scripts_v6"))

from auto_ingest_bot import scan_drives, is_file_content_legal, SUPPORTED_EXTS

target_drives = ["H:\\", "J:\\"]
all_courses = []

for drive in target_drives:
    if not os.path.exists(drive):
        continue
    valid_folders = scan_drives(drive)
    for folder in valid_folders:
        try:
            for f in os.listdir(folder):
                f_path = os.path.join(folder, f)
                if os.path.isfile(f_path) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
                    if is_file_content_legal(f_path):
                        all_courses.append(f_path)
        except Exception:
            pass

all_courses.sort()
out_path = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scratch/all_courses_list.md"
with open(out_path, 'w', encoding='utf-8') as out:
    out.write(f"# 找到的 492 筆檔案清單\n\n")
    for idx, c in enumerate(all_courses):
        out.write(f"{idx+1}. {c}\n")

print(f"Dumped {len(all_courses)} files to {out_path}")
