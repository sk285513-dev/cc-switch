import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Let's see if there is a 'st.button("🚀 啟動一鍵'
matches = re.findall(r'st\.button\("🚀 啟動一鍵.*?"', content)
print(f"Current button label in app.py: {matches}")
