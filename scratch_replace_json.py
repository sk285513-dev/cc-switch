import os
import re

directory = r"C:\LocalAI_Workstation\scripts"
app_file = r"C:\LocalAI_Workstation\app.py"

def process_file(filepath, is_app=False):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # Skip if no json.load or json.loads
    if 'json.load(' not in content and 'json.loads(' not in content:
        return

    # Skip robust_json.py itself!
    if 'robust_json.py' in filepath:
        return

    print(f"Processing {filepath}...")
    
    # 1. Replace usages
    new_content = content.replace('json.load(', 'load_json_safe(')
    new_content = new_content.replace('json.loads(', 'parse_json_safe(')
    
    # 2. Add imports
    import_stmt = "from scripts.robust_json import load_json_safe, parse_json_safe" if is_app else "from robust_json import load_json_safe, parse_json_safe"
    
    # Check if already imported
    if "load_json_safe" not in content and "parse_json_safe" not in content:
        # Insert after import json, or at the top
        if 'import json' in new_content:
            new_content = new_content.replace('import json', f"import json\n{import_stmt}")
        else:
            new_content = f"{import_stmt}\n{new_content}"
    else:
        # if load_json_safe is already in there, make sure parse_json_safe is too if needed
        if 'parse_json_safe' not in content:
            new_content = new_content.replace('import load_json_safe', 'import load_json_safe, parse_json_safe')

    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(new_content)

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(".py"):
            process_file(os.path.join(root, file))
            
process_file(app_file, is_app=True)
print("Replacement completed.")
