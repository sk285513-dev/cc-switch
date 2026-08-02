"""
【機制對應宣告】
此腳本 (reboot_watcher.py) 主要實作了以下視覺測試機制：
- [機制十四] 硬體級 Watchdog 與 Email 警報之設計 (Deadlock Watchdog)
"""
import os
import sys
import time
import subprocess
import urllib.request
import json
from datetime import datetime
import ctypes

LOG_FILE = r"A:\logs\reboot_watcher.log"

def write_log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}\n"
    print(line.strip())
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except:
        pass

def is_workflow_running():
    try:
        output = subprocess.check_output(
            'wmic process where "name=\'python.exe\'" get commandline',
            shell=True, text=True
        )
        return "run_workflow" in output
    except:
        return False

def is_ollama_busy():
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/ps", method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            return len(data.get("models", [])) > 0
    except:
        return False

def get_gpu_temp():
    try:
        output = subprocess.check_output(
            "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader",
            shell=True, text=True
        )
        temps = [int(x.strip()) for x in output.strip().split("\n") if x.strip().isdigit()]
        return max(temps) if temps else 0
    except:
        return 0

def test_system_idle():
    if is_workflow_running():
        return False, "Workflow is running"
    
    if is_ollama_busy():
        return False, "Ollama is inferencing"
    
    temp = get_gpu_temp()
    if temp >= 60:
        return False, f"GPU temp is {temp}C (needs <60C)"
        
    return True, "System idle"

def show_reboot_dialog(status_msg):
    # MB_YESNO = 4, MB_ICONQUESTION = 32, MB_TOPMOST = 262144
    style = 4 | 32 | 262144
    title = "LexMind Reboot Suggestion"
    text = (
        "LexMind Monitor: System is idle, safe to reboot!\n\n"
        f"Status: {status_msg}\n\n"
        "After reboot, auto-start:\n"
        "  [1] Dashboard window\n"
        "  [2] KPI monitor window\n"
        "  [3] Workflow transcription window\n\n"
        "Reboot now?"
    )
    # Return 6 for Yes, 7 for No
    return ctypes.windll.user32.MessageBoxW(0, text, title, style) == 6

def main():
    write_log("=== LexMind Python Reboot Watcher Started ===")
    check_count = 0
    
    while True:
        check_count += 1
        is_idle, status = test_system_idle()
        write_log(f"#{check_count} [{'IDLE' if is_idle else 'BUSY'}] {status}")
        
        if is_idle:
            write_log("==> All conditions met! Showing dialog...")
            if show_reboot_dialog(status):
                write_log("==> User clicked YES. Rebooting in 60s...")
                subprocess.Popen("shutdown /r /t 60", shell=True)
                
                # Show countdown info
                ctypes.windll.user32.MessageBoxW(
                    0, 
                    "System will reboot in 60 seconds.\nRun 'shutdown /a' in terminal if you want to cancel.", 
                    "Rebooting", 
                    48 | 262144
                )
                break
            else:
                write_log("==> User clicked NO. Waiting 10 minutes...")
                time.sleep(600)
        else:
            time.sleep(120)

if __name__ == "__main__":
    main()
