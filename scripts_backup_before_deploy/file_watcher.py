import os
import sys
import time
import json
import random
from pathlib import Path
from workflow_helper import ensure_dirs, log_workflow, log_error
try:
    from auto_ingest_bot import is_file_content_legal
except ImportError:
    def is_file_content_legal(f_path):
        return True

SUPPORTED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm', '.mp3', '.wav', '.m4a', '.flac'}

def get_existing_sources(manifests_dir):
    sources = set()
    manifests_path = Path(manifests_dir)
    for f in manifests_path.glob("*.json"):
        if f.name.endswith("_chunks.json") or f.name == "queue.json":
            continue
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                source_path = data.get("source_path")
                if source_path:
                    sources.add(os.path.abspath(source_path))
        except Exception:
            pass
    return sources

def generate_task_id():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    rand_part = random.randint(1000, 9999)
    return f"task_{timestamp}_{rand_part}"

def scan_new_files():
    paths = ensure_dirs()
    raw_data_dir = paths["raw_data_dir"]
    manifests_dir = paths["manifests_dir"]
    
    existing_sources = get_existing_sources(manifests_dir)
    
    new_tasks = []
    raw_path = Path(raw_data_dir)
    
    if not raw_path.exists():
        log_error(f"輸入影音目錄不存在: {raw_data_dir}")
        return new_tasks

    for item in raw_path.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            abs_item_path = os.path.abspath(str(item))
            if abs_item_path not in existing_sources:
                # [新增防護] 強制過濾非國家考試的非相關檔案
                if not is_file_content_legal(abs_item_path):
                    continue
                
                task_id = generate_task_id()
                
                # 初始化任務狀態檔案
                manifest_data = {
                    "task_id": task_id,
                    "source_path": abs_item_path,
                    "source_name": item.name,
                    "status": "queued",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "error_count": 0,
                    "steps": {
                        "watcher": "completed",
                        "preprocess": "pending",
                        "chunk_planner": "pending",
                        "stt": "pending",
                        "merge": "pending",
                        "formatter": "pending"
                    }
                }
                
                manifest_file = os.path.join(manifests_dir, f"{task_id}.json")
                try:
                    with open(manifest_file, "w", encoding="utf-8") as f:
                        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
                    
                    log_workflow(f"Detected new file: {item.name}. Created task_id: {task_id}")
                    new_tasks.append(task_id)
                except Exception as e:
                    log_error(f"Failed to create manifest for {item.name}: {e}")
                    
    return new_tasks

if __name__ == "__main__":
    scan_new_files()
