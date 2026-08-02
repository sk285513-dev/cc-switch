import glob

old_str = '''try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass'''

new_str = '''try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass'''

for f in glob.glob('C:/LocalAI_Workstation/scripts/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if 'sys.stdout.reconfigure' in content and 'try:' not in content[:300]:
        content = content.replace(old_str, new_str)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
print('Done batch replacing.')
