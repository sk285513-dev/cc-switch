import os
import re

target_dir = r'C:\LocalAI_Workstation\scripts'

for root, _, files in os.walk(target_dir):
    for f in files:
        if f.endswith('.py') and f != 'robust_json.py':
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8-sig') as file:
                content = file.read()
            
            orig_content = content
            
            # Remove robust_json imports
            content = re.sub(r'from\s+scripts\.robust_json\s+import\s+.*', 'import json', content)
            content = re.sub(r'from\s+robust_json\s+import\s+.*', 'import json', content)
            content = re.sub(r'import\s+robust_json\n?', 'import json\n', content)
            
            # Replace method calls
            content = content.replace('load_json_safe(', 'json.load(')
            content = content.replace('parse_json_safe(', 'json.loads(')
            content = content.replace('save_json_safe(', 'json.dump(')
            
            # Replace encodings
            content = content.replace('utf-8-sig', 'utf-8')
            content = content.replace('utf8-sig', 'utf-8')
            
            if content != orig_content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f'Patched {filepath}')

# Also delete robust_json.py to be safe
try:
    os.remove(os.path.join(target_dir, 'robust_json.py'))
    print('Deleted robust_json.py')
except:
    pass
