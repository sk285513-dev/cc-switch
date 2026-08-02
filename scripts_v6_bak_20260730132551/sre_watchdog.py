# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: System Scheduler
# Downstream: auto_healer.py
# Shared State: Process Status, Resource Usage

import os
import sys
import time
import json
import logging
import threading
import re
from collections import defaultdict
from datetime import datetime, timedelta

# ==========================================
# 專家修復版：安全日誌系統 (防止 print 崩潰)
# ==========================================
log_dir = r"C:\LocalAI_Workstation\logs"
os.makedirs(log_dir, exist_ok=True)
watchdog_error_log = os.path.join(log_dir, "watchdog_internal_error.log")
incident_queue_log = os.path.join(log_dir, "sre_incident_queue.jsonl")

# 專家修復：處理 pythonw.exe 的 stdout/stderr 防止 IO 崩潰
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(watchdog_error_log, 'a')

logging.basicConfig(
    filename=watchdog_error_log,
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

LOG_FILES = [
    r"A:\logs\workflow.log",
    r"A:\logs\kpi_monitor.log",
    r"A:\logs\watchdog.log",
    r"C:\LocalAI_Workstation\logs\ui_test_report.log",
    r"C:\LocalAI_Workstation\logs\watchdog_alerts.jsonl"
]

# SRE thresholds
DEDUPE_WINDOW_SECONDS = 300
ERROR_COUNT_THRESHOLD = 3
DEADLOCK_TIMEOUT_SECONDS = 180
PROGRESS_TIMEOUT_SECONDS = 900

# 專家設計：使用 DOTALL 確保多行錯誤也能完整捕捉，剃除前綴的時間與級別標籤
LOG_PATTERN = re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3})\s+\[.*?\]\s+(?P<core_message>.*)$', re.DOTALL)

def dispatch_incident(incident_type, signature, source_file, message, count=1, original_log=""):
    incident = {
        "timestamp": datetime.now().isoformat(),
        "type": incident_type,
        "signature": signature,
        "source_file": source_file,
        "message": message,
        "count": count,
        "original_log": original_log.strip()
    }
    try:
        with open(incident_queue_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(incident, ensure_ascii=False) + "\n")
    except Exception as e:
        logging.error(f"Failed to write to incident queue: {e}")

class SREWatchdog:
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.last_alert_time = defaultdict(lambda: datetime.min)
        self.last_log_activity = datetime.now()
        self.file_positions = {}

    def parse_and_alert(self, line, source_file):
        self.last_log_activity = datetime.now()
        
        if "成功" in line or "完成" in line or "[SUCCESS]" in line or "✅" in line:
            self.last_progress_activity = datetime.now()

        lower_line = line.lower()
        fatal_keywords = ["traceback (most recent", "unexpected utf-8 bom", "jsondecodeerror", "winerror", "[fail]", "[error]"]
        is_fatal = any(k in lower_line for k in fatal_keywords)
        
        warning_keywords = ["error_type", "exception", "401 unauthenticated", "429 too many"]
        is_warning = any(k in lower_line for k in warning_keywords)

        if is_fatal or is_warning:
            # 完美分離時間與核心訊息，只用乾淨核心來分組，不會因為時間跳動而被判定為新錯誤
            match = LOG_PATTERN.search(line)
            if match:
                signature = match.group('core_message').strip()
            else:
                signature = line[:100].strip()
                if "[FAIL]" in line.upper():
                    parts = line.upper().split("[FAIL]")
                    signature = "[FAIL]" + parts[-1][:90].strip()
                elif "[ERROR]" in line.upper():
                    parts = line.upper().split("[ERROR]")
                    signature = "[ERROR]" + parts[-1][:90].strip()
            
            self.error_counts[signature] += 1
            now = datetime.now()
            
            threshold_met = True if is_fatal else (self.error_counts[signature] >= ERROR_COUNT_THRESHOLD)
            
            if threshold_met:
                if (now - self.last_alert_time[signature]).total_seconds() > DEDUPE_WINDOW_SECONDS:
                    level_text = "致命崩潰" if is_fatal else "持續異常"
                    msg = f"症狀: 系統發生 {level_text}！ (在 {DEDUPE_WINDOW_SECONDS} 秒內累計 {self.error_counts[signature]} 次)"
                    
                    dispatch_incident(
                        "fatal" if is_fatal else "warning", 
                        signature, 
                        os.path.basename(source_file), 
                        msg,
                        self.error_counts[signature],
                        original_log=line
                    )
                    
                    logging.error(f"[INCIDENT DISPATCHED] {signature}")
                    
                    self.error_counts[signature] = 0
                    self.last_alert_time[signature] = now

    def check_deadlock(self):
        if not hasattr(self, 'last_progress_activity'):
            self.last_progress_activity = datetime.now()
            
        while True:
            try:
                time.sleep(60)
                idle_time = (datetime.now() - self.last_log_activity).total_seconds()
                if idle_time > DEADLOCK_TIMEOUT_SECONDS:
                    msg = f"系統已經連續 {int(idle_time)} 秒沒有產生任何日誌活動。"
                    dispatch_incident("deadlock", "System Deadlock", "System", msg, original_log=msg)
                    self.last_log_activity = datetime.now()
                    
                progress_idle_time = (datetime.now() - self.last_progress_activity).total_seconds()
                if progress_idle_time > PROGRESS_TIMEOUT_SECONDS:
                    msg = f"系統已經連續 {int(progress_idle_time/60)} 分鐘沒有成功完成任何任務！"
                    dispatch_incident("zero_progress", "Zero Progress", "System", msg, original_log=msg)
                    self.last_progress_activity = datetime.now()
            except Exception as e:
                logging.error(f"Error in check_deadlock thread: {e}")

    def tail_files(self):
        logging.info("SRE 智慧哨兵已啟動，正在背景監控系統日誌...")
        threading.Thread(target=self.check_deadlock, daemon=True).start()

        for fpath in LOG_FILES:
            if os.path.exists(fpath):
                self.file_positions[fpath] = os.path.getsize(fpath)
            else:
                self.file_positions[fpath] = 0

        last_heartbeat = 0
        while True:
            time.sleep(1)
            
            # 安全非阻塞心跳：寫入獨立檔案供其他 UI 監聽，不破壞 stdout
            now = time.time()
            if now - last_heartbeat > 10:
                try:
                    with open(r"C:\LocalAI_Workstation\logs\watchdog_heartbeat.ping", "w", encoding="utf-8") as f:
                        f.write(f"ALIVE: {now}")
                except: pass
                last_heartbeat = now

            for fpath in LOG_FILES:
                if not os.path.exists(fpath):
                    continue
                
                current_size = os.path.getsize(fpath)
                if current_size < self.file_positions[fpath]:
                    self.file_positions[fpath] = 0
                
                if current_size > self.file_positions[fpath]:
                    try:
                        with open(fpath, 'r', encoding='utf-8-sig', errors='replace') as f:
                            f.seek(self.file_positions[fpath])
                            for line in f:
                                if line.strip():
                                    self.parse_and_alert(line, fpath)
                            self.file_positions[fpath] = f.tell()
                    except Exception as e:
                        logging.warning(f"Failed to read file {fpath}: {e}")

if __name__ == "__main__":
    watchdog = SREWatchdog()
    watchdog.tail_files()

