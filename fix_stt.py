import os
path = r'C:\LocalAI_Workstation\scripts_v6\stt_runner.py'
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# 1. Add import
if 'from google.api_core.exceptions import ResourceExhausted' not in content:
    content = content.replace('import google.genai as genai\n', 'import google.genai as genai\nfrom google.api_core.exceptions import ResourceExhausted\n')

# 2. Replace gemini exception handling
old_gemini = '''if stt_engine == "gemini" and (
                "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            ):'''
new_gemini = '''if stt_engine == "gemini" and isinstance(e, ResourceExhausted):'''
content = content.replace(old_gemini, new_gemini)

# 3. Replace vertexai exception handling
old_vertex = '''elif stt_engine == "vertexai" and (
                "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            ):'''
new_vertex = '''elif stt_engine == "vertexai" and isinstance(e, ResourceExhausted):'''
content = content.replace(old_vertex, new_vertex)

with open(path, 'w', encoding='utf-8-sig') as f:
    f.write(content)
print('Updated stt_runner.py')
