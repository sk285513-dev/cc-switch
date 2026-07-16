with open('src/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for "totalChunks" or "processedChunks" in App.tsx
matches = []
for i, line in enumerate(content.splitlines(), 1):
    if 'totalChunks' in line or 'processedChunks' in line or 'ingest_progress' in line:
        matches.append(f"{i}: {line}")

with open('scratch/progress_render_matches.txt', 'w', encoding='utf-8') as out:
    out.write('\n'.join(matches))
