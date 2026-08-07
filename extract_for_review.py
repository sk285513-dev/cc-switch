import json
import os

transcript_path = r"C:\Users\temp\.gemini\antigravity\brain\8e4b2906-ce3c-4c6e-9f84-8a6df4d0b737\.system_generated\logs\transcript_full.jsonl"
blocks = []
with open(transcript_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in reversed(lines):
    try:
        data = json.loads(line)
        if data.get("type") == "USER_INPUT":
            content = data.get("content", "")
            if "# [CRITICAL CROSS-FILE DEPENDENCY WARNING]" in content:
                blocks.append(content)
                if len(blocks) >= 2: # user pasted code in turn N-2 and turn N-1. Turn N-1 is the latest.
                    break
    except:
        pass

# The most recent one is blocks[0] (which is Turn N-1)
# It contains the 3 files with log_stage
out_path = r"C:\LocalAI_Workstation\review_target_v2.py"
with open(out_path, "w", encoding="utf-8-sig") as f:
    f.write(blocks[0].strip() + "\n")
print("Saved review target to", out_path)
