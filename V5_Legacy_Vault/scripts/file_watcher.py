import os
import sys
import time
import json
import random
from pathlib import Path
from workflow_helper import ensure_dirs, log_workflow, log_error
from national_exam_rules import get_usb_drives, is_file_content_legal

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
    
    # 收集要掃描的目錄清單：A:\raw_data_stash 以及所有外接 USB 碟
    scan_dirs = []
    if raw_path.exists():
        scan_dirs.append(raw_path)
    else:
        log_error(f"輸入影音目錄不存在: {raw_data_dir}")
        
    usb_drives = get_usb_drives()
    for d in usb_drives:
        usb_path = Path(d)
        if usb_path.exists():
            scan_dirs.append(usb_path)

    for current_dir in scan_dirs:
        # 使用 os.walk 遞迴掃描目錄，過濾隱藏與系統資料夾加速掃描
        for root, dirs, files in os.walk(str(current_dir)):
            # 移除隱藏與系統資料夾
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('$') and d not in ("System Volume Information", "Windows", "Program Files", "Program Files (x86)")]
            
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    abs_item_path = os.path.abspath(os.path.join(root, filename))
                    
                    try:
                        file_size_mb = os.path.getsize(abs_item_path) / (1024 * 1024)
                    except OSError:
                        continue
                        
                    if file_size_mb < 5.0:
                        continue
                        
                    if abs_item_path not in existing_sources:
                        # [防重複處理邏輯] 檢查原始課程檔案的目錄底下看是不是有存在原本的 srt, md, json 檔
                        # 如果在 process 找不到，但實體檔案已經出來且大小正常，表示已經處理過了
                        stem = Path(abs_item_path).stem
                        parent_dir = Path(abs_item_path).parent
                        has_md = False
                        has_srt = False
                        has_json = False
                        try:
                            for f in parent_dir.iterdir():
                                if f.is_file() and stem in f.name:
                                    if f.suffix == '.md' and f.stat().st_size > 1024:
                                        has_md = True
                                    elif f.suffix == '.srt' and f.stat().st_size > 1024:
                                        has_srt = True
                                    elif f.name.endswith('_index.json') and f.stat().st_size > 512:
                                        has_json = True
                        except Exception:
                            pass
                        
                        if has_md and has_srt and has_json:
                            # 原始目錄已有處理完成的產物，標記為已存在並跳過
                            existing_sources.add(abs_item_path)
                            continue

                        # [Bug #7 Fix] 強制過濾掉舊版系統殘留在 J/H 碟的切片與暫存音檔
                        if "chunk_" in filename.lower() or "temp_" in filename.lower() or "extract_" in filename.lower():
                            continue

                        # 使用 SSOT 檢查是否為國考法律教材
                        if not is_file_content_legal(abs_item_path):
                            continue
                            
                        task_id = generate_task_id()
                        
                        # 自動根據目錄結構產生命名格式: [科目_章節]_檔名
                        path_parts = Path(abs_item_path).parts
                        if len(path_parts) >= 3:
                            if path_parts[-3].endswith(':\\'):
                                formatted_name = f"[{path_parts[-2]}]_{filename}"
                            else:
                                formatted_name = f"[{path_parts[-3]}_{path_parts[-2]}]_{filename}"
                        elif len(path_parts) == 2:
                            formatted_name = f"[{path_parts[-2]}]_{filename}"
                        else:
                            formatted_name = filename

                        # 初始化任務狀態檔案
                        manifest_data = {
                            "task_id": task_id,
                            "source_path": abs_item_path,
                            "source_name": formatted_name,
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
                            
                            log_workflow(f"Detected new file: {filename}. Created task_id: {task_id}")
                            new_tasks.append(task_id)
                        except Exception as e:
                            log_error(f"Failed to create manifest for {filename}: {e}")
                    
    return new_tasks

if __name__ == "__main__":
    scan_new_files()
