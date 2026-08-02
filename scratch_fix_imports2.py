import os
import glob

# Search in scripts folder and app.py
targets = glob.glob(r"C:\LocalAI_Workstation\scripts\**\*.py", recursive=True) + [r"C:\LocalAI_Workstation\app.py"]

old_import = "from robust_json import load_json_safe, parse_json_safe\n"
new_import = """try:
    from robust_json import load_json_safe, parse_json_safe
except ImportError:
    from scripts.robust_json import load_json_safe, parse_json_safe
"""

for file in targets:
    try:
        with open(file, "r", encoding="utf-8-sig") as f:
            content = f.read()
            
        if old_import in content:
            new_content = content.replace(old_import, new_import)
            with open(file, "w", encoding="utf-8-sig") as f:
                f.write(new_content)
            print(f"Fixed {file}")
    except Exception as e:
        pass
