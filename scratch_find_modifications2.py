import json
import os
from pathlib import Path

brain_dir = Path(r'C:\Users\temp\.gemini\antigravity\brain')

print("Looking for modified files in transcripts...")
for root, dirs, files in os.walk(brain_dir):
    if 'transcript.jsonl' in files:
        t_path = os.path.join(root, 'transcript.jsonl')
        try:
            with open(t_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'replace_file_content' in line or 'write_to_file' in line:
                        data = json.loads(line)
                        if data.get('type') == 'PLANNER_RESPONSE' and 'tool_calls' in data:
                            for call in data['tool_calls']:
                                if call.get('name') in ['default_api:write_to_file', 'default_api:replace_file_content', 'default_api:multi_replace_file_content']:
                                    args = call.get('arguments', {})
                                    target = args.get('TargetFile', '')
                                    if 'LocalAI_Workstation' in target:
                                        # Use the conversation folder name (which is the parent of .system_generated)
                                        # root is like brain\<id>\.system_generated\logs
                                        conv_id = Path(root).parent.parent.name
                                        print(f"{conv_id} modified {Path(target).name}")
        except Exception as e:
            pass
