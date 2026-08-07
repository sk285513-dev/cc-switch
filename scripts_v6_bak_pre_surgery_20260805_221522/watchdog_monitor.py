import os
import sys
import time
import json
import glob
import subprocess
import datetime
from pathlib import Path

# ── 設定 ──
WORKDIR = Path("C:/LocalAI_Workstation")
LOG_PATH = Path("A:/logs_v6/watchdog.log")
MANIFESTS_DIR = Path("A:/manifests_v6")
WORKFLOW_LOCK = MANIFESTS_DIR / "workflow.lock"
CHECK_INTERVAL = 15 * 60   # 15 分鐘
PIPELINE_INTERVAL = 30     # 30 秒做一次 pipeline tick

os.chdir(WORKDIR)
sys.path.insert(0, str(WORKDIR / "scripts_v6"))

def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8-sig") as f:
            f.write(line + "\n")
    except Exception:
        pass

def is_workflow_alive() -> bool:
    """檢查 run_workflow.py 是否在 python 進程中存活。"""
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info.get('name', '')
                cmdline = p.info.get('cmdline', [])
                if name and 'python' in name.lower() and cmdline:
                    if any('run_workflow' in str(arg) for arg in cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
    except Exception as e:
        log(f"[WARN] psutil failed, fallback to WMI: {e}")
        try:
            result = subprocess.run(
                ["powershell", "-c",
                 "Get-WmiObject Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
                 "Where-Object {$_.CommandLine -match 'run_workflow'} | "
                 "Measure-Object | Select-Object -ExpandProperty Count"],
                capture_output=True, text=True, timeout=10, encoding="utf-8-sig", errors="ignore"
            )
            count = int(result.stdout.strip() or "0")
            if count > 0:
                return True
        except Exception:
            pass
        return WORKFLOW_LOCK.exists()

def main():
    log("=" * 60)
    log("[Watchdog] LexMind-Omni 持久性監測程序啟動 (V6 Sandbox - ReadOnly)")
    log("[Watchdog] 監測間隔: 15 分鐘（workflow 健康檢查）")
    log("[Watchdog] Pipeline tick 間隔: 30 秒")
    log(f"[Watchdog] Manifest Dir: {MANIFESTS_DIR}")
    log("=" * 60)

    last_verify = 0

    while True:
        now = time.time()

        if now - last_verify >= CHECK_INTERVAL:
            log("[Watchdog] === 15 分鐘定期檢查 ===")
            if not is_workflow_alive():
                log("[ALERT] V6 workflow absent; manual controlled restart required.")
            else:
                log("[Watchdog] run_workflow.py 存活 ✅")

            try:
                completed = sum(
                    1 for mf in MANIFESTS_DIR.glob("task_*.json")
                    if "_chunks" not in mf.name
                    and json.load(open(mf, encoding="utf-8-sig")).get("status") == "completed"
                )
                log(f"[Watchdog] 已完成任務: {completed}")
            except Exception:
                pass

            last_verify = now

        time.sleep(PIPELINE_INTERVAL)

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8-sig', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8-sig', errors='replace')
    main()
