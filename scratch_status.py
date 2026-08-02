import json
from pathlib import Path
from collections import defaultdict

manifests_dir = Path('A:\\manifests')
processed_dir = Path('A:\\processed_md')

processed_stems = set()
if processed_dir.exists():
    for f in processed_dir.glob('*.md'):
        processed_stems.add(f.stem.replace('[', '').replace(']', '')) 

task_files = list(manifests_dir.glob('task_*.json'))

status_counts = defaultdict(int)
for tf in task_files:
    if '_chunks' in tf.name: continue
    try:
        with open(tf, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            src = data.get('source_path', '')
            status = data.get('status', '')
            
            base_src_name = Path(src).stem
            is_processed = False
            for p_stem in processed_stems:
                if base_src_name in p_stem or p_stem in base_src_name:
                    is_processed = True
                    break
            
            if is_processed:
                status_counts[status] += 1
    except:
        pass

print("Status of the 263 processed files' tasks in A:\manifests:")
for st, cnt in status_counts.items():
    print(f"{st}: {cnt}")
