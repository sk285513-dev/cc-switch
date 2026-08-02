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
LexMind-Omni 處理進度即時儀表板
=================================
用法：python scripts/progress_dashboard.py
      python scripts/progress_dashboard.py --once   (只顯示一次)
      python scripts/progress_dashboard.py --export  (匯出 CSV)

功能：
  - 即時顯示每堂課的處理狀態與完成時間
  - 計算實測吞吐量與預計完成時間（ETA）
  - 每 30 秒自動刷新
"""

import os, sys, json, glob, re, csv, argparse, time
from datetime import datetime, timedelta
from pathlib import Path

# ── 嘗試載入 rich（彩色顯示），若無則降備純文字 ──
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.live import Live
    from rich.columns import Columns
    from rich.text import Text
    RICH = True
except ImportError:
    RICH = False

MANIFESTS_DIR = Path("A:/manifests")
LOG_PATH = Path("A:/logs/workflow.log")
REFRESH_SEC = 30


# ════════════════════════════════════════════
# 資料收集
# ════════════════════════════════════════════

def load_all_tasks():
    """讀取所有任務 manifest，返回結構化資料。"""
    tasks = []
    for mf in MANIFESTS_DIR.glob("task_*.json"):
        if "_chunks" in mf.name:
            continue
        try:
            with open(mf, encoding="utf-8") as f:
                m = json.load(f)

            task_id   = m.get("task_id", "")
            status    = m.get("status", "queued")
            steps     = m.get("steps", {})
            name      = (m.get("source_name") or m.get("video_path",""))
            name      = Path(name).stem[:40] if name else task_id[-8:]
            created   = m.get("created_at","")
            completed = m.get("completed_at","") or m.get("updated_at","")

            # chunk 統計
            cm = str(mf).replace(".json","_chunks.json")
            n_chunks = done_chunks = 0
            if os.path.exists(cm):
                try:
                    chunks    = json.load(open(cm, encoding="utf-8"))
                    n_chunks  = len(chunks)
                    done_chunks = sum(1 for c in chunks if c.get("status")=="completed")
                except Exception:
                    pass

            # 跳過 mock（檢查 task_id 及課程名）
            raw_name = m.get("source_name","") or m.get("video_path","")
            if "mock_" in task_id or "mock_" in str(raw_name).lower() or "mock_lesson" in str(raw_name).lower():
                continue

            # 流水線階段
            if status == "completed":
                stage = "✅ 完成"
            elif status == "failed":
                stage = "❌ 失敗"
            elif steps.get("formatter") == "completed":
                stage = "✅ 完成"
                status = "completed"
            elif steps.get("merge") == "completed":
                stage = "🔄 Formatter"
            elif steps.get("stt") == "completed":
                stage = "🔄 Merge"
            elif done_chunks > 0:
                stage = f"🎙️ STT {done_chunks}/{n_chunks}"
            elif n_chunks > 0:
                stage = "⏳ STT 待開始"
            else:
                stage = "📂 預處理"

            tasks.append({
                "task_id":     task_id,
                "name":        name,
                "status":      status,
                "stage":       stage,
                "steps":       steps,
                "n_chunks":    n_chunks,
                "done_chunks": done_chunks,
                "created":     created,
                "completed":   completed,
            })
        except Exception:
            pass
    return tasks


def parse_formatter_completions():
    """從 workflow.log 解析每個任務的 Formatter 完成時間（過濾 mock）。"""
    events = {}  # task_id → datetime
    try:
        lines = open(LOG_PATH, encoding="utf-8", errors="replace").readlines()
        for line in lines:
            if "Markdown Formatter: Completed task" not in line:
                continue
            ts_m  = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
            tid_m = re.search(r"task_\w+", line)
            if ts_m and tid_m:
                tid = tid_m.group(0)
                if "mock" in tid:          # ★ 過濾 mock 任務
                    continue
                ts = datetime.strptime(ts_m.group(1), "%Y-%m-%d %H:%M:%S")
                events[tid] = ts
    except Exception:
        pass
    return events


def compute_throughput(fmt_events):
    """根據最近 formatter 完成時間計算實測速率，返回 (tasks/hr, min/task)。"""
    sorted_ts = sorted(fmt_events.values())
    if len(sorted_ts) < 2:
        return None, None
    # 取最近 10 個有效間隔（排除超過 2 小時的異常大間隔）
    gaps = []
    for i in range(1, len(sorted_ts)):
        g = (sorted_ts[i] - sorted_ts[i-1]).total_seconds() / 60
        if 0.5 < g < 120:
            gaps.append(g)
    gaps = gaps[-10:]
    if not gaps:
        return None, None
    avg_min = sum(gaps) / len(gaps)
    return round(60 / avg_min, 2), round(avg_min, 1)


def compute_eta(remaining, tasks_per_hr):
    if not tasks_per_hr or tasks_per_hr <= 0:
        return "計算中..."
    hours_left = remaining / tasks_per_hr
    eta_dt = datetime.now() + timedelta(hours=hours_left)
    day_str = "今天" if eta_dt.date() == datetime.now().date() else eta_dt.strftime("%m/%d")
    return f"{day_str} {eta_dt.strftime('%H:%M')} (剩餘 {hours_left:.1f} 小時)"


# ════════════════════════════════════════════
# 顯示（rich 版）
# ════════════════════════════════════════════

def render_rich(tasks, fmt_events, export=False):
    console = Console()
    now = datetime.now()

    # ── 分類統計 ──
    done     = sum(1 for t in tasks if t["status"] == "completed")
    failed   = sum(1 for t in tasks if t["status"] == "failed")
    stt_act  = sum(1 for t in tasks if "STT" in t["stage"] and "待開始" not in t["stage"])
    merge_fmt = sum(1 for t in tasks if "Merge" in t["stage"] or "Formatter" in t["stage"])
    preproc  = sum(1 for t in tasks if "預處理" in t["stage"] or "待開始" in t["stage"])
    
    # 總計只算有意義的進度（排除失敗與無效任務）
    total    = done + stt_act + merge_fmt + preproc
    remaining = total - done

    tasks_per_hr, min_per_task = compute_throughput(fmt_events)
    eta_str = compute_eta(remaining, tasks_per_hr)

    # ── 標題面板 ──
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S")
    rate_str = f"{tasks_per_hr:.1f} 堂/小時 (實測)" if tasks_per_hr else "資料收集中..."
    console.print(Panel(
        f"[bold cyan]LexMind-Omni 處理進度儀表板[/]  [dim]{ts_str}[/]\n"
        f"[green]完成 {done}[/] / [yellow]進行中 {stt_act+merge_fmt}[/] / [dim]預處理 {preproc}[/] / 總計 {total}堂\n"
        f"實測速率：[bold yellow]{rate_str}[/]   ETA：[bold green]{eta_str}[/]",
        title="📊 進度總覽", border_style="bright_blue"
    ))

    # ── 已完成任務表（含實際完成時間）──
    done_tasks = [t for t in tasks if t["status"] == "completed"]
    # 為已完成任務補充 formatter 完成時間
    for t in done_tasks:
        t["fmt_ts"] = fmt_events.get(t["task_id"])

    # 按完成時間排序（最近優先）
    with_ts = [(t, t["fmt_ts"]) for t in done_tasks if t["fmt_ts"]]
    with_ts.sort(key=lambda x: x[1], reverse=True)
    without_ts = [(t, None) for t in done_tasks if not t["fmt_ts"]]
    sorted_done = with_ts[:100] + without_ts[:20]

    display_count = len(sorted_done)
    # 若數量少於 100，直接顯示「已完成課程 (共 X 堂)」
    # 若超過 100，才顯示「僅列出最近 100 堂，總計...」
    if display_count == done:
        tbl_title = f"✅ 已完成課程（共 {done} 堂）"
    else:
        tbl_title = f"✅ 已完成課程（僅列出最近 {display_count} 堂，總計已完成 {done} 堂）"

    tbl = Table(title=tbl_title, border_style="green", show_lines=True)
    tbl.add_column("完成時間",       style="dim",     width=17)
    tbl.add_column("課程名稱",       style="cyan",    width=38)
    tbl.add_column("Chunks",        style="magenta", width=8, justify="right")
    tbl.add_column("課程時長(估)",   style="yellow",  width=10, justify="right")

    for t, fmt_ts in sorted_done:
        ts_str2 = fmt_ts.strftime("%m-%d %H:%M:%S") if fmt_ts else "—"
        dur = f"~{t['n_chunks']*12}min" if t["n_chunks"] else "純文字"
        tbl.add_row(ts_str2, t["name"][:38], str(t["n_chunks"]) if t["n_chunks"] else "TXT", dur)

    console.print(tbl)

    # ── 進行中任務表 ──
    active = [t for t in tasks if t["status"] not in ("completed","failed")]
    if active:
        tbl2 = Table(title=f"🔄 進行中任務（{len(active)} 個切片）",
                     border_style="yellow", show_lines=False)
        tbl2.add_column("階段",      style="bold", width=20)
        tbl2.add_column("課程名稱",  style="cyan", width=38)
        tbl2.add_column("進度",      style="green",width=12, justify="right")

        stage_order = {"🔄 Formatter":0, "🔄 Merge":1, "🎙️":2, "⏳":3, "📂":4}
        def sort_key(t):
            import sys
            import re
            if 'C:\\LocalAI_Workstation\\scripts' not in sys.path:
                sys.path.append('C:\\LocalAI_Workstation\\scripts')
            try:
                import run_workflow
                priority = run_workflow.get_legal_priority_score(t.get("name", ""))
            except Exception:
                priority = 100

            stage_val = 9
            for k,v in stage_order.items():
                if t["stage"].startswith(k): 
                    stage_val = v
                    break
            
            padded_name = re.sub(r'\d+', lambda m: m.group().zfill(5), t.get("name", ""))
            return (stage_val, priority, padded_name)

        for t in sorted(active, key=sort_key)[:25]:
            prog = f"{t['done_chunks']}/{t['n_chunks']}" if t["n_chunks"] else "—"
            tbl2.add_row(t["stage"], t["name"][:38], prog)
        console.print(tbl2)

    # ── 吞吐量歷史（最近 10 個完成間隔）──
    sorted_fmt = sorted(fmt_events.items(), key=lambda x: x[1])
    if len(sorted_fmt) >= 3:
        tbl3 = Table(title="⚡ 最近完成速率記錄",
                     border_style="blue", show_lines=False)
        tbl3.add_column("完成時間",   width=17, style="dim")
        tbl3.add_column("任務",       width=14, style="cyan")
        tbl3.add_column("間隔",       width=10, style="yellow", justify="right")
        tbl3.add_column("速率",       width=12, style="green",  justify="right")

        recent10 = sorted_fmt[-11:]
        for i in range(1, len(recent10)):
            tid, ts = recent10[i]
            gap_min = (ts - recent10[i-1][1]).total_seconds() / 60
            rate_h  = 60/gap_min if gap_min > 0 else 0
            gap_str = f"{gap_min:.1f} min" if gap_min < 60 else f"{gap_min/60:.1f} hr"
            rate_str2 = f"{rate_h:.1f}/hr" if 0 < gap_min < 120 else "[dim]異常[/]"
            tbl3.add_row(ts.strftime("%m-%d %H:%M:%S"), tid[-10:], gap_str, rate_str2)
        console.print(tbl3)

    # ── 匯出 CSV ──
    if export:
        csv_path = Path("A:/processed_md/progress_report.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["task_id","name","status","stage","n_chunks","done_chunks","formatter_completed"])
            for t in tasks:
                w.writerow([
                    t["task_id"], t["name"], t["status"], t["stage"],
                    t["n_chunks"], t["done_chunks"],
                    fmt_events.get(t["task_id"],"")
                ])
        console.print(f"\n[green]✅ 已匯出 CSV：{csv_path}[/]")


# ════════════════════════════════════════════
# 顯示（純文字降備版）
# ════════════════════════════════════════════

def render_plain(tasks, fmt_events):
    os.system("cls" if sys.platform == "win32" else "clear")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done      = sum(1 for t in tasks if t["status"]=="completed")
    stt_act   = sum(1 for t in tasks if "STT" in t["stage"] and "待開始" not in t["stage"])
    merge_fmt = sum(1 for t in tasks if "Merge" in t["stage"] or "Formatter" in t["stage"])
    preproc   = sum(1 for t in tasks if "預處理" in t["stage"] or "待開始" in t["stage"])
    
    total     = done + stt_act + merge_fmt + preproc
    remaining = total - done

    tasks_per_hr, _ = compute_throughput(fmt_events)
    eta_str = compute_eta(remaining, tasks_per_hr)

    print("=" * 70)
    print(f" LexMind-Omni 處理進度儀表板  [{now}]")
    print("=" * 70)
    print(f" 完成: {done} / 總計: {total}  |  剩餘: {remaining}")
    print(f" 實測速率: {tasks_per_hr:.1f} 堂/小時" if tasks_per_hr else " 速率: 資料收集中")
    print(f" ETA: {eta_str}")
    print("-" * 70)

    print("\n[ 已完成課程 - 最近 15 筆 ]")
    with_ts = [(t, fmt_events.get(t["task_id"])) for t in tasks if t["status"]=="completed" and fmt_events.get(t["task_id"])]
    with_ts.sort(key=lambda x: x[1], reverse=True)
    for t, ts in with_ts[:15]:
        print(f"  {ts.strftime('%m-%d %H:%M')}  [{t['n_chunks']:2d} chunks]  {t['name'][:45]}")

    print("\n[ 進行中 ]")
    active = [t for t in tasks if t["status"] not in ("completed","failed")]
    for t in active[:10]:
        prog = f"{t['done_chunks']}/{t['n_chunks']}" if t["n_chunks"] else "—"
        print(f"  {t['stage']:<22} {prog:<8} {t['name'][:35]}")
    print("=" * 70)


# ════════════════════════════════════════════
# 主程式
# ════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="LexMind-Omni 進度儀表板")
    parser.add_argument("--once",   action="store_true", help="只顯示一次，不迴圈")
    parser.add_argument("--export", action="store_true", help="匯出 CSV 報表")
    parser.add_argument("--interval", type=int, default=REFRESH_SEC, help="刷新間隔秒數（預設30）")
    args = parser.parse_args()

    while True:
        try:
            tasks      = load_all_tasks()
            fmt_events = parse_formatter_completions()

            if RICH:
                if not args.once:
                    os.system("cls" if sys.platform == "win32" else "clear")
                try:
                    render_rich(tasks, fmt_events, export=args.export)
                except Exception as re:
                    # rich 渲染失敗 → 降級為純文字
                    print(f"[Dashboard] rich 渲染異常，降級輸出: {re}")
                    render_plain(tasks, fmt_events)
            else:
                render_plain(tasks, fmt_events)

        except Exception as e:
            print(f"[Dashboard] 資料載入異常，60 秒後重試: {e}")
            time.sleep(60)
            continue

        if args.once or args.export:
            break

        print(f"\n[自動刷新中，每 {args.interval} 秒更新一次。Ctrl+C 離開]\n")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[已停止監測]")
