# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: watchdog.py, sre_watchdog.py
# Downstream: System Processes
# Shared State: Error Logs, System State

import os
import sys
import time
import json
import glob
import ctypes
import shutil
import logging
import threading
import subprocess
from datetime import datetime
from collections import defaultdict

# ==========================================
# Auto Healer: SRE 智慧自癒引擎
# ==========================================
log_dir = r"C:\LocalAI_Workstation\logs"
os.makedirs(log_dir, exist_ok=True)
healer_log = os.path.join(log_dir, "auto_healer.log")
incident_queue_log = os.path.join(log_dir, "sre_incident_queue.jsonl")
manifests_dir = r"A:\manifests"
corrupted_dir = r"A:\corrupted_backup"
os.makedirs(corrupted_dir, exist_ok=True)

sys.stdout = open(os.devnull, 'w')
sys.stderr = open(healer_log, 'a')

logging.basicConfig(
    filename=healer_log,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Windows MessageBox types for Escalation
MB_OK = 0x0
MB_ICONERROR = 0x10
MB_SERVICE_NOTIFICATION = 0x00200000

class AutoHealer:
    def __init__(self):
        self.heal_attempts = defaultdict(int)
        self.last_position = 0
        self.last_escalated_time = 0.0

    def escalate_to_human(self, signature, original_log):
        now = time.time()
        if now - self.last_escalated_time < 5.0:
            logging.info("Escalation rate-limited. Dropped popup.")
            return
        self.last_escalated_time = now
        title = "🚨 [AutoHealer 崩潰升級] 需要長官介入"
        logging.error(f"[ESCALATION] {signature} - {original_log}")
        
        alert_msg = f"Critical Error Escalation!\n\nSignature:\n{signature}\n\nLast Occurrence:\n{original_log}"
        
        def show_alert():
            try:
                flags = MB_OK | MB_ICONERROR | MB_SERVICE_NOTIFICATION | 0x40000
                ctypes.windll.user32.MessageBoxTimeoutW(0, ctypes.c_wchar_p(alert_msg), ctypes.c_wchar_p(title), flags, 0, 30000)
            except Exception as e:
                logging.error(f"Failed to escalate: {e}")
                
        # 專家設計：使用 Daemon Thread 發送彈跳視窗，徹底與核心監視管線脫鉤，解決阻塞問題
        threading.Thread(target=show_alert, daemon=True).start()

    def heal_json_corruption(self):
        logging.info("Attempting to heal JSON corruption...")
        healed = False
        if os.path.exists(manifests_dir):
            for filepath in glob.glob(os.path.join(manifests_dir, "*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8-sig') as f:
                        json.load(f)
                except Exception as e:
                    logging.warning(f"Found corrupted manifest: {filepath}. Moving to corrupted_backup.")
                    try:
                        shutil.move(filepath, os.path.join(corrupted_dir, os.path.basename(filepath)))
                        healed = True
                    except Exception as move_err:
                        logging.error(f"Failed to move corrupted file {filepath}: {move_err}")
        return healed

    def heal_deadlock(self):
        logging.info("Attempting to heal Deadlock...")
        try:
            subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True, creationflags=0x08000000)
            logging.info("Killed ffmpeg.exe just in case.")
            return True
        except Exception as e:
            logging.error(f"Failed to heal deadlock: {e}")
            return False

    def heal_quota_exceeded(self):
        logging.info("Handling Quota Exceeded (429/401)...")
        # Sleep for 15 minutes to cool down the queue
        time.sleep(15 * 60)
        return True

    def process_incident(self, incident):
        signature = incident.get("signature", "")
        original_log = incident.get("original_log", signature)
        lower_sig = signature.lower()
        incident_type = incident.get("type", "")

        logging.info(f"Processing incident: {signature}")

        self.heal_attempts[signature] += 1
        if self.heal_attempts[signature] > 3:
            self.escalate_to_human(signature, original_log)
            self.heal_attempts[signature] = 0
            return

        healed = False
        if "utf-8 bom" in lower_sig or "jsondecodeerror" in lower_sig:
            healed = self.heal_json_corruption()
        elif incident_type == "deadlock" or incident_type == "zero_progress":
            healed = self.heal_deadlock()
        elif "429" in lower_sig or "401" in lower_sig:
            healed = self.heal_quota_exceeded()
        else:
            logging.info(f"No specific playbook for {signature}, skipping.")
            healed = True

        if healed:
            logging.info(f"Successfully applied playbook for {signature}")
        else:
            logging.warning(f"Playbook failed for {signature}")

    def run(self):
        logging.info("Auto Healer 已啟動，正在背景監控 SRE Incident Queue...")
        if os.path.exists(incident_queue_log):
            self.last_position = os.path.getsize(incident_queue_log)
            
        while True:
            time.sleep(2)
            if not os.path.exists(incident_queue_log):
                continue
                
            current_size = os.path.getsize(incident_queue_log)
            if current_size < self.last_position:
                self.last_position = 0 
                
            if current_size > self.last_position:
                try:
                    with open(incident_queue_log, 'r', encoding='utf-8-sig') as f:
                        f.seek(self.last_position)
                        for line in f:
                            if line.strip():
                                try:
                                    incident = json.loads(line)
                                    self.process_incident(incident)
                                except json.JSONDecodeError:
                                    logging.error(f"Malformed incident log: {line}")
                        self.last_position = f.tell()
                except Exception as e:
                    logging.error(f"Failed to read incident queue: {e}")

if __name__ == "__main__":
    healer = AutoHealer()
    healer.run()

