import os
import sys
import time
import json
import random
from pathlib import Path
from workflow_helper import ensure_dirs, log_workflow, log_error

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
    
    # 預先讀取 A:\processed_md 中的已處理檔案清單，寫死比對，避免重複消化
    processed_md_dir = Path("A:\\processed_md")
    processed_files = []
    if processed_md_dir.exists():
        processed_files = [f.name for f in processed_md_dir.glob("*.md")]
        
    new_tasks = []
    
    # 擴充要掃描的目錄清單：包含 J 碟、H 碟主要教材目錄
    scan_paths = [Path(raw_data_dir)]
    if os.path.exists("J:\\"): scan_paths.append(Path("J:\\"))
    if os.path.exists("H:\\"): scan_paths.append(Path("H:\\"))
    
    # 定義法律課程關鍵字，避免掃描到不相關的私人檔案 (依照 Rule #10 防護禁令)
    LAW_KEYWORDS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法"]
    EXCLUDE_DIRS = {
        "system volume information", "$recycle.bin", "windows", "program files", 
        "program files (x86)", "appdata", ".gemini", "node_modules", ".git", 
        "localai_workstation"
    }

    for raw_path in scan_paths:
        if not raw_path.exists():
            continue
            
        try:
            drive_root = raw_path.anchor
        except Exception:
            drive_root = str(raw_path)

        for root, dirs, files in os.walk(str(raw_path)):
            # 限制深度與排除目錄
            try:
                rel_path = os.path.relpath(root, drive_root)
                depth = 0 if rel_path == "." else len(Path(rel_path).parts)
            except Exception:
                continue
                
            if depth >= 8:
                dirs.clear()
                continue
                
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIRS and not d.startswith('.')]
            
            for f in files:
                item = Path(root) / f
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                    abs_item_path = os.path.abspath(str(item))
                    
                    # 過濾非法律課程檔案
                    if not any(kw in abs_item_path for kw in LAW_KEYWORDS):
                        continue
                        
                    if abs_item_path not in existing_sources:
                        # 寫死檢查是否已經在 A:\processed_md 中
                        base_name = item.stem
                        is_already_processed = any(base_name in p_file for p_file in processed_files)
                        
                        if is_already_processed:
                            # 已經處理過，跳過
                            continue
                            
                        task_id = generate_task_id()
                        
                        # 依據資料夾結構推算課程名稱 (例如: [民事訴訟法_ch10]_預約...)
                        parent_dir = item.parent
                        grandparent_dir = parent_dir.parent if parent_dir else None
                        
                        if grandparent_dir and parent_dir and grandparent_dir.name != raw_path.name:
                            prefix = f"[{grandparent_dir.name}_{parent_dir.name}]_"
                            if not item.name.startswith("["):
                                display_name = prefix + item.name
                            else:
                                display_name = item.name
                        else:
                            display_name = item.name
                        
                        # 初始化任務狀態檔案
                        manifest_data = {
                            "task_id": task_id,
                            "source_path": abs_item_path,
                            "source_name": display_name,
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
                            with open(manifest_file, "w", encoding="utf-8") as fw:
                                json.dump(manifest_data, fw, ensure_ascii=False, indent=2)
                            
                            log_workflow(f"Detected new file: {display_name}. Created task_id: {task_id}")
                            new_tasks.append(task_id)
                        except Exception as e:
                            log_error(f"Failed to create manifest for {item.name}: {e}")
                    
    return new_tasks

if __name__ == "__main__":
    scan_new_files()
