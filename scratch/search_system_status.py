with open('server.ts', 'r', encoding='utf-8') as f:
    content = f.read().splitlines()

# Let's search for "/api/system-status" definition in server.ts
matches = []
for i, line in enumerate(content):
    if '/api/system-status' in line:
        matches.append((i + 1, line))

print("Found system-status matches:")
for idx, line in matches:
    print(f"{idx}: {line}")
