try:
    import json
except ImportError:
    import json
"""
LexMind-Omni Workflow Watchdog
================================
自動守護程式：每 60 秒檢查 run_workflow.py 是否仍在跑，
若進程消失或日誌停滯 > 25 分鐘，自動重啟。
"""

import os
import sys
import time
import subprocess
import psutil
import logging
import threading
import json
from collections import deque
import ctypes
from datetime import datetime, timedelta
from pathlib import Path

# ─── 路徑設定 ─────────────────────────────────────────
BASE_DIR = Path(r"C:\LocalAI_Workstation")
V6_ENV = os.environ.get("LEXMIND_ENV", "v5_prod")
if V6_ENV == "v6_canary":
    WORKFLOW_SCRIPT = BASE_DIR / "scripts" / "run_workflow.py"
    LOG_FILE = Path(r"A:\logs_v6\workflow.log")
    WATCHDOG_LOG = Path(r"A:\logs_v6\watchdog.log")
    WATCHDOG_ALERTS = Path(r"A:\logs_v6\watchdog_alerts.jsonl")
    LOCK_FILE = Path(r"A:\manifests_v6\workflow.lock")
    MANIFESTS_DIR = Path(r"A:\manifests_v6")
else:
    WORKFLOW_SCRIPT = BASE_DIR / "scripts" / "run_workflow.py"
    LOG_FILE = Path(r"A:\logs\workflow.log")
    WATCHDOG_LOG = Path(r"A:\logs\watchdog.log")
    WATCHDOG_ALERTS = Path(r"A:\logs\watchdog_alerts.jsonl")
    LOCK_FILE = Path(r"A:\manifests\workflow.lock")
    MANIFESTS_DIR = Path(r"A:\manifests")

CHECK_INTERVAL = 60           # 每 60 秒檢查一次
LOG_STALE_MINUTES = 12        # ★ BUG-17 修正：quota 冷卻需 10 分鐘，留 2 分鐘緩衝，防死鎖
MAX_RESTARTS = 999999         # 永不放棄

# ─── 日誌設定 ─────────────────────────────────────────
WATCHDOG_LOG.parent.mkdir(parents=True, exist_ok=True)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(WATCHDOG_LOG), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("watchdog")


def is_workflow_running() -> bool:
    """檢查是否有 run_workflow.py 正在執行"""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "run_workflow.py" in cmdline and "watchdog" not in cmdline:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def is_log_fresh() -> bool:
    """檢查 workflow.log 是否在最近 LOG_STALE_MINUTES 分鐘內有更新"""
    if not LOG_FILE.exists():
        return False
    mtime = datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
    return datetime.now() - mtime < timedelta(minutes=LOG_STALE_MINUTES)


def get_pending_count() -> int:
    """★ 計算所有尚未完成的真實任務（queued/stt_in_progress/merged 全算）
    修正原本只計 queued 的缺陷——merged 任務還需要 formatter 才算完成。"""
    if not MANIFESTS_DIR.exists():
        return 0
    count = 0
    import json
    PENDING_STATUSES = {"queued", "chunked", "stt_in_progress", "merged", "formatter_pending"}
    for f in MANIFESTS_DIR.glob("*.json"):
        if "_chunks" in f.name:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") in PENDING_STATUSES:
                if "mock_" not in data.get("task_id", ""):
                    count += 1
        except Exception:
            pass
    return count


def clear_stale_lock():
    """清除殭屍 lock 檔，確保重啟的 workflow 能正常取鎖"""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            log.info("[LOCK] 已清除殭屍 lock 檔")
    except Exception as e:
        log.warning(f"[LOCK] 清除 lock 失敗: {e}")


def reset_quota_state():
    """重置 key pool exhausted 狀態，避免重啟後 key 仍被標為耗盡"""
    try:
        import json
        qstate = BASE_DIR / "config" / "quota_state.json"
        qstate.write_text(json.dumps({"exhausted_keys": []}, ensure_ascii=False), encoding="utf-8")
        log.info("[QUOTA] key pool 狀態已重置")
    except Exception as e:
        log.warning(f"[QUOTA] 重置 key pool 失敗: {e}")


def kill_existing_workflow():
    """強制終止所有現存的 run_workflow.py 進程"""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "run_workflow.py" in cmdline and "watchdog" not in cmdline:
                log.info(f"[KILL] 正在終止舊的 run_workflow.py (PID: {proc.pid})")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(2)

def start_workflow() -> subprocess.Popen:
    """啟動 run_workflow.py 背景進程"""
    kill_existing_workflow()
    LOCK_FILE.unlink(missing_ok=True)
    proc = subprocess.Popen(
        [sys.executable, str(WORKFLOW_SCRIPT)],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    log.info(f"[RESTART] run_workflow.py 已重啟，PID={proc.pid}")
    return proc


def register_autostart():
    """將 watchdog 自己寫入 Registry Run Key，開機/登入自動啟動"""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        cmd = f'"{sys.executable}" "{WORKFLOW_SCRIPT.parent / "watchdog.py"}"'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "LexMindWatchdog", 0, winreg.REG_SZ, cmd)
        log.info(f"[AUTOSTART] Registry Run Key 已更新: {cmd}")
    except Exception as e:
        log.warning(f"[AUTOSTART] Registry 寫入失敗: {e}")

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
        with open(WATCHDOG_ALERTS, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        log.info(f"[ALERT_REPORT] 錯誤報告已寫入: {error_type}")
    except Exception as e:
        log.error(f"[ALERT_REPORT] 寫入錯誤報告失敗: {e}")

# ─── Log Monitor (Tailing Thread) ─────────────────────

def log_tail_worker():
    """背景即時追蹤 workflow.log，偵測無限迴圈與 BOM 致命錯誤"""
    if not LOG_FILE.exists():
        open(LOG_FILE, 'a').close()
        
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        # 先跳到檔案末尾
        f.seek(0, 2)
        
        # 建立雙向佇列來記錄出現特徵字串的時間戳記 (用於防禦無限迴圈)
        thundering_herd_q = deque()
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            line_lower = line.lower()
            
            # 1. 致命錯誤攔截: BOM
            if "unexpected utf-8 bom" in line_lower:
                log.error("[ALERT] 偵測到致命 BOM 錯誤！立即啟動緊急煞車！")
                kill_existing_workflow()
                write_alert_report(
                    error_type="Unexpected UTF-8 BOM",
                    details="系統偵測到 Unexpected UTF-8 BOM 致命崩潰。已強制終止所有工作管線。請檢查相關 JSON 檔案編碼。"
                )
            
            # 2. 頻率異常偵測: 狂印同一種 INFO (如 Key Pool 標記)
            if "[key pool]" in line_lower or "jitter" in line_lower:
                now = time.time()
                thundering_herd_q.append(now)
                
                # 剔除超過 10 秒的紀錄
                while thundering_herd_q and now - thundering_herd_q[0] > 10:
                    thundering_herd_q.popleft()
                    
                # 如果 10 秒內出現 30 次，就是無限迴圈洗版
                if len(thundering_herd_q) > 30:
                    log.error("[ALERT] 偵測到無限迴圈洗版！立即啟動緊急煞車！")
                    kill_existing_workflow()
                    write_alert_report(
                        error_type="Thundering Herd / Infinite Loop",
                        details="系統偵測到「無限金鑰輪替 / Jitter 迴圈」瘋狂洗版 (10秒內超過30次異常重試)。已強制切斷管線防止配額耗盡。"
                    )
                    # 清空 queue 避免連環紀錄
                    thundering_herd_q.clear()
                    # 休息一下再繼續追蹤
                    time.sleep(10)


def main():
    log.info("=" * 60)
    log.info("LexMind-Omni Watchdog 啟動")
    log.info(f"檢查間隔: {CHECK_INTERVAL}s | 日誌失效閾值: {LOG_STALE_MINUTES} 分鐘")
    log.info("=" * 60)

    # 確保開機自啟
    register_autostart()
    
    # 啟動背景 Log Tailing
    log.info("[LOG MONITOR] 啟動背景日誌即時追蹤執行緒...")
    tail_thread = threading.Thread(target=log_tail_worker, daemon=True)
    tail_thread.start()

    restart_count = 0

    # 立即做一次快速檢查
    log.info("[INIT CHECK] 啟動後立即執行首次健康檢查...")
    running = is_workflow_running()
    pending = get_pending_count()
    log.info(f"[INIT CHECK] 進程存活={running} | 待處理任務={pending}")
    if pending > 0 and not running:
        log.warning("[INIT CHECK] 工作流未運行，立即重啟！")
        try:
            clear_stale_lock()
            reset_quota_state()
            start_workflow()
            restart_count += 1
        except Exception as e:
            log.error(f"[INIT CHECK] 重啟失敗: {e}")

    while restart_count < MAX_RESTARTS:
        time.sleep(CHECK_INTERVAL)

        running = is_workflow_running()
        fresh = is_log_fresh()
        pending = get_pending_count()

        log.info(
            f"[CHECK] 進程存活={running} | 日誌新鮮={fresh} | "
            f"待處理={pending} | 已重啟次數={restart_count}"
        )

        # 沒有待處理任務 → 等待，不重啟
        if pending == 0:
            log.info("[IDLE] 所有任務已完成，等待新任務...")
            continue

        # 進程死掉 或 日誌超過 25 分鐘沒動（卡死）
        need_restart = (not running) or (running and not fresh)

        if need_restart:
            reason = "進程不存在" if not running else f"超過 {LOG_STALE_MINUTES} 分鐘無活動"
            log.warning(f"[ALERT] 工作流崩潰：{reason}，重啟中...")
            try:
                clear_stale_lock()
                reset_quota_state()
                start_workflow()
                restart_count += 1
                time.sleep(30)
            except Exception as e:
                log.error(f"[ERROR] 重啟失敗：{e}")
        else:
            log.info("[OK] 工作流正常運行中")

    log.warning(f"[STOP] 已達最大重啟 {MAX_RESTARTS} 次（不應發生，請檢查）")


if __name__ == "__main__":
    main()
