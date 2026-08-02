import json
import os
import glob
from pathlib import Path

brain_dir = r'C:\Users\temp\.gemini\antigravity\brain'
modifications = {}

for root, dirs, files in os.walk(brain_dir):
    if 'transcript.jsonl' in files:
        t_path = os.path.join(root, 'transcript.jsonl')
        conv_id = Path(root).parent.parent.name
        
        try:
            with open(t_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'write_to_file' in line or 'replace_file_content' in line:
                        data = json.loads(line)
                        if data.get('type') == 'PLANNER_RESPONSE' and 'tool_calls' in data:
                            for call in data['tool_calls']:
                                if call['name'] in ['default_api:write_to_file', 'default_api:replace_file_content', 'default_api:multi_replace_file_content']:
                                    args = call.get('arguments', {})
                                    target = args.get('TargetFile', '')
                                    desc = args.get('Description', args.get('Instruction', 'No description'))
                                    
                                    if target and 'LocalAI_Workstation' in target:
                                        fname = Path(target).name
                                        if fname not in modifications:
                                            modifications[fname] = set()
                                        modifications[fname].add(desc)
        except Exception as e:
            pass

print("=== Modified files in AI memory (across conversations) ===")
for fname, descs in sorted(modifications.items()):
    print(f"\n[ {fname} ]")
    for d in list(descs)[:10]:
        print(f"  - {d[:150]}")
