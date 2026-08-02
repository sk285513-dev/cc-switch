import codecs

path = r'C:\LocalAI_Workstation\scripts_v6\sre_watchdog.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# We need to add logic to check if workflow is alive, and phase.
# To check workflow alive:
# import subprocess
# workflow_alive = 'run_workflow' in subprocess.getoutput('tasklist /FI "IMAGENAME eq python*" /V')
# current_phase_stt = True if os.environ.get("LEXMIND_ENTERPRISE", "0") == "1" else (datetime.now(timezone.utc) + timedelta(hours=8)).hour >= 16 or ...

old_block = '''                idle_time = (datetime.now() - self.last_log_activity).total_seconds()
                if idle_time > DEADLOCK_TIMEOUT_SECONDS:
                    msg = f"系統已經連續 {int(idle_time)} 秒沒有產生任何日誌活動。"
                    dispatch_incident("deadlock", "System Deadlock", "System", msg, original_log=msg)
                    self.last_log_activity = datetime.now()'''

new_block = '''                idle_time = (datetime.now() - self.last_log_activity).total_seconds()
                if idle_time > DEADLOCK_TIMEOUT_SECONDS:
                    msg = f"系統已經連續 {int(idle_time)} 秒沒有產生任何日誌活動。"
                    import subprocess
                    import os
                    from datetime import timezone, timedelta
                    workflow_alive = 'run_workflow' in subprocess.getoutput('tasklist /FI "IMAGENAME eq python*" /V')
                    enterprise_mode = os.environ.get("LEXMIND_ENTERPRISE", "0") == "1"
                    now_tw = datetime.now(timezone.utc) + timedelta(hours=8)
                    current_phase_stt = True if enterprise_mode else (now_tw.hour >= 16 or now_tw.hour < 8)
                    
                    if not workflow_alive and current_phase_stt:
                        dispatch_incident("deadlock", "System Deadlock", "System", msg, original_log=msg)
                    else:
                        logging.warning(msg + " (But workflow is alive or not in STT phase, skipping deadlock alert)")
                    self.last_log_activity = datetime.now()'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(content)
    print("SRE Watchdog patched")
else:
    print("Block not found in sre_watchdog")
