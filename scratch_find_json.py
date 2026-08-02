import os
import re

directory = r"C:\LocalAI_Workstation\scripts"
app_file = r"C:\LocalAI_Workstation\app.py"

def find_json_loads(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if re.search(r'json\.load\(', line) or re.search(r'json\.loads\(.*read', line) or re.search(r'json\.loads\(.*open', line):
            print(f"{filepath}:{i+1}:{line.strip()}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".py"):
            find_json_loads(os.path.join(root, file))
            
find_json_loads(app_file)
