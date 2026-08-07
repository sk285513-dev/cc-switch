import os
import sys
import shutil

sys.stdout.reconfigure(encoding='utf-8')

processed_dir = "A:/processed_md/"
quarantine_dir = "A:/quarantine/"

if not os.path.exists(processed_dir):
    print("A:/processed_md/ does not exist!")
    sys.exit()

os.makedirs(quarantine_dir, exist_ok=True)

expected_exts = ['.md', '.srt', '.vtt', '.txt', '_index.json']
MIN_FILE_SIZE_KB = 2.0

stems = set()
for f in os.listdir(processed_dir):
    if f.endswith('.md') and not f.startswith("00_"):
        stem = f[:-3]
        stems.add(stem)

valid_count = 0
failed_count = 0
failures = []

for stem in stems:
    missing = []
    too_small = []
    for ext in expected_exts:
        path = os.path.join(processed_dir, f"{stem}{ext}")
        if not os.path.exists(path):
            missing.append(ext)
        else:
            size_kb = os.path.getsize(path) / 1024.0
            if size_kb < MIN_FILE_SIZE_KB:
                too_small.append(ext)
    
    if missing or too_small:
        failures.append(stem)
        failed_count += 1
    else:
        valid_count += 1

print(f"Total processed stems checked: {len(stems)}")
print(f"[Valid] (all 5 files present & size >= {MIN_FILE_SIZE_KB}KB): {valid_count}")
print(f"[Failed] (Missing files or too small): {failed_count}")
print(f"Quarantining {failed_count} failed stems to {quarantine_dir}...")

moved_files = 0
for stem in failures:
    for f in os.listdir(processed_dir):
        if f.startswith(stem):
            src_path = os.path.join(processed_dir, f)
            dest_path = os.path.join(quarantine_dir, f)
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                shutil.move(src_path, dest_path)
                moved_files += 1
            except Exception as e:
                print(f"Error moving {f}: {e}")

print(f"Quarantine complete! Moved {moved_files} leftover files.")
print("The failed courses will now be correctly re-ingested as new tasks by auto_ingest_bot.py on its next run.")
