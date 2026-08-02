try:
    import json
except ImportError:
    import json
import json
import glob
import os
from collections import Counter

manifest_dir = r'A:\manifests'
json_files = glob.glob(os.path.join(manifest_dir, '*.json'))
manifests = [f for f in json_files if not f.endswith('_chunks.json')]

status_counts = Counter()
for f in manifests:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            status_counts[data.get('status')] += 1
    except:
        pass

print("Manifest statuses:")
for status, count in status_counts.items():
    print(f"{status}: {count}")
