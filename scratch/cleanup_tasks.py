import json
import os
from pathlib import Path

MANIFESTS = Path('A:/manifests')
VALID_SUBJECTS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法"]

deleted_count = 0
for mf in MANIFESTS.glob("task_*.json"):
    if "_chunks" in mf.name:
        continue
    try:
        data = json.loads(mf.read_text(encoding='utf-8'))
        source_path = data.get('source_path', '')
        
        # Check if any valid subject is in the source path
        is_valid = any(subj in source_path for subj in VALID_SUBJECTS)
        
        # Or more accurately, check if any INVALID subjects are in it that aren't also matching a valid one
        # But wait, it's easier to just match exactly the valid list.
        
        # If it doesn't match any valid subject, delete it.
        if not is_valid:
            print(f"Deleting invalid task: {source_path}")
            os.remove(mf)
            # also delete the chunks manifest if it exists
            chunk_mf = str(mf).replace('.json', '_chunks.json')
            if os.path.exists(chunk_mf):
                os.remove(chunk_mf)
            deleted_count += 1
    except Exception as e:
        print(f"Error reading {mf}: {e}")

print(f"\nTotal invalid tasks deleted: {deleted_count}")
