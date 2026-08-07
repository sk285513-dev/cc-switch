import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

processed_dir = "A:/processed_md/"

if not os.path.exists(processed_dir):
    print("A:/processed_md/ does not exist!")
    sys.exit()

expected_exts = ['.md', '.srt', '.vtt', '.txt', '_index.json']
MIN_FILE_SIZE_KB = 2.0  # At least 2KB for a valid ~3hr course transcript

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
        if ext == '_index.json':
            path = os.path.join(processed_dir, f"{stem}{ext}")
        else:
            path = os.path.join(processed_dir, f"{stem}{ext}")
        
        if not os.path.exists(path):
            missing.append(ext)
        else:
            size_kb = os.path.getsize(path) / 1024.0
            if size_kb < MIN_FILE_SIZE_KB:
                too_small.append(f"{ext} ({size_kb:.2f}KB)")
    
    if missing or too_small:
        failures.append({
            "course": stem,
            "missing": missing,
            "too_small": too_small
        })
        failed_count += 1
    else:
        valid_count += 1

print(f"Total processed stems checked: {len(stems)}")
print(f"[Valid] (all 5 files present & size >= {MIN_FILE_SIZE_KB}KB): {valid_count}")
print(f"[Failed] (Missing files or too small): {failed_count}")

if failures:
    print("\n--- Failed Courses Sample ---")
    for fail in failures[:15]:
        msg = f"Course: {fail['course']}"
        if fail['missing']:
            msg += f" | Missing: {', '.join(fail['missing'])}"
        if fail['too_small']:
            msg += f" | Too Small: {', '.join(fail['too_small'])}"
        print(msg)
