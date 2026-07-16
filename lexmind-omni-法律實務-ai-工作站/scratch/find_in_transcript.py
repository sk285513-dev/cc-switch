import json

transcript_path = r"C:\Users\temp\.gemini\antigravity\brain\3c092ea4-56b0-4204-8f0d-93b116c3a423\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, 1):
        if "updateVaultItem" in line:
            # Parse json to print step index and type
            try:
                obj = json.loads(line)
                print(f"Line {line_num}: Step {obj.get('step_index')}, Type: {obj.get('type')}, Status: {obj.get('status')}")
            except Exception as e:
                print(f"Line {line_num}: {e}")
