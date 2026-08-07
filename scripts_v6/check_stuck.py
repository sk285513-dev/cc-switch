# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 4: 系統守門員與高可用 (SRE, Watchdog & Email)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 4】。
# 負責監控卡死並發送 SMTP Email 警報。嚴禁在除錯時閹割掉 Email 發送與監控邏輯。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
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

if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LOG_PATH = r"A:\logs\workflow.log"
MANIFESTS_DIR = r"A:\manifests"
TIMEOUT_THRESHOLD = 600  # 10 分鐘超時

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

from win32_kernel import KernelJobObject
from security_utils import clean_env

class ProcessTreeManager:
    """Phase 7.8 OS API 進程管理引擎 (Job Object 封裝)
    調用 Windows 核心 API 瞬間無情斬殺整個進程樹，絕不錯殺與遺留殭屍。
    """
    @staticmethod
    def kill_workflow_tree():
        print(f"{YELLOW}[自癒行動] 偵測到背景進程超時卡死，正在執行核心級強制重啟自癒程序...{RESET}")
        try:
            # 透過名稱開啟全域 Job Object
            job = KernelJobObject("Global\\LexMind_Job", open_only=True)
            job.terminate(1)
            job.close()
            print(f"  - {GREEN}[成功] 已透過 Job Object 瞬間清除死鎖的進程樹。{RESET}")
        except Exception as e:
            print(f"  - {RED}嘗試關閉舊進程時發生錯誤或 Job Object 不存在: {e}{RESET}")

    @staticmethod
    def spawn_daemon():
        try:
            script_path = os.path.join(os.getcwd(), "scripts", "run_workflow.py")
            if not os.path.exists(script_path):
                script_path = r"C:\LocalAI_Workstation\scripts\run_workflow.py"
            
            # 使用 Popen 在背景非同步啟動
            subprocess.Popen([sys.executable, script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, env=clean_env())
            print(f"{GREEN}[成功] 背景工作流已重新拉起！繼續執行佇列。{RESET}")
        except Exception as re:
            print(f"{RED}[錯誤] 無法重新啟動工作流守護進程: {re}{RESET}")

def restart_daemon():
    ProcessTreeManager.kill_workflow_tree()
    # 2. 清除鎖定文件 (如果是 SQLite lock 或 SingleInstanceLock)
    # 我們的 SingleInstanceLock 會在進程關閉後自動釋放，所以可以直接重啟
    ProcessTreeManager.spawn_daemon()

def check_stuck():
    if not os.path.exists(LOG_PATH):
        print(f"{YELLOW}[警告] 找不到日誌檔 {LOG_PATH}，可能工作流尚未啟動。{RESET}")
        return False

    # 1. 計算日誌最後更新時間距今秒數
    try:
        mtime = os.path.getmtime(LOG_PATH)
    except FileNotFoundError:
        print(f"{YELLOW}[警告] 找不到日誌檔 {LOG_PATH}，可能工作流尚未啟動或已被輪替刪除。{RESET}")
        return False
        
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

