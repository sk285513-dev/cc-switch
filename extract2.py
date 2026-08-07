import json
import os

transcript_path = r"C:\Users\temp\.gemini\antigravity\brain\8e4b2906-ce3c-4c6e-9f84-8a6df4d0b737\.system_generated\logs\transcript_full.jsonl"
last_user_msg = ""

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in reversed(f.readlines()):
        try:
            data = json.loads(line)
            if data.get("type") == "USER_INPUT":
                last_user_msg = data.get("content", "")
                if "# [CRITICAL CROSS-FILE DEPENDENCY WARNING]" in last_user_msg:
                    break
        except:
            pass

parts = last_user_msg.split("# [CRITICAL CROSS-FILE DEPENDENCY WARNING]")
out_dir = r"C:\LocalAI_Workstation\scripts_v6"
os.makedirs(out_dir, exist_ok=True)

saved_files = []
for part in parts:
    if not part.strip():
        continue
    content = "# [CRITICAL CROSS-FILE DEPENDENCY WARNING]" + part
    
    filename = None
    if "Shared State: task manifests (*.json), chunks manifests (*_chunks.json)" in content:
        filename = "manifest_manager.py"
    elif "Shared State: config.yaml, api_keys_state.json, config/quota_state.json, logs" in content:
        filename = "workflow_helper.py"
    elif "Upstream: LexMind_V6_沙盒驗證版.ps1" in content:
        filename = "run_workflow.py"
    elif "Upstream: run_workflow.py" in content and "Downstream: quota_manager.py, Gemini API / Vertex AI" in content:
        filename = "stt_runner.py"
        
    if filename:
        out_path = os.path.join(out_dir, filename)
        with open(out_path, "w", encoding="utf-8-sig") as f:
            f.write(content.strip() + "\n")
        saved_files.append(filename)

print("Saved files:", saved_files)
