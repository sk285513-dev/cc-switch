import os
import json

filepath = r"C:\Users\temp\.gemini\antigravity\brain\3c092ea4-56b0-4204-8f0d-93b116c3a423\.system_generated\logs\transcript_full.jsonl"
output_file = r"C:\Users\temp\.gemini\antigravity\brain\3c092ea4-56b0-4204-8f0d-93b116c3a423\scratch\transcript_full_search.txt"

results = []
with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    for idx, line in enumerate(f, 1):
        try:
            data = json.loads(line)
            if data.get("step_index", 0) >= 210:
                results.append(f"Step {data.get('step_index')}: {data.get('type')} - {data.get('source')}")
                if "content" in data and data["content"]:
                    content = data["content"]
                    results.append(f"  Content: {content[:400]}")
        except Exception as e:
            results.append(f"Error parsing line {idx}: {e}")

with open(output_file, 'w', encoding='utf-8') as out:
    out.write("\n".join(results))

print("Done!")
