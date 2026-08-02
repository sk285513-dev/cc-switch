import os
import re

manifest_dir = 'A:/manifests'
c = 0
for f in os.listdir(manifest_dir):
    if f.startswith('task_') and f.endswith('.json'):
        path = os.path.join(manifest_dir, f)
        try:
            with open(path, 'r', encoding='utf-8-sig', errors='replace') as file:
                lines = file.readlines()
            
            changed = False
            new_lines = []
            for line in lines:
                if '"source_path"' in line or '"source_name"' in line or '"video_path"' in line:
                    # just replace all backslashes with forward slashes for the whole line, it's safe for these keys
                    new_line = line.replace('\\', '/')
                    if new_line != line:
                        changed = True
                        line = new_line
                new_lines.append(line)
            
            if changed:
                with open(path, 'w', encoding='utf-8-sig') as file:
                    file.writelines(new_lines)
                c += 1
        except Exception as e:
            print(f"Failed {f}: {e}")
            
print(f"Fixed {c} files.")
