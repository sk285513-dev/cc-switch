# -*- coding: utf-8 -*-
import json
"""
即時課程進度監控工具
顯示當前真實任務的 STT 分片完成進度、總任務數、J 碟備份狀態
"""
import os, sys, json, time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8-sig')

MANIFESTS_DIR = r"A:\manifests"
PROCESSED_DIR = r"A:\processed_md"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def scan_progress():
    if not os.path.exists(MANIFESTS_DIR):
        print(f"{RED}A:\\manifests 不存在{RESET}")
        return

    tasks = {"completed": [], "transcribed": [], "chunked": [], "queued": [], "pending": [], "failed": [], "other": []}
    for f in os.listdir(MANIFESTS_DIR):
        if f.endswith(".json") and not f.endswith("_chunks.json") and f.startswith("task_"):
            try:
                with open(os.path.join(MANIFESTS_DIR, f), 'r', encoding='utf-8-sig') as jf:
                    data = json.load(jf)
                status = data.get("status", "other")
                # 只計入真實任務（排除 mock_course_dir）
                source_path = data.get("source_path", "")
                if "mock_course_dir" in source_path or "raw_data" in source_path:
                    continue
                tasks.get(status, tasks["other"]).append(data)
            except:
                pass

    real_completed = tasks["completed"]
    print("=" * 65)
    print(f"{BOLD}[LexMind-Omni] 真實課程端到端進度監控{RESET}  {time.strftime('%H:%M:%S')}")
    print("=" * 65)
    print(f"  {GREEN}已完成 (completed) : {len(real_completed):>3}/30{RESET}")
    print(f"  {BLUE}已轉錄 (transcribed): {len(tasks['transcribed']):>3}/30{RESET}")
    print(f"  {YELLOW}切片中 (chunked)    : {len(tasks['chunked']):>3}/30{RESET}")
    print(f"  佇列中 (queued)     : {len(tasks['queued']):>3}/30")
    print(f"  待處理 (pending)    : {len(tasks['pending']):>3}/30")
    print(f"  {RED}失敗   (failed)     : {len(tasks['failed']):>3}/30{RESET}")

    # 掃描當前正在轉錄的分片進度（chunked 中的第一個）
    chunked_tasks = tasks["chunked"]
    if chunked_tasks:
        active = chunked_tasks[0]
        task_id = active.get("task_id")
        source_name = active.get("source_name", "?")
        chunks_path = os.path.join(MANIFESTS_DIR, f"{task_id}_chunks.json")
        if os.path.exists(chunks_path):
            with open(chunks_path, 'r', encoding='utf-8-sig') as cf:
                chunks = json.load(cf)
            done = sum(1 for c in chunks if c.get("status") == "completed")
            total = len(chunks)
            print(f"\n  {BOLD}當前正在處理：{source_name}{RESET}")
            print(f"  分片進度：{YELLOW}{done}/{total} chunks 完成{RESET}")

    # J 碟備份核實
    print(f"\n{BOLD}[J 碟原始目錄備份狀態]{RESET}")
    backup_count = 0
    for task in real_completed:
        sp = task.get("source_path", "")
        if sp:
            backup_dir = os.path.dirname(sp)
            stem = task.get("task_id", "")
            md_path = task.get("output_markdown", "")
            if md_path and os.path.exists(os.path.join(backup_dir, os.path.basename(md_path))):
                backup_count += 1
                print(f"  {GREEN}[OK]{RESET} J 碟備份: {os.path.basename(md_path)}")
            elif backup_dir:
                print(f"  {RED}[缺]{RESET} J 碟備份缺失: {backup_dir}")

    if not real_completed:
        print(f"  {YELLOW}（尚無真實課程完成，J 碟備份待生成）{RESET}")
    print(f"\n  J 碟已備份課程數：{backup_count}/30")
    print("=" * 65)

if __name__ == "__main__":
    scan_progress()

