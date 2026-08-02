import time
import subprocess
import datetime
import os

log_file = r"C:\LocalAI_Workstation\logs\infinite_runner.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)

def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] {msg}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")

log("啟動無限耐久壓力測試 (Soak Testing)...")

while True:
    log("開始執行新的一輪測試...")
    # 執行 AppTest 邏輯腳本
    result = subprocess.run(["python", r"C:\LocalAI_Workstation\tests\system_ui_tester.py"])
    if result.returncode != 0:
        log(f"⚠️ 測試迴圈偵測到異常退出，代碼: {result.returncode}")
    else:
        log("✅ 本輪測試順利完成")
    time.sleep(5)
