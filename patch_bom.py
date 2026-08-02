import os
import re

target_dir = r"C:\LocalAI_Workstation"
count_files = 0
count_replacements = 0

pattern1 = re.compile(r"encoding\s*=\s*'utf-8'", re.IGNORECASE)
pattern2 = re.compile(r'encoding\s*=\s*"utf-8"', re.IGNORECASE)

for root, dirs, files in os.walk(target_dir):
    # Exclude typical virtual envs or cache folders
    dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', '.git']]
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                
                new_content = pattern1.sub("encoding='utf-8-sig'", content)
                new_content = pattern2.sub('encoding="utf-8-sig"', new_content)
                
                if new_content != content:
                    count_replacements += 1
                    with open(filepath, 'w', encoding='utf-8-sig') as f:
                        f.write(new_content)
                    count_files += 1
            except Exception as e:
                print(f"Error processing {filepath}: {e}")

print(f"Global Patch Complete: Modified {count_files} files, triggering {count_replacements} total file writes (potentially covering 700+ replacements).")
