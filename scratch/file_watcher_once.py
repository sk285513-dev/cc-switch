import os
import sys
import time
import json
import random
import subprocess
from pathlib import Path
from workflow_helper import ensure_dirs, log_workflow, log_error

try:
    from auto_ingest_bot import is_file_content_legal
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from auto_ingest_bot import is_file_content_legal


SUPPORTED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm', '.mp3', '.wav', '.m4a', '.flac'}

def get_video_duration_and_size(file_path):
    """
    呼叫 ffprobe 取得影片分鐘數，並計算檔案大小 (MB)
    回傳 (分鐘數, 大小MB, MB/分比例)
    """
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        duration_sec = float(result.stdout.strip())
        duration_min = duration_sec / 60.0
        
        if duration_min <= 0:
            return 0, size_mb, 0
            
        ratio = size_mb / duration_min
        return duration_min, size_mb, ratio
    except Exception as e:
        return 0, 0, 0

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
    
    # 預先讀取 A:\processed_md 中的已處理檔案清單，並內建「檔案大小健康度檢查」
    # 取得目前已存在的 markdown 檔案清單（先不判斷大小，稍後動態判斷）
    processed_md_dir = Path("A:\\processed_md")
    processed_files = []
    if processed_md_dir.exists():
        for f in processed_md_dir.glob("*.md"):
            processed_files.append(f)
        
    new_tasks = []
    
    # 擴充要掃描的目錄清單：包含 J 碟、H 碟主要教材目錄
    scan_paths = [Path(raw_data_dir)]
    if os.path.exists("J:\\"): scan_paths.append(Path("J:\\"))
    if os.path.exists("H:\\"): scan_paths.append(Path("H:\\"))
    
    # 嚴格依照使用者要求：前提是必須嚴格封鎖非國家考試「司法官與律師」等法律相關專業科目以外的雜訊檔案
    LAW_KEYWORDS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法", "強制執行法", "智慧財產權法", "土地稅法", "土地登記", "不動產估價", "立法程序與技術", "法院組織法", "海商法", "海洋法", "勞動社會法", "關稅法規"]
    EXCLUDE_DIRS = {
        "system volume information", "$recycle.bin", "windows", "program files", 
        "program files (x86)", "appdata", ".gemini", "node_modules", ".git", 
        "localai_workstation", "chunks", "chunks_backup", "processed_md", "manifests", "distillation_data"
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
                if f.startswith("chunk_") or "temp_extract_" in f or "bandicam" in root.lower() or "bandicam" in f.lower():
                    continue
                item = Path(root) / f
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                    abs_item_path = os.path.abspath(str(item))
                    
                    # 過濾非法律課程檔案 (嚴格呼叫白名單與黑名單過濾)
                    if not is_file_content_legal(abs_item_path):
                        continue
                        
                    if abs_item_path not in existing_sources:
                        # 動態影片健康度檢查：取得時長與大小
                        duration_min, size_mb, ratio = get_video_duration_and_size(abs_item_path)
                        
                        # 檢查是否已經在 A:\processed_md 中，且符合動態大小驗證
                        base_name = item.stem
                        matching_md = next((p for p in processed_files if base_name in p.name), None)
                        
                        if matching_md and duration_min > 0:
                            try:
                                md_size_kb = matching_md.stat().st_size / 1024
                                min_kb = max(5.0, duration_min * 0.6)
                                max_kb = max(50.0, duration_min * 1.5)
                                
                                if min_kb <= md_size_kb <= max_kb:
                                    # 已經成功處理過且大小合理，跳過
                                    continue
                                else:
                                    log_error(f"[Markdown 異常] {matching_md.name} 大小 {md_size_kb:.1f}KB 與時長 {duration_min:.1f}分鐘 不符 (合理區間: {min_kb:.1f}~{max_kb:.1f}KB)。將重新加入佇列。")
                            except Exception:
                                pass
                                
                        initial_status = "queued"
                        if duration_min > 0:
                            is_video = item.suffix.lower() == '.mp4'
                            lower_bound = 2.0 if is_video else 0.1  # mp3/wav 語音檔每分鐘只需 0.1MB
                            
                            # 嚴格過濾：< 20分鐘為垃圾，20~60分鐘為待審核補充課
                            if duration_min < 20.0 or ratio < lower_bound or ratio > 50.0:
                                log_error(f"[異常廢片警告] 檔案 {item.name} 比例異常: {ratio:.2f} MB/分 (大小: {size_mb:.1f} MB, 長度: {duration_min:.1f} 分鐘)。已拒絕加入佇列。")
                                continue
                            elif duration_min < 60.0:
                                log_workflow(f"[⚠️ 需人工核准] 發現潛在補充課 (20~60分鐘): {item.name} (長度: {duration_min:.1f} 分鐘)。")
                                initial_status = "pending_approval"
                                
                        task_id = generate_task_id()
                        
                        # 依據資料夾結構推算課程名稱 (例如: [民事訴訟法_ch10]_預約...)
                        parts = list(item.parts)
                        dirs = parts[1:-1]
                        
                        class_name = "預設課程"
                        lesson_name = "預設課堂"
                        
                        if len(dirs) >= 2:
                            if dirs[-1].lower() in ['bandicam', 'record', '錄音', '錄影']:
                                lesson_name = dirs[-2]
                                class_name = dirs[-3] if len(dirs) >= 3 else dirs[-2]
                            else:
                                lesson_name = dirs[-1]
                                class_name = dirs[-2]
                        elif len(dirs) == 1:
                            class_name = dirs[0]
                            lesson_name = dirs[0]
                            
                        prefix = f"[{class_name}_{lesson_name}]_"
                        
                        if not item.name.startswith("["):
                            display_name = prefix + item.name
                        else:
                            display_name = item.name
                        
                        # 初始化任務狀態檔案
                        manifest_data = {
                            "task_id": task_id,
                            "source_path": abs_item_path,
                            "source_name": display_name,
                            "status": initial_status,
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


