import hashlib
import re

with open('C:/LocalAI_Workstation/LexMind_V6_Source_Code_Mirror.txt', 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'FILE: run_workflow\.py\r?\n=+\r?\n(.*?)=========================================\nFILE:', text, re.DOTALL)
if not m:
    print("Could not find run_workflow.py block")
    exit()

rw = m.group(1)
target = "24b674415fae685a1378f44b96e48c1d062e63c907b0e97df09dd6bfceb01c1d"

variants = [
    rw,
    rw.strip(),
    rw.replace('\r\n', '\n'),
    rw.replace('\r\n', '\n').strip(),
    rw.strip() + '\n',
    rw.strip() + '\r\n',
    rw.replace('\r\n', '\n').strip() + '\n',
]

print(f"Target: {target}")
for i, v in enumerate(variants):
    for bom in [False, True]:
        b = v.encode('utf-8-sig') if bom else v.encode('utf-8')
        h = hashlib.sha256(b).hexdigest()
        if h == target:
            print(f"Match found! Variant {i}, BOM: {bom}")
            with open('C:/LocalAI_Workstation/run_workflow_golden.py', 'wb') as out:
                out.write(b)
            exit()
print("No match found.")
