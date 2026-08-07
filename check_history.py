import json
path = r'C:\Users\temp\.gemini\antigravity\brain\81e392d6-0b96-48b6-ad8a-585c30054413\.system_generated\logs\transcript.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        if 'sre_watchdog' in line:
            data = json.loads(line)
            print(f"Step {data.get('step_index')}: {data.get('type')}")
            if 'tool_calls' in data:
                for tc in data['tool_calls']:
                    print(f"Tool: {tc.get('name')}")
                    args = tc.get('arguments', {})
                    if 'Instruction' in args: print('Instruction:', args['Instruction'])
                    if 'ReplacementContent' in args: print('ReplacementContent:', args['ReplacementContent'])
                    if 'CommandLine' in args: print('CommandLine:', args['CommandLine'])
            print('-' * 40)
