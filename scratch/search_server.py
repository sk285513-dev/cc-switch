with open('server.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for getFilesRecursively function definition
matches = []
for i, line in enumerate(content.splitlines(), 1):
    if 'getFilesRecursively' in line:
        matches.append((i, line))

print(f"Found {len(matches)} matches in server.ts:")
for idx, line in matches:
    print(f"{idx}: {line}")
