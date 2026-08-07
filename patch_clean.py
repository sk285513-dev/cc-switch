import re

file_path = r'C:\LocalAI_Workstation\app_v6_clean.py'
with open(file_path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# 1. Update JSON paths to mock test dir
content = content.replace(r'C:\LocalAI_Workstation\chosen_paths_buffer.json', r'A:\manifests_v6_test\chosen_paths_buffer.json')
content = content.replace(r'C:\LocalAI_Workstation\ingested_history.json', r'A:\manifests_v6_test\ingested_history.json')
content = content.replace(r'C:\LocalAI_Workstation\ingest_state.json', r'A:\manifests_v6_test\ingest_state.json')
content = content.replace(r'C:\LocalAI_Workstation\subject_intelligence.json', r'A:\manifests_v6_test\subject_intelligence.json')

# 2. Strip run_background_ingestion entirely
# Find the start of the function
start_idx = content.find('def run_background_ingestion(')
if start_idx != -1:
    # Find the next top-level def or class to determine where it ends
    next_def_idx = content.find('\ndef ', start_idx + 10)
    next_class_idx = content.find('\nclass ', start_idx + 10)
    
    # Actually, we know this is likely the last function or we can just cut till the end if it's the end, 
    # but let's just use regex to chop everything from def run_background_ingestion to the end of the file 
    # since it's typically the background worker at the bottom.
    content = content[:start_idx]

with open(file_path, 'w', encoding='utf-8-sig') as f:
    f.write(content)

print('app_v6_clean.py successfully patched.')
