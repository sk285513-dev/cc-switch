# -*- coding: utf-8 -*-
import os
import shutil

task_id = "task_20260727_112835_5881"
backup_dir = r"A:\failed_chunks_backup\[憲法霖洄_ch15]"
chunks_dir = rf"A:\chunks\{task_id}"

if not os.path.exists(chunks_dir):
    os.makedirs(chunks_dir)

print("Copying files...")
count = 0
if os.path.exists(backup_dir):
    for f in os.listdir(backup_dir):
        src = os.path.join(backup_dir, f)
        dst = os.path.join(chunks_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            count += 1
    print(f"Copied {count} files.")
else:
    print(f"Directory not found: {backup_dir}")
