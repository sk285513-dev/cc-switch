import glob
import re
import os

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple replace ignoring \r vs \n
    content_normalized = content.replace('\r\n', '\n')
    
    old_str = '''if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')'''
    
    new_str = '''try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass'''

    if old_str in content_normalized:
        new_content = content_normalized.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {filepath}')
    elif 'sys.stdout.reconfigure' in content and 'try:' not in content[:300]:
        print(f'Could not replace in {filepath}, manual check needed!')

for f in glob.glob('scripts/*.py'):
    fix_file(f)
