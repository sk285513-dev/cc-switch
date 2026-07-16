with open('src/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for "rawRemaining" or "smoothRemaining" in App.tsx
matches = []
for i, line in enumerate(content.splitlines(), 1):
    if 'rawRemaining' in line or 'smoothRemaining' in line or 'Math.max(5' in line:
        matches.append(f"{i}: {line}")

for m in matches:
    print(m)
