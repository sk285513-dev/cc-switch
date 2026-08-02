with open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "st.stop()" in line and i > 1815 and i < 1830:
        lines[i] = "            pass\n"
        print("Found st.stop at", i)

start_idx = -1
for i, line in enumerate(lines):
    if "# 4. 正常狀態下 (Idle) 的匯入 UI" in line:
        start_idx = i
        break

end_idx = -1
for i in range(start_idx, len(lines)):
    if "TAB 2.5: 📂 法律個案管理區" in line:
        end_idx = i - 1
        break

print("Start at", start_idx, "End at", end_idx)

lines.insert(start_idx, "        elif IngestionBackgroundTask.status not in ['completed', 'cancelled', 'error']:\n")
start_idx += 1
end_idx += 1

for i in range(start_idx, end_idx):
    if lines[i].strip() == "":
        continue
    lines[i] = "    " + lines[i]

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
