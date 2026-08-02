lines = open('C:/LocalAI_Workstation/app.py', 'r', encoding='utf-8').readlines()
new_lines = []
for line in lines:
    if 'def load_from_disk(cls):' in line:
        new_lines.append(line)
        new_lines.append('        if not os.path.exists(cls.STATE_FILE):\n')
        new_lines.append('            return False\n')
        new_lines.append('        try:\n')
        new_lines.append('            with open(cls.STATE_FILE, "r", encoding="utf-8") as f:\n')
        new_lines.append('                state = json.load(f)\n')
        new_lines.append('            cls.status = state.get("status", "idle")\n')
        new_lines.append('            cls.total_files = state.get("total_files", 0)\n')
        new_lines.append('            cls.processed_count = state.get("processed_count", 0)\n')
        new_lines.append('            cls.current_file = state.get("current_file", "")\n')
        new_lines.append('            cls.current_action = state.get("current_action", "")\n')
        new_lines.append('            cls.logs = state.get("logs", [])\n')
        new_lines.append('            cls.generated_transcripts = state.get("generated_transcripts", [])\n')
        new_lines.append('            cls.generated_visual_notes = state.get("generated_visual_notes", [])\n')
        new_lines.append('            cls.cancel_requested = state.get("cancel_requested", False)\n')
        new_lines.append('            cls.pause_requested = state.get("pause_requested", False)\n')
        new_lines.append('            cls.error_message = state.get("error_message", "")\n')
        new_lines.append('            cls.valid_files_info = state.get("valid_files_info", [])\n')
        new_lines.append('            cls.transcripts_dir = state.get("transcripts_dir", "")\n')
        new_lines.append('            cls.class_name = state.get("class_name", "")\n')
        new_lines.append('            cls.lesson_name = state.get("lesson_name", "")\n')
        new_lines.append('            cls.last_heartbeat = state.get("last_heartbeat", 0.0)\n')
        new_lines.append('            return True\n')
        new_lines.append('        except Exception as e:\n')
        new_lines.append('            import sys\n')
        new_lines.append('            if sys.stdout and not getattr(sys.stdout, "closed", False):\n')
        new_lines.append('                print(f"[WARNING] Failed to load ingest state: {e}")\n')
        new_lines.append('            return False\n')
        break
    else:
        new_lines.append(line)

skip = False
for i, line in enumerate(lines):
    if 'def load_from_disk(cls):' in line:
        skip = True
    if skip and 'return False' in line and 'except Exception as e:' in lines[i-1]:
        skip = False
        continue
    if skip:
        continue
    if not skip and 'def load_from_disk(cls):' not in line:
        new_lines.append(line)

with open('C:/LocalAI_Workstation/app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
