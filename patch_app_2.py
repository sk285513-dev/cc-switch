import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Completely remove color overrides in the specific CSS blocks
code = re.sub(r'color:\s*#ffffff\s*!important;', '', code)
code = re.sub(r'color:\s*#e5e7eb\s*!important;', '', code)
code = re.sub(r'color:\s*#[0-9a-fA-F]+\s*!important;', '', code) # Strip any other hardcoded !important colors

# Ensure no empty !important rules left by my previous regex
code = code.replace(' !important;', '')

with open('C:\\LocalAI_Workstation\\app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("CSS colors stripped.")
