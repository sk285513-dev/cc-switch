try:
    import json
except ImportError:
    import json
import json
import os
import re

# 1. Read the 88 courses list
with open(r'C:\LocalAI_Workstation\old_engine_courses.json', 'r', encoding='utf-8') as f:
    courses_88 = json.load(f)

# Extract basenames of the 88 courses for exact matching
basenames_88 = {c['course_name'] for c in courses_88}

# 2. Read the full 520 courses list from the previous agent's markdown
# The markdown has lines like: | 1 | [民法_ch24]_預約 24 2024-09-04 13-12-00-432 | ...
full_md_path = r'C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md'

whitelist_432 = []
if os.path.exists(full_md_path):
    with open(full_md_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'\|\s*\d+\s*\|\s*([^|]+?)\s*\|', line)
            if match:
                course_name = match.group(1).strip()
                if course_name not in basenames_88 and course_name != 'Course Name':
                    whitelist_432.append(course_name)

# Alternatively, we can also scan A:\processed_md directly for any .md files 
# that are not in the 88 list. Wait, A:\processed_md might have been polluted?
# Let's check what's actually in A:\processed_md now that ends with .md
actual_processed = []
for f in os.listdir(r'A:\processed_md'):
    if f.endswith('.md'):
        course_name = f[:-3]
        if course_name not in basenames_88:
            actual_processed.append(course_name)

print(f"Total 88 courses: {len(basenames_88)}")
print(f"Total 432 courses from MD: {len(whitelist_432)}")
print(f"Total valid courses currently in A:\\processed_md (excluding 88): {len(actual_processed)}")

# Save to whitelist
with open(r'C:\LocalAI_Workstation\whitelist_432.json', 'w', encoding='utf-8') as f:
    json.dump(actual_processed, f, ensure_ascii=False, indent=2)

print('Saved whitelist_432.json')
