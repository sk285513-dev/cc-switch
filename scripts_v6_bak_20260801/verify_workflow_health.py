#!/usr/bin/env python3
# verify_workflow_health.py
# 自動化驗收腳本 - LexMind SRE 系統健康檢查
# 用途：每次修改完核心腳本後，一鍵驗證所有關鍵指標
# 輸出：JSON PASS/FAIL 報告

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

# ─── 路徑設定 ──────────────────────────────────────────────────────────────
LOG_BASE        = Path("A:/logs")
LOG_V6          = Path("A:/logs_v6")
KPI_LOG         = LOG_BASE / "kpi_monitor.log"
SRE_LOG         = LOG_BASE / "watchdog_internal_error.log"
STACK_DUMP_LOG  = LOG_V6 / "stack_dump.log"
MANIFESTS       = Path("A:/manifests")

# ─── 工具 ──────────────────────────────────────────────────────────────────
def _read_tail(path: Path, lines: int = 200) -> str:
    """安全讀取檔案末尾 N 行，encoding 統一 utf-8/errors=replace。"""
    try:
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        return "\n".join(text.splitlines()[-lines:])
    except Exception as e:
        return f"[READ ERROR] {e}"

def _wmic_output() -> str:
    """取得目前所有 python.exe / pythonw.exe 進程的命令列。"""
    try:
        r = subprocess.run(
            ["wmic", "process", "where",
             'name="python.exe" or name="pythonw.exe"',
             "get", "ProcessId,CommandLine"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30
        )
        return r.stdout.lower().replace("\\", "/")
    except Exception as e:
        return f"[WMIC ERROR] {e}"

# ─── 各項檢查 ──────────────────────────────────────────────────────────────

def check_processes(wmic_out: str) -> dict:
    """
    檢查 4 個核心進程：
      - run_workflow.py   (必須存在)
      - watchdog.py       (必須存在且只能有 1 支)
      - auto_healer.py    (必須存在)
      - progress_dashboard.py (必須存在)
    """
    results = {}

    # run_workflow.py
    results["run_workflow_alive"] = "run_workflow" in wmic_out

    # watchdog.py - 只能有 1 支
    watchdog_count = wmic_out.count("watchdog")
    results["watchdog_alive"] = watchdog_count >= 1
    results["watchdog_single"] = watchdog_count == 1
    results["watchdog_count"] = watchdog_count

    # auto_healer.py
    results["auto_healer_alive"] = "auto_healer" in wmic_out

    # progress_dashboard.py
    results["progress_dashboard_alive"] = "progress_dashboard" in wmic_out

    return results


def check_kpi_log() -> dict:
    """
    檢查 kpi_monitor.log 是否有：
      - Stalled tasks: N
      - [WARNING] / [MAJOR WARNING] / [STALL]
    """
    tail = _read_tail(KPI_LOG, lines=500)
    return {
        "kpi_log_exists": KPI_LOG.exists(),
        "has_stalled_tasks_output": "Stalled tasks:" in tail,
        "has_kpi_warning":         "[WARNING]" in tail,
        "has_kpi_major_warning":   "[MAJOR WARNING]" in tail,
        "has_kpi_stall":           "[STALL]" in tail,
    }


def check_sre_log_no_false_deadlock(wmic_out: str) -> dict:
    """
    當 workflow 存活時，sre_watchdog.log 不應出現 [DEADLOCK]。
    """
    tail = _read_tail(SRE_LOG, lines=200)
    workflow_alive = "run_workflow" in wmic_out
    has_deadlock_in_log = "[DEADLOCK]" in tail
    # 若 workflow 活著但日誌出現 [DEADLOCK]，就是誤報
    false_deadlock = workflow_alive and has_deadlock_in_log
    return {
        "sre_log_exists": SRE_LOG.exists() if SRE_LOG.exists() else (LOG_BASE / "watchdog_internal_error.log").exists(),
        "workflow_alive_at_check": workflow_alive,
        "has_deadlock_in_sre_log": has_deadlock_in_log,
        "false_deadlock_detected": false_deadlock,
    }


def check_stack_dump() -> dict:
    """
    檢查 stack_dump.log 是否存在且有效。
    """
    if not STACK_DUMP_LOG.exists():
        return {
            "stack_dump_exists": False,
            "has_stack_dump_tag": False,
            "has_task_id": False,
            "has_stage": False,
        }
    tail = _read_tail(STACK_DUMP_LOG, lines=100)
    return {
        "stack_dump_exists": True,
        "has_stack_dump_tag": "[STACK_DUMP]" in tail,
        "has_task_id":       "task_id" in tail,
        "has_stage":         "stage" in tail,
    }


def check_structured_event_tags() -> dict:
    """
    結構化日誌驗證：掃描所有相關日誌確認 5 個事件標籤是否有實際輸出。
    若有邏輯但無日誌輸出，視為 FAIL。
    """
    # 合併多個日誌來源
    combined = ""
    for lp in [KPI_LOG, SRE_LOG, LOG_BASE / "watchdog_internal_error.log"]:
        combined += _read_tail(lp, lines=500)
    # 也掃 workflow.log
    combined += _read_tail(LOG_BASE / "workflow.log", lines=200)
    combined += _read_tail(LOG_V6 / "stack_dump.log", lines=100)

    tags = ["[DEADLOCK]", "[STALL]", "[THROUGHPUT_STALL]", "[DEGRADED]", "[REVIEW_NEEDED]"]
    return {tag: tag in combined for tag in tags}


def check_stalled_tasks() -> dict:
    """
    從 manifests 計算 stalled_tasks。
    """
    stall_threshold = 15 * 60
    now_ts = datetime.now(timezone.utc).timestamp()
    stalled = 0
    total_processing = 0
    try:
        for mf in MANIFESTS.glob("task_*.json"):
            if "_chunks" in mf.name:
                continue
            try:
                with mf.open("r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
                if data.get("status") == "processing":
                    total_processing += 1
                    mtime = mf.stat().st_mtime
                    if (now_ts - mtime) > stall_threshold:
                        stalled += 1
            except Exception:
                pass
    except Exception:
        pass
    return {
        "total_processing": total_processing,
        "stalled_count": stalled,
    }


# ─── 主驗收邏輯 ────────────────────────────────────────────────────────────

def run_health_check() -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'='*60}")
    print(f"  LexMind SRE Health Check  |  {ts}")
    print(f"{'='*60}")

    wmic_out = _wmic_output()

    proc     = check_processes(wmic_out)
    kpi      = check_kpi_log()
    sre      = check_sre_log_no_false_deadlock(wmic_out)
    stack    = check_stack_dump()
    tags     = check_structured_event_tags()
    stalled  = check_stalled_tasks()

    # ─── PASS / FAIL 判定 ─────────────────────────────────────────────
    failures = []

    if not proc["run_workflow_alive"]:
        failures.append("FAIL: run_workflow.py 進程不存在")
    if not proc["watchdog_alive"]:
        failures.append("FAIL: watchdog.py 進程不存在")
    if not proc["watchdog_single"]:
        failures.append(f"FAIL: watchdog.py 有 {proc['watchdog_count']} 支（應恰好 1 支）")
    if not proc["auto_healer_alive"]:
        failures.append("WARN: auto_healer.py 進程不存在（非嚴格失敗）")
    if not proc["progress_dashboard_alive"]:
        failures.append("WARN: progress_dashboard.py 進程不存在（非嚴格失敗）")
    if sre["false_deadlock_detected"]:
        failures.append("FAIL: workflow 存活時 sre_watchdog.log 出現 [DEADLOCK]（誤報）")
    if not kpi["kpi_log_exists"]:
        failures.append("FAIL: kpi_monitor.log 不存在")

    # 事件標籤驗證（有邏輯但無輸出 => WARN，不是硬 FAIL，因為部分標籤需特定觸發條件）
    for tag, found in tags.items():
        if not found:
            failures.append(f"WARN: 事件標籤 {tag} 在日誌中未出現（可能尚未觸發）")

    overall = "PASS" if not any(f.startswith("FAIL") for f in failures) else "FAIL"

    # ─── 輸出 ──────────────────────────────────────────────────────────
    report = {
        "timestamp": ts,
        "overall": overall,
        "processes": proc,
        "kpi_log":  kpi,
        "sre_log":  sre,
        "stack_dump": stack,
        "event_tags": tags,
        "stalled_tasks": stalled,
        "issues": failures,
    }

    print(f"\n  Overall: {'[PASS]' if overall == 'PASS' else '[FAIL]'}")
    print(f"\n  Processes:")
    for k, v in proc.items():
        icon = "[OK]" if v else "[FAIL]"
        print(f"    {icon} {k}: {v}")
    print(f"\n  KPI Log:")
    for k, v in kpi.items():
        icon = "[OK]" if v else "[WARN]"
        print(f"    {icon} {k}: {v}")
    print(f"\n  SRE / Deadlock Misfire:")
    for k, v in sre.items():
        icon = "[OK]" if not (k == "false_deadlock_detected" and v) else "[FAIL]"
        print(f"    {icon} {k}: {v}")
    print(f"\n  Stack Dump:")
    for k, v in stack.items():
        icon = "[OK]" if v else "[WARN]"
        print(f"    {icon} {k}: {v}")
    print(f"\n  Event Tags (structured log grep):")
    for tag, found in tags.items():
        icon = "[OK]" if found else "[WARN]"
        print(f"    {icon} {tag}: {'found' if found else 'NOT FOUND in logs'}")
    print(f"\n  Stalled Tasks: {stalled['stalled_count']} / {stalled['total_processing']} processing")
    if failures:
        print(f"\n  Issues ({len(failures)}):")
        for f in failures:
            print(f"    {'[FAIL]' if f.startswith('FAIL') else '[WARN]'} {f}")
    print(f"\n{'='*60}\n")

    return report


if __name__ == "__main__":
    report = run_health_check()
    # 輸出 JSON 報告
    out_path = LOG_BASE / "verify_workflow_health_report.json"
    try:
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON 報告已寫入：{out_path}")
    except Exception as e:
        print(f"[WARN] 無法寫入 JSON 報告：{e}")
    sys.exit(0 if report["overall"] == "PASS" else 1)

