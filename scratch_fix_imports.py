import os
import re

directory = r"C:\LocalAI_Workstation\scripts"
app_file = r"C:\LocalAI_Workstation\app.py"

def fix_imports(filepath, is_app=False):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
        
    has_bad_import = False
    needs_import = False
    new_lines = []
    
    for line in lines:
        if 'load_json_safe' in line or 'parse_json_safe' in line:
            needs_import = True
            
        # Check if it's the badly inserted import (starts with from without indentation, but we just remove all of them and re-add at top)
        if re.match(r'^\s*from (scripts\.)?robust_json import load_json_safe.*', line):
            has_bad_import = True
            continue
            
        new_lines.append(line)
        
    if not needs_import:
        return
        
    # We stripped all imports for robust_json. Now add it at the top (after coding / shebang)
    import_stmt = "from scripts.robust_json import load_json_safe, parse_json_safe\n" if is_app else "from robust_json import load_json_safe, parse_json_safe\n"
    
    insert_idx = 0
    for i, line in enumerate(new_lines):
        if line.startswith('#!') or line.startswith('# -*-'):
            insert_idx = i + 1
        elif line.strip() == '' or line.startswith('#'):
            pass
        else:
            break
            
    # Also we don't want to insert if the file is empty
    if new_lines:
        new_lines.insert(insert_idx, import_stmt)
    else:
        new_lines = [import_stmt]
        
    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.writelines(new_lines)
        
    if has_bad_import:
        print(f"Fixed {filepath}")

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".py"):
            fix_imports(os.path.join(root, file))
            
fix_imports(app_file, is_app=True)
