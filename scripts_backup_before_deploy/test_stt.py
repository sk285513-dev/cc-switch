try:
    import json
except ImportError:
    import json
import json
import glob
import os
import subprocess

manifest_dir = r'A:\manifests'
json_files = glob.glob(os.path.join(manifest_dir, '*.json'))
manifests = [f for f in json_files if not f.endswith('_chunks.json')]

for f in manifests:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if data.get('status') == 'chunked':
                task_id = os.path.basename(f).replace('.json', '')
                print(f"Testing task: {task_id}")
                subprocess.run(['python', r'C:\LocalAI_Workstation\scripts\stt_runner.py', task_id])
                break
    except:
        pass
