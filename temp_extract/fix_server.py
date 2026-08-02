import re

with open(r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\server.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Wrong default port 11436 → 11434
original = content
content = content.replace('127.0.0.1:11436', '127.0.0.1:11434')

changes = (content != original)
print(f"Fix 1 (port 11436→11434): {'DONE' if changes else 'no change needed'}")

with open(r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\server.ts', 'w', encoding='utf-8') as f:
    f.write(content)

print("server.ts written.")
