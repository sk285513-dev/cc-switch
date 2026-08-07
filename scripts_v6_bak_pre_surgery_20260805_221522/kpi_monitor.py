# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: kpi_runner.ps1
# Downstream: None
# Shared State: KPI Logs, System Metrics

try:
    import json
except ImportError:
    import json
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

"""
kpi_monitor.py — LexMind-Omni 自動 KPI 監控與修正
每 5 分鐘執行一次（由排程或 watchdog 呼叫）

KPI 定義：
  Phase A (NOW～16:00)  Preprocess 階段
    KPI-A1: queued→chunked 轉換率 ≥ 10 任務/小時 (3 workers × ~3.3/hr)
    KPI-A2: workflow 進程必須存活
    KPI-A3: 同一批任務不得重複出現 >5 次（卡死偵測）

  Phase B (16:00 以後)  STT 階段
    KPI-B1: chunked→completed 轉換率 ≥ 40 任務/小時
    KPI-B2: 每 5 分鐘至少新增 3 個 completed chunk
    KPI-B3: failed 任務數不超過 total 的 5%

自動修正行為：
  - Workflow 死掉 → 自動重啟
  - 任務卡死迴圈 → 強制標記為 failed 跳過
  - CPU 過熱 > 78°C → 臨時降並發
  - quota_state 鬼畜 → 清空重置
  - source 磁碟無法存取 → 跳過該 drive 的任務
"""

import json
import os
import sys
import time
import subprocess
import datetime
import shutil
from pathlib import Path
from collections import Counter

# 共用監控工具
_mu_dir = os.path.dirname(os.path.abspath(__file__))
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("monitoring_utils", os.path.join(_mu_dir, "monitoring_utils.py"))
    _mu = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mu)
    _check_workflow_alive = _mu.check_workflow_alive
except Exception:
    _check_workflow_alive = None

# ─── 路徑 ───────────────────────────────────────────────
WORK_DIR    = Path("C:/LocalAI_Workstation")
MANIFESTS   = Path("A:/manifests_v6")
LOG_PATH    = Path("A:/logs/workflow.log")
KPI_STATE   = Path("A:/logs/kpi_state.json")   # 上次快照
KPI_LOG     = Path("A:/logs/kpi_monitor.log")   # KPI 監控 log
QUOTA_STATE = WORK_DIR / "config/quota_state.json"
RESTART_SCRIPT = WORK_DIR / "restart_workflow.ps1"

# ─── KPI 閾值 ────────────────────────────────────────────
KPI_A1_MIN_TASKS_PER_HOUR    = 10     # Preprocess: queued→chunked ≥ 10/hr
KPI_A3_STUCK_REPEAT_LIMIT    = 24     # 同批任務重複 ≥ 24 次 = 卡死（2小時），防止誤別STT任務
KPI_B1_MIN_COMPLETE_PER_HOUR = 40     # STT: completed ≥ 40/hr
KPI_B2_MIN_CHUNKS_PER_5MIN   = 1      # BUG-17 修正：降為 0 會導致完全假死也達標，改為 1 避免防禦盲點
KPI_B3_MAX_FAIL_RATIO        = 0.05   # failed 不超過 5%
CPU_OVERTEMP_C               = 78     # GPU 過熱閾值
STT_PHASE_HOUR               = 16     # 幾點開始 STT（本地時間）
# 企業金鑰模式：LEXMIND_ENTERPRISE="1" 時全天視為 STT Phase B，不受 16:00 時段限制
# 預設 "0" = 保留舊的免費金鑰時段分流（回滾用）
ENTERPRISE_MODE              = os.environ.get("LEXMIND_ENTERPRISE", "0") == "1"

# ─── 工具函數 ─────────────────────────────────────────────

def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # keeping naive for log display
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(KPI_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_snapshot() -> dict:
    if KPI_STATE.exists():
        try:
            return json.loads(KPI_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_snapshot(snap: dict):
    KPI_STATE.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


def scan_manifests() -> dict:
    """掃描所有 manifest，回傳統計資料。"""
    stats = Counter()
    done_chunks_total = 0
    total_chunks_total = 0
    failed_tasks = []
    repeated_tasks = []   # 判斷是否卡死

    # 讀 log 中最後 50 行，統計重複 task id
    task_appear = Counter()
    try:
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
        for line in lines:
            if "Task task_" in line and "開始" in line:
                import re
                m = re.search(r'task_\w+', line)
                if m:
                    task_appear[m.group()] += 1
    except Exception:
        pass

    for mf in MANIFESTS.glob("task_*.json"):
        if "_chunks" in mf.name:
            continue
        try:
            m = json.loads(mf.read_text(encoding="utf-8-sig"))
            tid = m.get("task_id", "")
            if "mock_" in tid:
                continue
            status = m.get("status", "unknown")
            stats[status] += 1

            if status == "failed":
                failed_tasks.append(tid)

            # chunk 統計
            cm = str(mf).replace(".json", "_chunks.json")
            if os.path.exists(cm):
                try:
                    with open(cm, "r", encoding="utf-8-sig", errors="replace") as _cf:
                        chunks = json.load(_cf)
                    done  = sum(1 for c in chunks if c.get("status") in ("completed", "stt_done"))
                    total = len(chunks)
                    done_chunks_total  += done
                    total_chunks_total += total
                except Exception:
                    pass
        except Exception:
            pass

    # 卡死任務（重複出現超過閾值）
    repeated_tasks = [tid for tid, cnt in task_appear.most_common(5) if cnt >= KPI_A3_STUCK_REPEAT_LIMIT]

    # 長時間停滯的 processing 任務（超過 15 分鐘未更新）
    stalled_tasks = 0
    stall_threshold = 15 * 60  # 15 分鐘
    now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
    for mf in MANIFESTS.glob("task_*.json"):
        if "_chunks" in mf.name:
            continue
        try:
            m = json.loads(mf.read_text(encoding="utf-8-sig", errors="replace"))
            if m.get("status") == "processing":
                mtime = mf.stat().st_mtime
                if (now_ts - mtime) > stall_threshold:
                    stalled_tasks += 1
        except Exception:
            pass

    return {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "queued":    stats.get("queued", 0),
        "chunked":   stats.get("chunked", 0),
        "completed": stats.get("completed", 0),
        "failed":    stats.get("failed", 0),
        "merged":    stats.get("merged", 0),
        "done_chunks":  done_chunks_total,
        "total_chunks": total_chunks_total,
        "failed_tasks": failed_tasks,
        "repeated_tasks": repeated_tasks,
        "stalled_tasks": stalled_tasks,
    }


def is_workflow_alive() -> bool:
    """
    偵測 run_workflow.py 進程是否存活。
    統一由 monitoring_utils.check_workflow_alive() 處理，
    相容 python.exe / pythonw.exe, 完整路徑與相對路徑。
    encoding='utf-8', errors='replace' 以防 CP950 0xa6 誤判。
    """
    if _check_workflow_alive is not None:
        try:
            return _check_workflow_alive()
        except Exception as e:
            log(f"  [ERROR] 檢查 workflow 狀態失敗: {e}")
            return False
    # fallback
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             'name="python.exe" or name="pythonw.exe"',
             "get", "ProcessId,CommandLine"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
            creationflags=0x08000000
        )
        return "run_workflow" in result.stdout.lower().replace("\\", "/")
    except Exception as e:
        log(f"  [ERROR] 檢查 workflow 狀態失敗: {e}")
        return False


def restart_workflow():
    log("[FIX] 重啟 run_workflow.py...")
    
    lock_file = MANIFESTS / "workflow.lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
            log(f"[FIX] 已清理殘留鎖定檔 {lock_file}")
        except Exception as e:
            log(f"[WARN] 無法清理鎖定檔: {e}")

    # 【重要修復】將 timeout 放寬至 120 秒，避免 WMI 與 Start-Process 拖慢導致 kpi_monitor 崩潰
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(RESTART_SCRIPT)],
        capture_output=True, timeout=120, cwd=str(WORK_DIR), creationflags=0x08000000
    )
    log("[FIX] ✅ restart_workflow.ps1 已執行")


def reset_quota_state():
    log("[FIX] 清空 quota_state.json...")
    QUOTA_STATE.write_text('{"exhausted_keys":[]}', encoding="utf-8")


def skip_stuck_tasks(task_ids: list):
    """
    安全版「卡死任務賻定」——加入「進度檢查」，避免誤殺正常任務。

    判定為「真正卡死」的條件（全部满足才殺）：
      1. 任務狀態為 chunked（已切片夠候 STT）
      2. chunk 完成數為 0（完全沒有任何進度）
      3. 任務建立超過 2 小時（不是剛剛創建的）
    """
    import os
    now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
    TWO_HOURS = 7200

    for tid in task_ids:
        for mf in MANIFESTS.glob(f"*{tid}*.json"):
            if "_chunks" in mf.name:
                continue
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))

                # 安全閘：已完成或已標記失敗的不動
                if m.get("status") in ("completed", "failed"):
                    continue

                # 安全閘：檢查 chunk 實際進度
                chunk_file = str(mf).replace(".json", "_chunks.json")
                done_chunks = 0
                total_chunks = m.get("chunks_count", 0)
                if os.path.exists(chunk_file):
                    try:
                        chunks = json.loads(open(chunk_file, encoding="utf-8").read())
                        done_chunks = sum(1 for c in chunks if c.get("status") in ("completed", "stt_done"))
                        total_chunks = len(chunks)
                    except Exception:
                        pass

                if done_chunks > 0:
                    log(f"[GUARD] 跳過 {tid}:已完成 {done_chunks}/{total_chunks} chunks，不視為卡死")
                    continue

                # 安全閘：檢查任務年齡（太新的任務不殺）
                created_str = m.get("created_at", "")
                if created_str:
                    try:
                        created_ts = datetime.datetime.fromisoformat(created_str.replace("Z","+00:00")).timestamp()
                        if (now_ts - created_ts) < TWO_HOURS:
                            log(f"[GUARD] 跳過 {tid}:建立不到 2 小時，不視為卡死")
                            continue
                    except Exception:
                        pass

                # 通過所有安全閘，才真正標記為失敗
                m["status"] = "failed"
                m["steps"]["stt"] = "failed"
                m["skip_reason"] = "kpi_monitor: stuck loop detected (0 chunks done, >2hr)"
                mf.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
                log(f"[FIX] 強制 skip 卡死任務 {tid} (0/{total_chunks} chunks, >2hr)")
            except Exception as e:
                log(f"[WARN] skip_stuck_tasks 失敗 {tid}: {e}")

def run_diagnostics():
    """執行主動診斷，並記錄到 kpi_monitor.log"""
    log("  [DIAG] === 啟動主動深度診斷 ===")
    
    # 1. 檢查 Python 程序
    try:
        r = subprocess.run(
            ['wmic', 'process', 'where', 'name="pythonw.exe" or name="python.exe"', 'get', 'ProcessId,CommandLine'],
            capture_output=True, text=True, encoding="utf-8-sig", errors="ignore", creationflags=0x08000000
        )
        if r.stdout:
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip() and "wmic" not in l]
            log(f"  [DIAG] 目前存活的 Python 程序 ({len(lines)-1 if len(lines)>0 else 0} 支):")
            for l in lines:
                log(f"    - {l}")
    except Exception as e:
        log(f"  [DIAG] 無法檢查 Python 程序: {e}")

    # 2. 檢查 Workflow 最後的進度
    try:
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]
        keywords = ["Parallel Dispatcher", "Merge Agent", "開始", "完成", "stalled", "deadlock"]
        rel_lines = [l for l in lines if any(k in l for k in keywords)]
        if rel_lines:
            log("  [DIAG] Workflow 死前最後的關鍵動作:")
            for l in rel_lines[-5:]:  # 只印最後 5 筆
                log(f"    - {l.strip()}")
        else:
            log("  [DIAG] 近期 50 行無關鍵活動紀錄。")
    except Exception as e:
        log(f"  [DIAG] 無法讀取 workflow.log: {e}")
        
    log("  [DIAG] ================================")


def check_gpu_temp() -> float:
    """嘗試讀 GPU 溫度，失敗回傳 0。"""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        , creationflags=0x08000000)
        temps = [float(x.strip()) for x in r.stdout.splitlines() if x.strip().isdigit() or x.strip().replace('.','').isdigit()]
        return max(temps) if temps else 0.0
    except Exception:
        return 0.0


# ─── 主 KPI 檢查邏輯 ──────────────────────────────────────

def run_kpi_check():
    _tw = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    now = _tw
    if ENTERPRISE_MODE:
        is_stt_phase = True
    else:
        is_stt_phase = now.hour >= STT_PHASE_HOUR or now.hour < 8
    log(f"=== KPI 檢查開始 | 階段={'STT' if is_stt_phase else 'Preprocess'} (台灣時間{now.strftime('%H:%M')}) ===")

    # 掃描當前狀態
    cur = scan_manifests()
    prev = load_snapshot()

    total = cur["queued"] + cur["chunked"] + cur["completed"] + cur["failed"] + cur["merged"]
    log(f"  任務: queued={cur['queued']} chunked={cur['chunked']} "
        f"completed={cur['completed']} failed={cur['failed']} total={total}")
    log(f"  Chunks: {cur['done_chunks']}/{cur['total_chunks']} done")
    stalled = cur.get("stalled_tasks", 0)
    stall_mark = "⚠️" if stalled > 0 else "✅"
    log(f"  {stall_mark} Stalled tasks: {stalled} (處理中超過 15 分鐘)")

    issues = []

    # ── 計算速率（需有上次快照）──
    rate_tasks_per_hour = None
    rate_chunks_per_5min = None
    elapsed_hours = 0

    if prev:
        try:
            t_prev = datetime.datetime.fromisoformat(prev["ts"])
            if t_prev.tzinfo is None:
                t_prev = t_prev.replace(tzinfo=datetime.timezone.utc)
            actual_now_utc = datetime.datetime.now(datetime.timezone.utc)
            elapsed = (actual_now_utc - t_prev).total_seconds()
            elapsed_hours = elapsed / 3600

            if not is_stt_phase:
                # Phase A: queued→chunked rate
                new_chunked = cur["completed"] - prev.get("completed", 0) + \
                              (prev.get("queued", 0) - cur["queued"])
                rate_tasks_per_hour = (new_chunked / elapsed_hours) if elapsed_hours > 0.33 else None
            else:
                # Phase B: completed rate
                new_completed = cur["completed"] - prev.get("completed", 0)
                rate_tasks_per_hour = (new_completed / elapsed_hours) if elapsed_hours > 0.33 else None

            # chunk delta（不分階段）— 保留快照 delta 供 fallback 參考
            chunk_delta_snapshot = cur["done_chunks"] - prev.get("done_chunks", 0)
            rate_chunks_per_5min = chunk_delta_snapshot
        except Exception as e:
            log(f"[WARN] 速率計算失敗: {e}")

    # ── KPI 評估 ──────────────────────────────────────────

    # KPI-A2 / B: Workflow 存活
    alive = is_workflow_alive()
    log(f"  Workflow 存活: {'✅' if alive else '❌'}")
    if not alive:
        issues.append("workflow_dead")
        log("  [ALERT] ❌ KPI-A2 FAIL: Workflow 進程不存在！")

    # KPI-A3: 卡死偵測
    if cur["repeated_tasks"]:
        log(f"  [ALERT] ⚠️  KPI-A3 WARN: 卡死任務 {cur['repeated_tasks']}")
        issues.append(f"stuck:{','.join(cur['repeated_tasks'])}")

    # KPI-A1 / B1: 速率檢查
    if rate_tasks_per_hour is not None:
        threshold = KPI_B1_MIN_COMPLETE_PER_HOUR if is_stt_phase else KPI_A1_MIN_TASKS_PER_HOUR
        kpi_id = "B1" if is_stt_phase else "A1"
        label = "completed/hr" if is_stt_phase else "queued→chunked/hr"
        status_mark = "✅" if rate_tasks_per_hour >= threshold else "❌"
        log(f"  {status_mark} KPI-{kpi_id}: {rate_tasks_per_hour:.1f} {label} (需 ≥ {threshold})")
        if rate_tasks_per_hour < threshold * 0.5:   # 低於 50% 才觸發修正
            issues.append(f"low_rate:{rate_tasks_per_hour:.1f}")

    # KPI-B2: chunk 完成速率（直接掃描 chunk .txt 最後修改時間，不依賴快照差值）
    if is_stt_phase:
        # 以 filesystem mtime 計算過去 5 分鐘內實際完成的 chunk 數量
        import os
        chunks_base = Path("A:/chunks")
        window_seconds = 300  # 5 分鐘 (依照論文 KPI-B2 嚴格規範)
        cutoff_ts = now.timestamp() - window_seconds
        realtime_chunk_count = 0
        try:
            for task_dir in chunks_base.iterdir():
                if not task_dir.is_dir():
                    continue
                for txt_file in task_dir.glob("*.txt"):
                    try:
                        if txt_file.stat().st_mtime >= cutoff_ts:
                            realtime_chunk_count += 1
                    except OSError:
                        pass
        except Exception as scan_err:
            log(f"[WARN] chunk 即時掃描失敗，回退至快照差值: {scan_err}")
            realtime_chunk_count = rate_chunks_per_5min if rate_chunks_per_5min is not None else 0

        ok = realtime_chunk_count >= KPI_B2_MIN_CHUNKS_PER_5MIN
        # 三段式停滯等級
        stagnant_count = prev.get("stagnant_count", 0) if prev else 0
        if realtime_chunk_count <= 0:
            stagnant_count += 1
        else:
            stagnant_count = 0
        cur["stagnant_count"] = stagnant_count

        if stagnant_count >= 3:
            stall_level = "[STALL]"
        elif stagnant_count == 2:
            stall_level = "[MAJOR WARNING]"
        elif stagnant_count == 1:
            stall_level = "[WARNING]"
        else:
            stall_level = None

        log(f"  {'✅' if ok else '❌'} KPI-B2: +{realtime_chunk_count} chunks/15min (需 ≥ {KPI_B2_MIN_CHUNKS_PER_5MIN}) [即時掃描]")
        if rate_chunks_per_5min is not None and rate_chunks_per_5min != realtime_chunk_count:
            log(f"    (快照差值={rate_chunks_per_5min}，即時掃描={realtime_chunk_count}，以即時為準)")
        if stall_level:
            log(f"  {stall_level} 連續 {stagnant_count} 輪無新增 chunks")

        if stagnant_count >= 3:
            log("  [STALL] ❌ Chunk throughput stalled for 3 consecutive KPI cycles.")
            issues.append("stalled_chunks")
        elif not ok:
            issues.append("low_chunk_rate")

    # KPI-B3: Failed 比例
    fail_ratio = cur["failed"] / max(total, 1)
    ok = fail_ratio <= KPI_B3_MAX_FAIL_RATIO
    log(f"  {'✅' if ok else '❌'} KPI-B3: failed={cur['failed']} ({fail_ratio*100:.1f}%) (需 ≤ {KPI_B3_MAX_FAIL_RATIO*100:.0f}%)")
    if not ok:
        issues.append("high_fail_ratio")

    # GPU 溫度
    gpu_temp = check_gpu_temp()
    if gpu_temp > 0:
        log(f"  {'✅' if gpu_temp < CPU_OVERTEMP_C else '⚠️'} GPU 溫度: {gpu_temp}°C")
        if gpu_temp >= CPU_OVERTEMP_C:
            issues.append(f"gpu_overheat:{gpu_temp}")

    # ── 自動修正 ──────────────────────────────────────────
    save_snapshot(cur)

    if not issues:
        log("  ✅ 所有 KPI 達標，系統健康")
        return

    log(f"  [ACTION] 發現 {len(issues)} 個問題，開始自動修正...")

    for issue in issues:
        if issue in ("workflow_dead", "stalled_chunks"):
            run_diagnostics()
            if issue == "stalled_chunks":
                log("  [FIX] 偵測到連續停滯，強制重啟 workflow...")
            reset_quota_state()
            restart_workflow()

        elif issue.startswith("stuck:"):
            stuck_ids = issue.split(":")[1].split(",")
            skip_stuck_tasks(stuck_ids)
            time.sleep(2)
            restart_workflow()

        elif issue.startswith("low_rate:"):
            rate = float(issue.split(":")[1])
            log(f"  [DIAG] 速率低: {rate}/hr，檢查 workflow 狀態...")
            if not is_workflow_alive():
                restart_workflow()
            else:
                # 清 quota state 可能有髒資料
                reset_quota_state()
                log("  [FIX] quota_state 已重置，等下次週期確認")

        elif issue == "high_fail_ratio":
            log(f"  [DIAG] failed 任務過多，檢查細節...")
            # 把 failed 任務重置為 queued 讓系統重試
            reset_count = 0
            for mf in MANIFESTS.glob("task_*.json"):
                if "_chunks" in mf.name:
                    continue
                try:
                    m = json.loads(mf.read_text(encoding="utf-8"))
                    if m.get("status") == "failed" and "kpi_monitor" not in m.get("skip_reason", ""):
                        m["status"] = "queued"
                        for k in ["stt", "merge", "formatter"]:
                            if k in m.get("steps", {}):
                                m["steps"][k] = "pending"
                        mf.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
                        reset_count += 1
                except Exception:
                    pass
            log(f"  [FIX] 重置了 {reset_count} 個 failed 任務")

        elif issue.startswith("gpu_overheat:"):
            temp = issue.split(":")[1]
            log(f"  [WARN] GPU {temp}°C 過熱，無法自動降溫但已記錄")
            # 可考慮修改 PREPROCESS_CONCURRENCY 但目前不自動動代碼

    log("=== KPI 檢查完成 ===")


if __name__ == "__main__":
    run_kpi_check()
