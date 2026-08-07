import re

with open('C:/LocalAI_Workstation/LexMind_V6_Source_Code_Mirror.txt', 'r', encoding='utf-8') as f:
    text = f.read()

files = [
    'run_workflow.py',
    'stt_runner.py',
    'manifest_manager.py',
    'workflow_helper.py'
]

for filename in files:
    m = re.search(f'FILE: {filename}\r?\n=+\r?\n(.*?)=========================================\nFILE:', text, re.DOTALL)
    if not m:
        # For the last file, the ending delimiter might just be the end of the file or another separator
        m = re.search(f'FILE: {filename}\r?\n=+\r?\n(.*)', text, re.DOTALL)
    
    if m:
        content = m.group(1).replace('\r\n', '\n').strip() + '\n'
        out_path = f'C:/LocalAI_Workstation/scripts_v6/{filename}'
        # The run_workflow_golden.py we tested required BOM to match the fingerprint perfectly
        with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as out:
            out.write(content)
        print(f"Extracted {filename}")
    else:
        print(f"Failed to find {filename}")
