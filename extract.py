import json
import os
import re

transcript_path = r"C:\Users\temp\.gemini\antigravity\brain\8e4b2906-ce3c-4c6e-9f84-8a6df4d0b737\.system_generated\logs\transcript_full.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

last_user_msg = ""
for line in reversed(lines):
    try:
        data = json.loads(line)
        if data.get("type") == "USER_INPUT":
            last_user_msg = data.get("content", "")
            break
    except:
        pass

# Split by the header
parts = last_user_msg.split("# [CRITICAL CROSS-FILE DEPENDENCY WARNING]")

out_dir = r"C:\LocalAI_Workstation\scripts_v6"
os.makedirs(out_dir, exist_ok=True)

for part in parts:
    if not part.strip():
        continue
    content = "# [CRITICAL CROSS-FILE DEPENDENCY WARNING]" + part
    
    # Auto-detect filename based on the upstream/downstream comments
    if "Shared State: task manifests (*.json), chunks manifests (*_chunks.json)" in content:
        filename = "manifest_manager.py"
    elif "Shared State: config.yaml, api_keys_state.json, config/quota_state.json, logs" in content:
        filename = "workflow_helper.py"
    elif "Upstream: LexMind_V6_沙盒驗證版.ps1" in content:
        filename = "run_workflow.py"
    elif "Upstream: run_workflow.py" in content and "Downstream: quota_manager.py, Gemini API / Vertex AI" in content:
        filename = "stt_runner.py"
    else:
        continue
        
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write(content.strip() + "\n")
    print(f"Saved {filename}")

