import json
path = r'C:\Users\temp\.gemini\antigravity\brain\81e392d6-0b96-48b6-ad8a-585c30054413\.system_generated\logs\transcript_full.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        if 'sre_watchdog.py' in line and ('replace_file_content' in line or 'multi_replace_file_content' in line):
            data = json.loads(line)
            if 'tool_calls' in data:
                for tc in data['tool_calls']:
                    args = tc.get('arguments', {})
                    if 'sre_watchdog.py' in str(args):
                        print(f"Tool: {tc.get('name')}")
                        if 'Instruction' in args: print('Instruction:', args['Instruction'])
                        if 'TargetContent' in args: print('TargetContent:\n' + args['TargetContent'])
                        if 'ReplacementContent' in args: print('ReplacementContent:\n' + args['ReplacementContent'])
                        if 'ReplacementChunks' in args: 
                            for chunk in args['ReplacementChunks']:
                                print('ReplacementContent:\n' + chunk['ReplacementContent'])
                        print('-' * 40)
