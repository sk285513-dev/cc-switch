try:
    import json
except ImportError:
    import json
"""
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
LexMind-Omni Watchdog Monitor
==============================
獨立於 Antigravity 會話的持久性監測程序。
功能：
  1. 每 15 分鐘執行 auto_verify.py 並寫入 log
  2. 偵測 run_workflow.py 是否存活，若死亡自動重啟
  3. 執行 pipeline_daemon_tick（補發卡住的 merge/formatter）
  4. 所有 log 寫入 A:\\logs\\watchdog.log

啟動方式（帳號切換後在新帳號執行）：
  python scripts/watchdog_monitor.py

或背景啟動（不阻塞終端）：
  Start-Process python -ArgumentList 'scripts/watchdog_monitor.py' -WindowStyle Hidden
"""

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
LOG_PATH = Path("A:/logs/watchdog.log")
WORKFLOW_LOCK = Path("A:/manifests/workflow.lock")
MANIFESTS_DIR = Path("A:/manifests")
CHECK_INTERVAL = 15 * 60   # 15 分鐘
PIPELINE_INTERVAL = 30     # 30 秒做一次 pipeline tick

os.chdir(WORKDIR)
sys.path.insert(0, str(WORKDIR / "scripts"))

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
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
                 "Get-Process python -ErrorAction SilentlyContinue | "
                 "Where-Object {$_.CommandLine -like '*run_workflow*'} | "
                 "Measure-Object | Select-Object -ExpandProperty Count"],
                capture_output=True, text=True, timeout=10
            )
            count = int(result.stdout.strip() or "0")
            if count > 0:
                return True
        except Exception:
            pass
        return WORKFLOW_LOCK.exists()


def restart_workflow():
    """重啟 run_workflow.py。"""
    log("[Watchdog] run_workflow.py 未偵測到！嘗試重啟...")
    try:
        WORKFLOW_LOCK.unlink(missing_ok=True)
    except Exception:
        pass
    proc = subprocess.Popen(
        [sys.executable, str(WORKDIR / "scripts" / "run_workflow.py")],
        env=env, cwd=str(WORKDIR),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    log(f"[Watchdog] run_workflow.py 重啟完成 (pid={proc.pid})")


def run_auto_verify():
    """執行 auto_verify.py 並摘錄結果。"""
    try:
        result = subprocess.run(
            [sys.executable, str(WORKDIR / "scripts" / "auto_verify.py")],
            capture_output=True, text=True, timeout=120,
            env=env, cwd=str(WORKDIR)
        )
        # 摘錄關鍵行
        lines = result.stdout.splitlines()
        for line in lines:
            if any(kw in line for kw in ["驗收結論", "偵測到", "PASS", "FAIL", "ERROR"]):
                log("[AutoVerify] " + line.strip())
    except Exception as e:
        log(f"[Watchdog] auto_verify 執行失敗: {e}")


def pipeline_tick():
    """補發卡住的 merge 和 formatter subprocess。"""
    spawned = 0
    for mf in MANIFESTS_DIR.glob("task_*.json"):
        if "_chunks" in mf.name:
            continue
        try:
            with open(mf, encoding="utf-8") as f:
                m = json.load(f)
            task_id = m.get("task_id", "")
            steps = m.get("steps", {})
            status = m.get("status", "")
            if status in ("completed", "failed"):
                continue

            if steps.get("stt") == "completed" and steps.get("merge") == "pending":
                proc = subprocess.Popen(
                    [sys.executable, str(WORKDIR / "scripts" / "merge_transcript.py"),
                     "--task-id", task_id],
                    env=env, cwd=str(WORKDIR),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                log(f"[PipelineTick] Spawned merge for {task_id[-4:]} (pid={proc.pid})")
                spawned += 1

            elif steps.get("merge") == "completed" and steps.get("formatter") == "pending":
                proc = subprocess.Popen(
                    [sys.executable, str(WORKDIR / "scripts" / "markdown_formatter.py"),
                     "--task-id", task_id],
                    env=env, cwd=str(WORKDIR),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                log(f"[PipelineTick] Spawned formatter for {task_id[-4:]} (pid={proc.pid})")
                spawned += 1
        except Exception:
            pass
    if spawned:
        log(f"[PipelineTick] Total spawned: {spawned}")


def main():
    log("=" * 60)
    log("[Watchdog] LexMind-Omni 持久性監測程序啟動")
    log("[Watchdog] 監測間隔: 15 分鐘（auto_verify + workflow 健康檢查）")
    log("[Watchdog] Pipeline tick 間隔: 30 秒")
    log("=" * 60)

    last_verify = 0

    while True:
        now = time.time()

        # ── 每 30 秒：pipeline tick ──
        pipeline_tick()

        # ── 每 15 分鐘：auto_verify + workflow 健康檢查 ──
        if now - last_verify >= CHECK_INTERVAL:
            log("[Watchdog] === 15 分鐘定期檢查 ===")

            # 健康檢查
            if not is_workflow_alive():
                restart_workflow()
            else:
                log("[Watchdog] run_workflow.py 存活 ✅")

            # 品管驗收
            run_auto_verify()

            # 完成數量快照
            try:
                completed = sum(
                    1 for mf in MANIFESTS_DIR.glob("task_*.json")
                    if "_chunks" not in mf.name
                    and json.load(open(mf, encoding="utf-8")).get("status") == "completed"
                )
                log(f"[Watchdog] 已完成任務: {completed}")
            except Exception:
                pass

            last_verify = now

        time.sleep(PIPELINE_INTERVAL)


if __name__ == "__main__":
    main()
