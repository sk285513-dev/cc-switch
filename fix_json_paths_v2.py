import os
import re

manifest_dir = 'A:/manifests'
c = 0
for f in os.listdir(manifest_dir):
    if f.startswith('task_') and f.endswith('.json'):
        path = os.path.join(manifest_dir, f)
        try:
            with open(path, 'r', encoding='utf-8-sig', errors='replace') as file:
                content = file.read()
            
            # Find any string that looks like a Windows path (e.g. "C:\...", "A:/...", etc)
            # inside quotes and replace backslashes with forward slashes
            def replacer(match):
                # match.group(0) is the entire "C:\path..." including quotes
                val = match.group(1)
                # replace backslash with forward slash
                val = val.replace('\\', '/')
                return '"' + val + '"'
                
            new_content = re.sub(r'"([A-Za-z]:[\\/][^"]*)"', replacer, content)
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8-sig') as file:
                    file.write(new_content)
                c += 1
        except Exception as e:
            print(f"Failed {f}: {e}")
            
print(f"Fixed {c} files.")
