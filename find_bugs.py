import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Match st.success/warning/error/info followed optionally by time.sleep and then st.rerun
pattern = r'(st\.(?:success|warning|error|info)\(.*?\))\s*(?:time\.sleep\([^)]*\)\s*)?st\.rerun\(\)'
matches = re.findall(pattern, content, re.DOTALL)
print(f"Found {len(matches)} occurrences of flash message bug pattern.")
