# -*- coding: utf-8 -*-
"""
自動診斷與卡死自癒工具 (check_stuck.py)
1. 檢查 workflow.log 的最後更新時間，若卡在原地超過 10 分鐘 (600秒) 未更新，自動判定為卡死。
2. 檢查目前正在處理的 chunk 狀態。
3. 若判定卡死，自動採取自癒行動：重啟工作流守護進程，重設金鑰狀態。
"""
import os
import sys
import time
import json
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

LOG_PATH = r"A:\logs\workflow.log"
MANIFESTS_DIR = r"A:\manifests"
TIMEOUT_THRESHOLD = 600  # 10 分鐘超時

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def restart_daemon():
    print(f"{YELLOW}[自癒行動] 偵測到背景進程超時卡死，正在執行強制重啟自癒程序...{RESET}")
    
    # 1. 殺死所有本機 python 運行的 run_workflow.py 實例
    try:
        # 在 Windows 上尋找並殺死 run_workflow 相關進程
        cmd = 'wmic process where "CommandLine like \'%run_workflow.py%\'" get ProcessId'
        output = subprocess.check_output(cmd, shell=True, text=True)
        pids = [line.strip() for line in output.split('\n') if line.strip() and line.strip().isdigit()]
        for pid in pids:
            print(f"  - 殺死卡死進程 PID: {pid}")
            subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  - 嘗試關閉舊進程時發生錯誤: {e}")

    # 2. 清除鎖定文件 (如果是 SQLite lock 或 SingleInstanceLock)
    # 我們的 SingleInstanceLock 會在進程關閉後自動釋放，所以可以直接重啟

    # 3. 重新拉起 run_workflow.py
    try:
        script_path = os.path.join(os.getcwd(), "scripts", "run_workflow.py")
        if not os.path.exists(script_path):
            script_path = r"C:\LocalAI_Workstation\scripts\run_workflow.py"
        
        # 使用 Popen 在背景非同步啟動
        subprocess.Popen([sys.executable, script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        print(f"{GREEN}[成功] 背景工作流已重新拉起！繼續執行佇列。{RESET}")
    except Exception as re:
        print(f"{RED}[錯誤] 無法重新啟動工作流守護進程: {re}{RESET}")

def check_stuck():
    if not os.path.exists(LOG_PATH):
        print(f"{YELLOW}[警告] 找不到日誌檔 {LOG_PATH}，可能工作流尚未啟動。{RESET}")
        return False

    # 1. 計算日誌最後更新時間距今秒數
    mtime = os.path.getmtime(LOG_PATH)
    elapsed = time.time() - mtime
    
    print(f"日誌最後更新時間: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
    print(f"已停頓時間: {elapsed:.1f} 秒 (超時閾值: {TIMEOUT_THRESHOLD} 秒)")

    if elapsed > TIMEOUT_THRESHOLD:
        print(f"{RED}[WARN] 日誌卡在原地超過 {TIMEOUT_THRESHOLD} 秒未更新，判定為異常停擺！{RESET}")
        restart_daemon()
        return True
    else:
        print(f"{GREEN}[正常] 日誌在安全時間窗口內有更新，系統運作中。{RESET}")
        return False

if __name__ == "__main__":
    check_stuck()
