import os
import sys
import time
import json
import threading
import psutil
from collections import deque
from datetime import datetime
from pathlib import Path

# ── 設定 ──
BASE_DIR = Path("C:/LocalAI_Workstation")
MANIFESTS_DIR = Path("A:/manifests_v6")
LOG_FILE = Path("A:/logs_v6/workflow.log")
WATCHDOG_LOG = Path("A:/logs_v6/watchdog.log")
WATCHDOG_ALERTS = Path("A:/logs_v6/watchdog_alerts.jsonl")
LOCK_FILE = MANIFESTS_DIR / "workflow.lock"

CHECK_INTERVAL = 60           # 每 60 秒檢查一次
LOG_STALE_MINUTES = 12        # 日誌失效閾值

import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(WATCHDOG_LOG, encoding='utf-8-sig'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("watchdog")

def is_workflow_running() -> bool:
    """檢查 run_workflow.py 是否在 python 進程中存活。"""
    try:
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info.get('name', '')
                cmdline = p.info.get('cmdline', [])
                if name and 'python' in name.lower() and cmdline:
                    if any('run_workflow' in str(arg) for arg in cmdline) and not any('watchdog' in str(arg) for arg in cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
    except Exception as e:
        log.warning(f"psutil failed: {e}")
        return LOCK_FILE.exists()

def is_log_fresh() -> bool:
    """檢查 workflow.log 是否在最近 N 分鐘內有更新"""
    try:
        if not LOG_FILE.exists():
            return False
        mtime = LOG_FILE.stat().st_mtime
        age_minutes = (time.time() - mtime) / 60.0
        return age_minutes < LOG_STALE_MINUTES
    except Exception as e:
        log.warning(f"[LOG] 檢查日誌新鮮度失敗: {e}")
        return True

def get_pending_count() -> int:
    """計算 manifests 目錄下尚未 completed 的任務數"""
    try:
        pending = 0
        for mf in MANIFESTS_DIR.glob("task_*.json"):
            if "_chunks" in mf.name:
                continue
            try:
                with open(mf, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                if data.get("status") != "completed":
                    pending += 1
            except Exception:
                pass
        return pending
    except Exception as e:
        log.warning(f"[MANIFEST] 檢查任務數量失敗: {e}")
        return 0

def write_alert_report(error_type: str, details: str):
    """將嚴重錯誤寫入 watchdog_alerts.jsonl 供 AI 定時巡邏讀取"""
    try:
        WATCHDOG_ALERTS.parent.mkdir(parents=True, exist_ok=True)
        alert = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "details": details,
            "status": "unresolved"
        }
        with open(WATCHDOG_ALERTS, 'a', encoding='utf-8-sig') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        log.info(f"[ALERT_REPORT] 錯誤報告已寫入: {error_type}")
    except Exception as e:
        log.error(f"[ALERT_REPORT] 寫入錯誤報告失敗: {e}")

def log_tail_worker():
    """背景即時追蹤 workflow.log，偵測異常"""
    if not LOG_FILE.exists():
        return
        
    try:
        with open(LOG_FILE, 'r', encoding='utf-8-sig', errors='replace') as f:
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(1)
                    continue
                
                line_lower = line.lower()
                
                if "unexpected utf-8 bom" in line_lower:
                    log.error("[ALERT] 偵測到致命 BOM 錯誤！")
                    write_alert_report("Unexpected UTF-8 BOM", "系統偵測到 Unexpected UTF-8 BOM 致命崩潰。")
    except Exception as e:
        log.error(f"[TAIL] tail worker died: {e}")

def main():
    log.info("=" * 60)
    log.info("LexMind-Omni Watchdog 啟動 (V6 Sandbox - ReadOnly)")
    log.info(f"檢查間隔: {CHECK_INTERVAL}s | 日誌失效閾值: {LOG_STALE_MINUTES} 分鐘")
    log.info(f"Manifest Dir: {MANIFESTS_DIR}")
    log.info("=" * 60)
    
    tail_thread = threading.Thread(target=log_tail_worker, daemon=True)
    tail_thread.start()

    while True:
        time.sleep(CHECK_INTERVAL)

        running = is_workflow_running()
        fresh = is_log_fresh()
        pending = get_pending_count()

        log.info(
            f"[CHECK] 進程存活={running} | 日誌新鮮={fresh} | 待處理={pending}"
        )

        if pending == 0:
            log.info("[IDLE] 所有任務已完成，等待新任務...")
            continue

        need_restart = (not running) or (running and not fresh)

        if need_restart:
            reason = "進程不存在" if not running else f"超過 {LOG_STALE_MINUTES} 分鐘無活動"
            log.warning(f"[ALERT] 工作流異常：{reason}")
            log.error("[ALERT] V6 workflow absent or stalled; manual controlled restart required.")
        else:
            log.info("[OK] 工作流正常運行中")

if __name__ == "__main__":
    main()
