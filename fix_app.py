import sys

file_path = r'c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\app.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_tab2 = False
in_idle = False

for i, line in enumerate(lines):
    if '# 1. 偵測與渲染自動復原/更新倒數畫面' in line:
        in_tab2 = True
    
    if in_tab2 and 'if st.session_state.get("recovery_active", False):' in line:
        pass  # Just keep it
        
    if in_tab2 and 'if IngestionBackgroundTask.status in ["running", "paused"]:' in line:
        line = line.replace('if IngestionBackgroundTask', 'elif IngestionBackgroundTask')
        
    if in_tab2 and 'if IngestionBackgroundTask.status in ["completed", "cancelled", "error"]:' in line:
        line = line.replace('if IngestionBackgroundTask', 'elif IngestionBackgroundTask')
        
    if in_tab2 and 'st.stop()' in line:
        line = line.replace('st.stop()', 'pass  # removed st.stop()')
        
    if in_tab2 and '# 4. 正常狀態下 (Idle) 的匯入 UI' in line:
        new_lines.append('    else:\n')
        in_idle = True
        
    if in_idle:
        if '# ==============================================================================' in line and 'TAB 2.5' in lines[i+1]:
            in_idle = False
            in_tab2 = False
        else:
            if line.strip() != '':
                line = '    ' + line
                
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Done!')
