with open('server.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for "currentIngestProgress" or "totalChunks" inside server.ts stdout parsing
matches = []
for i, line in enumerate(content.splitlines(), 1):
    if 'currentIngestProgress' in line or 'totalChunks' in line or 'processedChunks' in line:
        matches.append(f"{i}: {line}")

with open('scratch/telemetry_parsing_matches.txt', 'w', encoding='utf-8') as out:
    out.write('\n'.join(matches))
