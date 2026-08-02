import re

with open('C:\\LocalAI_Workstation\\app.py', 'r', encoding='utf-8-sig') as f:
    content = f.read()

pattern = r'([ \t]*)st\.(success|warning|error|info)\((.*?)\)\n(?:[ \t]*time\.sleep\([^)]*\)\n)*[ \t]*st\.rerun\(\)'

def replacer(match):
    indent = match.group(1)
    msg_type = match.group(2)
    msg_content = match.group(3)
    return f'{indent}flash_and_rerun("{msg_type}", {msg_content})'

content, count = re.subn(pattern, replacer, content, flags=re.DOTALL)
print(f"Replaced {count} occurrences of ghost clicks with DOTALL.")

with open('C:\\LocalAI_Workstation\\app.py', 'w', encoding='utf-8-sig') as f:
    f.write(content)
