import os
import shutil

manifest_dir = r'A:\manifests'
source_backups = [r'F:\chunks_backup', r'E:\chunks_backup']
dest_dir = r'A:\chunks'

import glob
chunk_files = glob.glob(os.path.join(manifest_dir, '*_chunks.json'))

restored_tasks = 0

for f in chunk_files:
    task_id = os.path.basename(f).replace('_chunks.json', '')
    
    # Check if the folder is missing in A:\chunks
    dest_task_dir = os.path.join(dest_dir, task_id)
    if not os.path.exists(dest_task_dir):
        # Look in backups
        for b_dir in source_backups:
            b_task_dir = os.path.join(b_dir, task_id)
            if os.path.exists(b_task_dir):
                print(f"Restoring {task_id} from {b_dir}...")
                try:
                    shutil.move(b_task_dir, dest_task_dir)
                    restored_tasks += 1
                except Exception as e:
                    print(f"Failed to move {task_id}: {e}")
                break

print(f"Restored {restored_tasks} tasks to A:\\chunks")
