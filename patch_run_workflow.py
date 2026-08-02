import os
import codecs

path = r'C:\LocalAI_Workstation\scripts_v6\run_workflow.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Add ENTERPRISE_MODE globally at the top
enterprise_code = "\nENTERPRISE_MODE = os.environ.get('LEXMIND_ENTERPRISE', '0') == '1'\n"
if "ENTERPRISE_MODE =" not in content:
    content = content.replace('import random\n', 'import random\n' + enterprise_code)

# Replace the condition in run_loop
old_cond = '_is_stt_phase = _now_hour >= 16 or _now_hour < 8   # 16:00-08:00 台灣時間走 STT Phase B'
new_cond = '_is_stt_phase = True if ENTERPRISE_MODE else (_now_hour >= 16 or _now_hour < 8)'
if old_cond in content:
    content = content.replace(old_cond, new_cond)

with codecs.open(path, 'w', 'utf-8-sig') as f:
    f.write(content)

print("Done")
