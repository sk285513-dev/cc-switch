import sys

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'with st.spinner' in line and '\\n' in line:
        lines[i] = line.replace('\\n', '\n')

with open('C:\\LocalAI_Workstation\\app.py', 'w', encoding='utf-8-sig') as f:
    f.writelines(lines)

print("Fixed syntax error.")
