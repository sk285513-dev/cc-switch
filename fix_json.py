import os
import re

manifest_dir = 'A:/manifests'
c = 0
for f in os.listdir(manifest_dir):
    if f.startswith('task_') and f.endswith('.json'):
        path = os.path.join(manifest_dir, f)
        try:
            with open(path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
            # Replace single backslashes with double backslashes, but avoid doubling already doubled ones
            # Also avoiding \" and \n etc if they exist, but path should just be fixed.
            # Actually, simplest is to use ast.literal_eval on the raw string if we can, 
            # but regex: replace \ with \\ unless it's followed by " or \ 
            new_content = re.sub(r'\\([^\\"])', r'\\\\\1', content)
            
            # Write it back if changed
            if new_content != content:
                with open(path, 'w', encoding='utf-8-sig') as file:
                    file.write(new_content)
                c += 1
        except Exception as e:
            print(f"Failed {f}: {e}")
            
print(f"Fixed {c} files.")
