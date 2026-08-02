try:
    import json
except ImportError:
    import json
import json
import glob
import os

manifest_dir = r'A:\manifests'
chunk_files = glob.glob(os.path.join(manifest_dir, '*_chunks.json'))

poisoned_chunks = 0
poisoned_tasks = 0

for f in chunk_files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            chunks = json.load(file)
            task_poisoned = False
            for chunk in chunks:
                if chunk.get('status') in ['completed', 'stt_done'] and not chunk.get('text'):
                    poisoned_chunks += 1
                    task_poisoned = True
            if task_poisoned:
                poisoned_tasks += 1
    except:
        pass

print(f"Total chunks files: {len(chunk_files)}")
print(f"Tasks with poisoned chunks: {poisoned_tasks}")
print(f"Total poisoned chunks (completed but no text): {poisoned_chunks}")
