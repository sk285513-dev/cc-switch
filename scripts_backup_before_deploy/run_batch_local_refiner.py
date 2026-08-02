try:
    import json
except ImportError:
    import json
import os
import re
import json
import subprocess
import sys
import glob
from pathlib import Path

def build_manifest_mapping(log_path):
    """
    掃描 workflow.log，建立 filename -> task_id 的映射
    """
    mapping = {}
    last_file = None
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match_file = re.search(r'Saved pure TXT transcript to .*\\(.+\.txt)', line)
                if match_file:
                    last_file = match_file.group(1).strip()
                
                match_task = re.search(r'Completed task (task_[a-zA-Z0-9_]+)', line)
                if match_task and last_file:
                    mapping[last_file] = match_task.group(1).strip()
                    last_file = None
    except Exception as e:
        print(f"解析 {log_path} 失敗: {e}")
            
    print(f"成功從日誌中建立 {len(mapping)} 筆任務映射。")
    return mapping

def extract_buggy_filenames(md_path):
    """
    從 buggy_legacy_srts_v2.md 中提取所有的 .txt 檔名
    """
    filenames = []
    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'### (\[.*\.txt)', line)
            if match:
                filenames.append(match.group(1).strip())
    print(f"從瑕疵清單中找到 {len(filenames)} 筆需要處理的檔案。")
    return filenames

def run_batch():
    log_path = r"A:\logs\workflow.log"
    buggy_list_path = r"C:\Users\temp\.gemini\antigravity\brain\d172c99e-f55a-4b1e-8bf0-0f33aed88a84\buggy_legacy_srts_v2.md"
    progress_file = r"C:\LocalAI_Workstation\batch_progress.json"
    
    # 1. 建立映射
    mapping = build_manifest_mapping(log_path)
    
    # 2. 取得目標檔案
    buggy_filenames = extract_buggy_filenames(buggy_list_path)
    
    # 3. 讀取斷點續傳進度
    completed = []
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            completed = json.load(f)
            
    # 4. 開始排隊處理
    for filename in buggy_filenames:
        if filename in completed:
            print(f"跳過已完成任務: {filename}")
            continue
            
        task_id = mapping.get(filename)
        if not task_id:
            print(f"找不到 {filename} 的 task_id 映射，請確認是否在 manifests 資料夾中。")
            continue
            
        print(f"\n=======================================================")
        print(f"開始處理: {filename} (Task ID: {task_id})")
        print(f"=======================================================")
        
        # Ensure manifests exist for downstream scripts (merge_transcript & markdown_formatter)
        manifest_path = f"A:\\manifests\\{task_id}.json"
        chunks_manifest_path = f"A:\\manifests\\{task_id}_chunks.json"
        if not os.path.exists(manifest_path):
            dummy_manifest = {
                "task_id": task_id,
                "source_name": filename.replace(".txt", ".mp4"),
                "source_path": f"dummy_path\\{filename.replace('.txt', '.mp4')}",
                "status": "chunked",
                "steps": {"stt": "completed"}
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(dummy_manifest, f, ensure_ascii=False)
        
        if not os.path.exists(chunks_manifest_path):
            with open(chunks_manifest_path, "w", encoding="utf-8") as f:
                json.dump([], f)
        
        try:
            # 呼叫我們剛剛寫好的完美隔離腳本
            subprocess.run([sys.executable, "-u", "scripts/local_chunk_refiner.py", "--task_id", task_id], cwd="C:/LocalAI_Workstation", check=True)
            
            # 記錄成功
            completed.append(filename)
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(completed, f, ensure_ascii=False, indent=2)
                
            print(f"[SUCCESS] {filename} 處理成功！")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] {filename} 處理失敗，跳過並繼續下一個。錯誤: {e}")
            continue

if __name__ == "__main__":
    run_batch()
