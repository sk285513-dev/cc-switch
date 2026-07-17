# -*- coding: utf-8 -*-
"""
自動激活 A:\manifests 下所有處於 initial 狀態的任務
將 steps 狀態重設為 pending，使 workflow_engine 能真正調度執行它們
"""
import os
import json
from pathlib import Path

manifests_dir = r"A:\manifests"
if not os.path.exists(manifests_dir):
    print("Manifests directory not found.")
    exit(1)

count = 0
for f in os.listdir(manifests_dir):
    if f.endswith(".json") and not f.endswith("_chunks.json") and f.startswith("task_"):
        p = os.path.join(manifests_dir, f)
        try:
            with open(p, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
            
            # 如果不是 completed/failed，且有 initial 的 steps，就重設
            status = data.get("status")
            steps = data.get("steps", {})
            
            if status not in ["completed", "failed"]:
                has_initial = any(v == "initial" for v in steps.values())
                if has_initial:
                    # 重新初始化為 pending 狀態，以供正常調度
                    data["status"] = "queued"
                    data["steps"] = {
                        "watcher": "completed",
                        "preprocess": "pending",
                        "chunk_planner": "pending",
                        "stt": "pending",
                        "merge": "pending",
                        "formatter": "pending"
                    }
                    with open(p, 'w', encoding='utf-8') as wf:
                        json.dump(data, wf, ensure_ascii=False, indent=2)
                    count += 1
        except Exception as e:
            print(f"Error processing {f}: {e}")

print(f"Successfully activated {count} tasks by resetting initial steps to pending.")
