import re

with open(r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\server.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace qwen3.5:9b and deepseek-r1:32b with ornith:9b-bf16
new_content = re.sub(r'\"qwen3\.5:9b\"', '\"ornith:9b-bf16\"', content)
new_content = re.sub(r'\"deepseek-r1:32b\"', '\"ornith:9b-bf16\"', new_content)

if new_content != content:
    with open(r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\server.ts', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Replaced successfully.')
else:
    print('No changes needed.')
