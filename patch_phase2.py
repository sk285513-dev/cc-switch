import os

plan_path = r'C:\Users\temp\.gemini\antigravity\brain\090c45c8-c66c-443a-b0a9-ac871eca1570\implementation_plan.md'

with open(plan_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: stt_runner.py KeyError on "steps" when completing
text = text.replace(
    '''        manifest["status"] = "transcribed"
        manifest["steps"]["stt"] = "completed"''',
    '''        manifest["status"] = "transcribed"
        manifest.setdefault("steps", {})
        manifest["steps"]["stt"] = "completed"'''
)

# Fix 2: stt_runner.py KeyError on "steps" when pending
text = text.replace(
    '''        manifest["status"] = "chunked"
        manifest["steps"]["stt"] = "pending"''',
    '''        manifest["status"] = "chunked"
        manifest.setdefault("steps", {})
        manifest["steps"]["stt"] = "pending"'''
)

# Fix 3: auto_healer.py Emoji violation
text = text.replace(
    '''       title = "🚨 [AutoHealer 崩潰升級] 需要長官介入"''',
    '''       title = "[ALERT] [AutoHealer 崩潰升級] 需要長官介入"'''
)

with open(plan_path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Phase 2 code patched successfully with Subagent fixes.')
