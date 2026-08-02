# monitoring_utils.py
# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: sre_watchdog.py, kpi_monitor.py, run_workflow.py
# Downstream: verify_workflow_health.py
# PURPOSE: 統一共用監控工具，禁止各腳本自行複製邏輯
#
# 提供以下共用函數：
#   check_workflow_alive()   - 偵測 run_workflow.py 進程
#   count_stalled_tasks()    - 計算 processing 超過 15 分鐘的任務數
#   ensure_aware(dt)         - 強制 datetime 為 timezone-aware (UTC)
#   log_event(tag, msg, log_path) - 結構化事件日誌
#   dump_stack_snapshot(...) - 全執行緒堆疊快照

import os
import sys
import json
import subprocess
import threading
import traceback
import faulthandler
from datetime import datetime, timezone
from pathlib import Path

# 允許的結構化事件標籤（嚴格白名單）
VALID_EVENT_TAGS = frozenset([
    "[DEADLOCK]",
    "[STALL]",
    "[THROUGHPUT_STALL]",
    "[DEGRADED]",
    "[REVIEW_NEEDED]",
])

MANIFESTS_PATH = Path("A:/manifests")
STACK_DUMP_LOG = Path(r"A:\logs_v6\stack_dump.log")


# ─── 1. check_workflow_alive ─────────────────────────────────────────────────

def check_workflow_alive() -> bool:
    """
    偵測 run_workflow.py 是否正在執行。
    相容 python.exe / pythonw.exe、完整路徑與相對路徑、斜線與反斜線。
    """
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             "name=\"python.exe\" or name=\"pythonw.exe\"",
             "get", "ProcessId,CommandLine"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.lower().replace("\\", "/")
        return "run_workflow" in stdout
    except Exception:
        return False


# ─── 2. count_stalled_tasks ──────────────────────────────────────────────────

def count_stalled_tasks(manifests_path: Path = MANIFESTS_PATH,
                        stall_minutes: int = 15) -> int:
    """
    計算所有 status == 'processing' 且 last_updated 距今超過 stall_minutes 的任務數。
    """
    stall_threshold_sec = stall_minutes * 60
    now_utc = datetime.now(timezone.utc)
    stalled = 0
    try:
        for mf in manifests_path.glob("task_*.json"):
            if "_chunks" in mf.name:
                continue
            try:
                with mf.open("r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
                if data.get("status") != "processing":
                    continue
                last_updated_str = data.get("last_updated") or data.get("updated_at", "")
                if not last_updated_str:
                    stalled += 1
                    continue
                last_updated = datetime.fromisoformat(last_updated_str)
                last_updated = ensure_aware(last_updated)
                elapsed = (now_utc - last_updated).total_seconds()
                if elapsed >= stall_threshold_sec:
                    stalled += 1
            except Exception:
                pass
    except Exception:
        pass
    return stalled


# ─── 3. ensure_aware ─────────────────────────────────────────────────────────

def ensure_aware(dt: datetime) -> datetime:
    """
    確保 datetime 物件帶有 timezone 資訊 (UTC)。
    避免「can't subtract offset-naive and offset-aware datetimes」錯誤。
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ─── 4. log_event ────────────────────────────────────────────────────────────

def log_event(tag: str, message: str, log_path: Path, extra: dict = None):
    """
    結構化事件日誌輸出。
    tag 必須為 VALID_EVENT_TAGS 中的標籤，否則拒絕寫入並發出警告。

    規則（防彈窗）：
      [STALL] / [THROUGHPUT_STALL] → 僅寫入日誌檔，不得觸發任何告警彈窗
      [DEADLOCK]                   → 允許寫入日誌並通知上層觸發告警/重啟
    """
    if tag not in VALID_EVENT_TAGS:
        # 不合規的標籤一律降為 WARNING，絕對不彈窗
        tag = "[STALL]"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    record = {
        "timestamp": ts,
        "tag": tag,
        "message": message,
    }
    if extra:
        record.update(extra)

    line = f"[{ts}] {tag} {message}"
    try:
        os.makedirs(log_path.parent, exist_ok=True)
        with open(log_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass

    # 標準輸出（若有 console）
    try:
        print(line, flush=True)
    except Exception:
        pass

    # 只有真 DEADLOCK 才回傳 True 讓呼叫方觸發告警
    return tag == "[DEADLOCK]"


# ─── 5. dump_stack_snapshot ──────────────────────────────────────────────────

def dump_stack_snapshot(
    task_id: str = "unknown",
    source_name: str = "unknown",
    stage: str = "unknown",
    chunk_count: int = 0,
    elapsed_seconds: float = 0.0,
    dump_path: Path = STACK_DUMP_LOG,
):
    """
    將所有執行緒的當前堆疊寫入 stack_dump.log。
    包含：timestamp, pid, task_id, source_name, stage, chunk_count, elapsed_seconds
    以及所有執行緒的 traceback。

    呼叫點（至少）：
      run_single_task_safe, merge_map, reduce, 單次 Vertex/外部 API 呼叫
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pid = os.getpid()

    lines = [
        "=" * 70,
        f"[STACK_DUMP] {ts}",
        f"  pid           = {pid}",
        f"  task_id       = {task_id}",
        f"  source_name   = {source_name}",
        f"  stage         = {stage}",
        f"  chunk_count   = {chunk_count}",
        f"  elapsed_sec   = {elapsed_seconds:.1f}",
        "-" * 70,
    ]

    # 收集所有執行緒堆疊
    frames = sys._current_frames()
    for thread in threading.enumerate():
        frame = frames.get(thread.ident)
        lines.append(f"\n[Thread] name={thread.name!r}  ident={thread.ident}")
        if frame is not None:
            tb_lines = traceback.format_stack(frame)
            lines.extend(tb_lines)
        else:
            lines.append("  (no frame)")

    lines.append("=" * 70 + "\n")
    full_text = "\n".join(lines)

    try:
        os.makedirs(dump_path.parent, exist_ok=True)
        with open(dump_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(full_text)
    except Exception as e:
        # 若連快照都寫不了，至少印到 stderr
        try:
            print(f"[dump_stack_snapshot ERROR] {e}", file=sys.stderr)
        except Exception:
            pass

    return full_text
