with open('src/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for batchIngestFiles in App.tsx
matches = []
for i, line in enumerate(content.splitlines(), 1):
    if 'batchIngestFiles' in line:
        matches.append((i, line))

print(f"Found {len(matches)} matches:")
for idx, line in matches:
    print(f"{idx}: {line}")
