import re

with open(r'C:\LocalAI_Workstation\scripts\run_workflow.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The pattern to remove
pattern = r"        # merge .*? formatter\n        if step_name == 'merge' and proc\.returncode == 0:\n            # .*? merge .*?\n            mf = Path\('A:/manifests'\) / f'\{task_id\}\.json'\n            try:\n                with open\(mf, encoding='utf-8'\) as f:\n                    m = json\.load\(f\)\n                if m\.get\('steps', \{\}\)\.get\('formatter'\) == 'pending':\n                    _spawn_step\(task_id, 'markdown_formatter\.py', 'formatter'\)\n            except Exception:\n                pass\n"

# Replace with regex
new_content = re.sub(pattern.replace("'", '"'), "", content, flags=re.DOTALL)

if new_content != content:
    with open(r'C:\LocalAI_Workstation\scripts\run_workflow.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Replaced successfully.')
else:
    print('Pattern not found!')
