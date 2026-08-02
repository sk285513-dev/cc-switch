lines = open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8').readlines()
for i in range(len(lines)):
    if "elif IngestionBackgroundTask.status not in ['completed'" in lines[i]:
        start = i + 1
    elif "TAB 2.5: 📂 法律個案管理區" in lines[i]:
        end = i - 1
        break

for i in range(start, end):
    if lines[i].strip() and not lines[i].startswith("        "):
        lines[i] = "    " + lines[i]

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8-sig') as f:
    f.writelines(lines)
