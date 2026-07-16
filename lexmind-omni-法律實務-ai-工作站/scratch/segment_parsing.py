with open('server.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for "區段" in server.ts
matches = []
for i, line in enumerate(content.splitlines(), 1):
    if '區段' in line or '進度' in line:
        matches.append(f"{i}: {line}")

with open('scratch/segment_parsing_matches.txt', 'w', encoding='utf-8') as out:
    out.write('\n'.join(matches))
