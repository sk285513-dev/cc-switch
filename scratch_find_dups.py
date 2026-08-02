import json
from pathlib import Path
from collections import defaultdict

manifests_dir = Path('A:\\manifests')
processed_dir = Path('A:\\processed_md')

# 1. Gather all processed basenames
processed_stems = set()
if processed_dir.exists():
    for f in processed_dir.glob('*.md'):
        processed_stems.add(f.stem.replace('[', '').replace(']', '')) # basic normalization

# 2. Gather all tasks
task_files = list(manifests_dir.glob('task_*.json'))
source_to_tasks = defaultdict(list)

for tf in task_files:
    if '_chunks' in tf.name: continue
    try:
        with open(tf, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            src = data.get('source_path', '')
            status = data.get('status', '')
            if src:
                source_to_tasks[src].append({'task_id': data.get('task_id'), 'file': tf.name, 'status': status, 'source_name': data.get('source_name', '')})
    except:
        pass

# Find duplicates
unprocessed_dups = []
processed_reingested = []

for src, tasks in source_to_tasks.items():
    # Check if already processed
    # We check if any processed stem matches the source name
    is_processed = False
    if len(tasks) > 0:
        base_src_name = Path(src).stem
        for p_stem in processed_stems:
            if base_src_name in p_stem or p_stem in base_src_name:
                is_processed = True
                break
                
    if is_processed:
        processed_reingested.append({'source': src, 'tasks': [t['file'] for t in tasks]})
    elif len(tasks) > 1:
        unprocessed_dups.append({'source': src, 'tasks': [t['file'] for t in tasks]})

print(f'=== 分析報告 ===')
print(f'發現 {len(processed_reingested)} 個已被處理過 (A:\processed_md 已存在) 但仍被重複建立 task 的課程')
if processed_reingested:
    for item in processed_reingested[:10]:
        print(f" - {item['source']} -> {item['tasks']}")

print(f'\n發現 {len(unprocessed_dups)} 個尚未處理完成，但同一個影片被建立了多個 task 的課程')
if unprocessed_dups:
    for item in unprocessed_dups[:10]:
        print(f" - {item['source']} -> {item['tasks']}")

