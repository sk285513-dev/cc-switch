import json
import os

transcript_path = r"C:\Users\temp\.gemini\antigravity\brain\8e4b2906-ce3c-4c6e-9f84-8a6df4d0b737\.system_generated\logs\transcript_full.jsonl"
last_user_msg = ""
with open(transcript_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for line in reversed(lines):
    try:
        data = json.loads(line)
        if data.get("type") == "USER_INPUT":
            content = data.get("content", "")
            if "# [CRITICAL CROSS-FILE DEPENDENCY WARNING]" in content:
                last_user_msg = content
                break
    except:
        pass

out_dir = r"C:\LocalAI_Workstation\scripts_v6"
os.makedirs(out_dir, exist_ok=True)

parts = last_user_msg.split("# [CRITICAL CROSS-FILE DEPENDENCY WARNING]")
saved = []
for part in parts:
    if not part.strip(): continue
    content = "# [CRITICAL CROSS-FILE DEPENDENCY WARNING]" + part
    
    filename = None
    if "def log_stage" in content and "def get_engine_setting" in content:
        filename = "workflow_helper.py"
    elif "def process_active_tasks" in content and "def run_loop" in content:
        filename = "run_workflow.py"
    elif "def transcribe_chunk" in content and "def run_stt" in content:
        filename = "stt_runner.py"
        
    if filename:
        out_path = os.path.join(out_dir, filename)
        with open(out_path, "w", encoding="utf-8-sig") as f:
            f.write(content.strip() + "\n")
        saved.append(filename)

print("Saved files:", saved)
