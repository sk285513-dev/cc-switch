import json
import os
from pathlib import Path
from datetime import datetime

brain_dir = Path(r'C:\Users\temp\.gemini\antigravity\brain')

files_modified = {}
for root, dirs, files in os.walk(brain_dir):
    if 'transcript.jsonl' in files:
        t_path = os.path.join(root, 'transcript.jsonl')
        try:
            with open(t_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get('type') == 'PLANNER_RESPONSE' and 'tool_calls' in data:
                        for call in data['tool_calls']:
                            if call.get('name') in ['default_api:write_to_file', 'default_api:replace_file_content', 'default_api:multi_replace_file_content']:
                                args = call.get('arguments', {})
                                target = args.get('TargetFile', '')
                                desc = args.get('Description', args.get('Instruction', ''))
                                
                                # Extract timestamp if available, rough heuristic
                                timestamp = data.get('timestamp', '')
                                
                                if target and 'C:\\LocalAI_Workstation' in target:
                                    if target not in files_modified:
                                        files_modified[target] = []
                                    # Avoid duplicates
                                    if desc not in files_modified[target]:
                                        files_modified[target].append(desc)
        except Exception as e:
            pass

for k, v in files_modified.items():
    print(f"File: {k}")
    for i, desc in enumerate(v):
        if i > 5:
            print("  ... and more")
            break
        print(f"  - {desc}")
