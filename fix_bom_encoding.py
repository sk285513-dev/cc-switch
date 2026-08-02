import os
import re

TARGET_DIR = r"C:\LocalAI_Workstation"
EXCLUDE_DIRS = ['venv', '.git', '__pycache__', 'scratch', 'LexMind_Code_Backup_v5.0_Ultimate_20260725_221055']

# This regex matches open(..., 'r', ... encoding='utf-8-sig') or open(..., "r", ... encoding="utf-8-sig")
# It handles spaces, single/double quotes, and arguments in between.
# group 1: everything before encoding value
# group 2: the quote character (' or ")
pattern = re.compile(r"(open\([^)]+,\s*[\"']r[\"']\s*,.*?encoding=)([\"'])utf-8\2")

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except UnicodeDecodeError:
        return False
        
    new_content, count = pattern.subn(r'\g<1>\g<2>utf-8-sig\g<2>', content)
    
    if count > 0:
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(new_content)
        print(f"Updated {count} occurrence(s) in {filepath}")
        return True
    return False

def main():
    total_files = 0
    total_updated = 0
    for root, dirs, files in os.walk(TARGET_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                total_files += 1
                if process_file(filepath):
                    total_updated += 1
    
    print(f"Scanned {total_files} python files.")
    print(f"Successfully updated {total_updated} files with utf-8-sig for read operations.")

if __name__ == '__main__':
    main()
