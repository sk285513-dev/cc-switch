lines = open('C:/LocalAI_Workstation/verify_settings.py', 'r', encoding='utf-8').readlines()
for i, line in enumerate(lines):
    if 'await tabs_locator.wait_for(state="visible", timeout=10000)' in line:
        lines[i] = '    await tabs_locator.wait_for(state="visible", timeout=60000)\n'
    elif 'await page.wait_for_selector(' in line:
        lines[i] = line.replace(')', ', timeout=60000)')

with open('C:/LocalAI_Workstation/verify_settings.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
