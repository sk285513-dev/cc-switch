import hashlib
import re

with open('C:/LocalAI_Workstation/progress_dashboard.py_Before_And_After.txt', 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'--- BEFORE \(from August 2nd/3rd Backup\) ---\r?\n(.*?)\r?\n--- AFTER', text, re.DOTALL)
if not m:
    print("Could not find BEFORE block")
    exit()

rw = m.group(1)
target = "A9E89539411600A7CC706905A9CE9CFFDA18E1B1278F8F693D87C88F9FDEC7B8".lower()

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
            exit()
print("No match found for BEFORE block.")
