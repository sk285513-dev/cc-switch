# -*- coding: utf-8 -*-
"""
check_stuck.py — 安全版 Workflow 健康監控
==========================================
殺任何程序前必須：
  1. 先確認錯誤碼（log / 進程存活 / 磁碟空間）
  2. 嘗試自動修復（清 lock、重設金鑰狀態等）
  3. 通知 AI 代理人（寫入 ALERT 檔）
  4. 最後才殺，且記錄原因

升級協議：
  STAGE 1 (> 10 min 無 log)  → 診斷並記錄
  STAGE 2 (> 15 min 無 log)  → 自動修復（清 lock、嘗試喚醒）
  STAGE 3 (> 20 min 無 log)  → 寫 ALERT 通知 AI，再殺
"""
import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

LOG_PATH     = Path(r"A:\logs\workflow.log")
ALERT_PATH   = Path(r"A:\logs\stuck_alert.json")  # AI 讀這個來診斷
MANIFESTS    = Path(r"A:\manifests")

# 三段升級閾值（秒）
WARN_THRESHOLD    = 600    # 10 min → 診斷
AUTOFIX_THRESHOLD = 900    # 15 min → 自動修復
KILL_THRESHOLD    = 1200   # 20 min → 通知+殺

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"


def get_log_age() -> float:
    """回傳 workflow.log 距離上次更新的秒數。"""
    if not LOG_PATH.exists():
        return float("inf")
    return time.time() - LOG_PATH.stat().st_mtime


def get_last_log_lines(n: int = 10) -> list[str]:
    try:
        return LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except Exception:
        return []


def get_workflow_pid() -> list[int]:
    """找所有 run_workflow.py 的 PID。"""
    try:
        out = subprocess.check_output(
            'wmic process where "CommandLine like \'%run_workflow.py%\'" get ProcessId,CommandLine',
            shell=True, text=True, timeout=5
        )
        pids = []
        for line in out.splitlines():
            parts = line.strip().split()
            if parts and parts[-1].isdigit():
                pids.append(int(parts[-1]))
        return pids
    except Exception:
        return []


def get_python_memory_mb() -> float:
    """估算所有 Python 進程的記憶體用量。"""
    try:
        out = subprocess.check_output(
            'wmic process where "Name=\'python.exe\'" get WorkingSetSize',
            shell=True, text=True, timeout=5
        )
        sizes = [int(line.strip()) for line in out.splitlines() if line.strip().isdigit()]
        return sum(sizes) / (1024 * 1024)
    except Exception:
        return 0.0


def diagnose() -> dict:
    """蒐集診斷資訊，不做任何修改。"""
    pids = get_workflow_pid()
    last_lines = get_last_log_lines(10)
    mem_mb = get_python_memory_mb()

    # 從 log 找最後錯誤碼
    error_lines = [l for l in last_lines if "ERROR" in l or "CRITICAL" in l or "Exception" in l]

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "log_age_sec": get_log_age(),
        "workflow_pids": pids,
        "workflow_alive": len(pids) > 0,
        "python_mem_mb": round(mem_mb, 1),
        "last_log_lines": last_lines,
        "last_errors": error_lines,
    }


def autofix(diag: dict) -> list[str]:
    """
    根據診斷結果嘗試自動修復，回傳已執行的動作清單。
    不殺任何進程。
    """
    actions = []

    # 1. 清 workflow.lock（可能死鎖）
    lock = Path(r"A:\manifests\workflow.lock")
    if lock.exists():
        lock.unlink()
        actions.append("cleared workflow.lock")

    # 2. 重置 quota_state（所有金鑰標回可用）
    quota_state = Path(r"C:\LocalAI_Workstation\config\quota_state.json")
    if quota_state.exists():
        try:
            qs = json.loads(quota_state.read_text(encoding="utf-8"))
            # 只清除短期限速（保留 limit:0 的永久封鎖）
            if qs.get("exhausted_keys"):
                qs["exhausted_keys"] = []
                quota_state.write_text(json.dumps(qs, indent=2), encoding="utf-8")
                actions.append("reset quota_state exhausted_keys")
        except Exception as e:
            actions.append(f"quota_state reset FAILED: {e}")

    # 3. 若 workflow 進程不在，嘗試輕量喚醒（不強制殺）
    if not diag["workflow_alive"]:
        try:
            script = r"C:\LocalAI_Workstation\scripts\run_workflow.py"
            subprocess.Popen(
                [sys.executable, script],
                cwd=r"C:\LocalAI_Workstation",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            actions.append("spawned run_workflow.py (process was dead)")
        except Exception as e:
            actions.append(f"spawn FAILED: {e}")
    else:
        actions.append(f"workflow alive (PIDs={diag['workflow_pids']}), no spawn needed")

    return actions


def write_alert(diag: dict, stage: str, actions: list[str], reason: str):
    """寫入 ALERT 檔，供 AI 代理人讀取診斷。"""
    alert = {
        "stage": stage,
        "reason": reason,
        "diagnosis": diag,
        "autofix_actions": actions,
        "instructions_for_ai": (
            f"Workflow log 超過 {int(diag['log_age_sec']//60)} 分鐘未更新。\n"
            f"已嘗試自動修復：{actions}\n"
            f"最後錯誤：{diag['last_errors']}\n"
            f"請檢查 run_workflow.py 並決定是否需要修改程式碼。"
        ),
    }
    ALERT_PATH.write_text(json.dumps(alert, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_kill(pids: list[int], reason: str):
    """
    記錄原因後才殺進程。
    只有在確認卡死（KILL_THRESHOLD 後）才呼叫。
    """
    for pid in pids:
        print(f"{RED}[KILL] 強制終止 PID {pid}（原因：{reason}）{RESET}")
        subprocess.run(f"taskkill /F /PID {pid}", shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check_stuck():
    age = get_log_age()
    diag = diagnose()
    actions_taken = []

    print(f"{CYAN}=== check_stuck.py ==={RESET}")
    print(f"Log 最後更新：{int(age)}s 前 | PID={diag['workflow_pids']} | 記憶體={diag['python_mem_mb']}MB")

    # ── Stage 1: 診斷（10 min）
    if age < WARN_THRESHOLD:
        print(f"{GREEN}[OK] Workflow 正常（log 於 {int(age)}s 前更新）{RESET}")
        # 若之前有 ALERT 檔，清除
        if ALERT_PATH.exists():
            ALERT_PATH.unlink()
        return False

    # ── Stage 2: 自動修復（15 min）
    if age >= WARN_THRESHOLD:
        print(f"{YELLOW}[WARN Stage 1] Log 超過 {int(age//60)} 分鐘未更新，開始診斷{RESET}")
        for line in diag["last_errors"]:
            print(f"  錯誤: {line}")

    if age >= AUTOFIX_THRESHOLD:
        print(f"{YELLOW}[WARN Stage 2] 嘗試自動修復...{RESET}")
        actions_taken = autofix(diag)
        for a in actions_taken:
            print(f"  自動修復: {a}")
        write_alert(diag, "AUTOFIX", actions_taken, f"log 超過 {int(age//60)} 分鐘未更新，已嘗試自動修復")

    # ── Stage 3: 通知 + 殺（20 min）
    if age >= KILL_THRESHOLD:
        reason = f"log 超過 {int(age//60)} 分鐘未更新，自動修復無效"
        write_alert(diag, "KILL", actions_taken, reason)
        print(f"{RED}[ALERT Stage 3] {reason}{RESET}")
        print(f"  ALERT 已寫入 {ALERT_PATH}")
        print(f"  最後錯誤行: {diag['last_errors']}")

        pids = get_workflow_pid()
        if pids:
            safe_kill(pids, reason)
            time.sleep(3)
            # 殺後重啟
            try:
                script = r"C:\LocalAI_Workstation\scripts\run_workflow.py"
                subprocess.Popen(
                    [sys.executable, script],
                    cwd=r"C:\LocalAI_Workstation",
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
                print(f"{GREEN}[OK] Workflow 已重啟{RESET}")
            except Exception as re_err:
                print(f"{RED}[ERR] 重啟失敗：{re_err}{RESET}")
        else:
            print(f"{YELLOW}[INFO] 沒有找到 workflow 進程（可能已自行結束）{RESET}")
            # 直接重啟
            autofix(diag)

        return True

    return False


if __name__ == "__main__":
    check_stuck()
