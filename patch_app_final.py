with open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(len(lines)):
    if 'if IngestionBackgroundTask.status in ["running", "paused"]:' in lines[i]:
        lines[i] = lines[i].replace("if", "elif", 1)
    if 'if IngestionBackgroundTask.status in ["completed", "cancelled", "error"]:' in lines[i]:
        lines[i] = lines[i].replace("if", "elif", 1)
    if 'st.stop()' in lines[i] and (1500 < i < 1700):
        lines[i] = "        pass\n"

start = -1
end = -1
for i in range(len(lines)):
    if '# 4. 正常狀態下 (Idle) 的匯入 UI' in lines[i]:
        start = i
        break
for i in range(start, len(lines)):
    if 'TAB 2.5: 📂 法律個案管理區' in lines[i]:
        end = i - 1
        break

lines.insert(start, "    else:\n")
start += 1
end += 1

for i in range(start, end):
    if lines[i].strip() and not lines[i].startswith("        # "):
        # carefully add 4 spaces
        lines[i] = "    " + lines[i]

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
