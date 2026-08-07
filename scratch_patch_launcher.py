import re
with open('C:/LocalAI_Workstation/LexMind_一鍵正式啟動.ps1', 'r', encoding='utf-8') as f:
    text = f.read()

new_text = re.sub(r'Start-Process "C:\\Python312\\pythonw\.exe" \s*-ArgumentList "scripts_v6\\(run_workflow\.py|watchdog_monitor\.py|auto_healer\.py|sre_watchdog\.py|.*?)" ',
                  lambda m: m.group(0).replace('pythonw.exe', 'python.exe'), text, flags=re.MULTILINE)

# Just broadly replace pythonw.exe with python.exe for the background processes that have RedirectStandardOutput
new_text = text.replace('Start-Process "C:\\Python312\\pythonw.exe"', 'Start-Process "C:\\Python312\\python.exe"')

with open('C:/LocalAI_Workstation/LexMind_一鍵正式啟動.ps1', 'w', encoding='utf-8-sig', newline='\n') as f:
    f.write(new_text)

print("Patched LexMind_一鍵正式啟動.ps1")
