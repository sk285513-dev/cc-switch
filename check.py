lines = open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8').readlines()
for i, line in enumerate(lines):
    if "TAB 2.5: 📂 法律個案管理區" in line:
        print("Found at", i)
