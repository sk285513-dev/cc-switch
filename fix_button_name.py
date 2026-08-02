import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8-sig') as f:
    content = f.read()

content = content.replace('啟動一鍵批次研讀與消化', '啟動一鍵批量研讀與消化')

with open('C:\\LocalAI_Workstation\\app.py', 'w', encoding='utf-8-sig') as f:
    f.write(content)
