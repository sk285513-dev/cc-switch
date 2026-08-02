import os
import hashlib
import sqlite3
import time
import subprocess
from pathlib import Path

try:
    from workflow_helper import log_error, log_workflow
except ImportError:
    def log_error(msg): print(f"ERROR: {msg}")
    def log_workflow(msg): print(f"INFO: {msg}")

DB_PATH = "A:\\manifests\\ingestion_ledger.db"
PROCESSED_MD_DIR = "A:\\processed_md"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            fingerprint TEXT PRIMARY KEY,
            file_path TEXT,
            processor TEXT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_fast_fingerprint(file_path: str) -> str:
    """計算快速指紋：檔案大小 + 修改時間 + 前 1MB 特徵"""
    try:
        if not os.path.exists(file_path):
            return None
            
        file_size = os.path.getsize(file_path)
        mtime = int(os.path.getmtime(file_path))
        
        sha256 = hashlib.sha256()
        sha256.update(f"{file_size}_{mtime}".encode('utf-8'))
        
        with open(file_path, 'rb') as f:
            data = f.read(1024 * 1024)
            if data:
                sha256.update(data)
                
        return sha256.hexdigest()
    except Exception as e:
        log_error(f"Failed to compute fingerprint for {file_path}: {e}")
        return None

def check_legacy_processed(file_path: str) -> bool:
    """檢查是否已經存在於舊版的 A:\\processed_md 中，若有則視為已處理"""
    try:
        path_obj = Path(file_path)
        base_name = path_obj.stem
        
        processed_dir = Path(PROCESSED_MD_DIR)
        if not processed_dir.exists():
            return False
            
        # 尋找是否存在包含檔名的 .srt 檔 (這是任務成功的終點標誌)
        for srt_file in processed_dir.glob(f"*{base_name}*.srt"):
            srt_size_kb = srt_file.stat().st_size / 1024
            # 取得時長來評估合理性
            duration_min = 0
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                duration_min = float(res.stdout.strip()) / 60.0
            except:
                pass
            
            if duration_min > 0:
                min_kb = max(5.0, duration_min * 0.6)
                max_kb = max(50.0, duration_min * 5.5)
                if min_kb <= srt_size_kb <= max_kb:
                    return True # 舊歷史中有合法的完成紀錄
            else:
                # 若無法取得時長(例如pdf/純文字)，只要srt存在且大於 1KB 視為有效
                if srt_size_kb > 1.0:
                    return True
        return False
    except Exception:
        return False

def check_name_duplicate(file_path: str) -> bool:
    """檢查檔名是否已經存在於 A:\\manifests 或 A:\\processed_md 中，防止同名不同 hash 的檔案被重複攝入"""
    try:
        path_obj = Path(file_path)
        base_name = path_obj.stem
        # 移除可能的前綴如 [民事訴訟法_ch10]_，只取後面的原始檔名
        import re
        m = re.match(r'^\[.*?\]_(.*)$', base_name)
        core_name = m.group(1) if m else base_name
        
        # 檢查 A:\processed_md
        processed_dir = Path(PROCESSED_MD_DIR)
        if processed_dir.exists():
            for f in processed_dir.glob("*.md"):
                if core_name in f.name:
                    return True
                    
        # 檢查 A:\manifests
        manifests_dir = Path("A:\\manifests")
        if manifests_dir.exists():
            for f in manifests_dir.glob("*.json"):
                if core_name in f.name:
                    return True
        return False
    except Exception:
        return False

def is_already_ingested(file_path: str, auto_migrate: bool = True) -> bool:
    """檢查指紋是否已存在於帳本中"""
    fingerprint = get_fast_fingerprint(file_path)
    if not fingerprint:
        return False
        
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM ledger WHERE fingerprint = ?", (fingerprint,))
        row = cursor.fetchone()
        conn.close()
        
        if row is not None:
            return True
            
        # 如果帳本中沒有，但要求自動繼承舊歷史
        if auto_migrate and check_legacy_processed(file_path):
            log_workflow(f"[Legacy Migration] 發現舊歷史已處理過 {os.path.basename(file_path)}，自動寫入新指紋帳本。")
            record_ingestion(file_path, "legacy_migration")
            return True
            
        # 如果帳本沒有，但檔名高度相似，也視為重複
        if check_name_duplicate(file_path):
            log_workflow(f"[Duplicate Guard] 發現同名檔案已存在，阻擋重複攝入: {os.path.basename(file_path)}")
            return True
            
        return False
    except Exception as e:
        log_error(f"Database read error: {e}")
        return False

def record_ingestion(file_path: str, processor: str):
    """將檔案指紋註冊到帳本中"""
    fingerprint = get_fast_fingerprint(file_path)
    if not fingerprint:
        return
        
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO ledger (fingerprint, file_path, processor) VALUES (?, ?, ?)",
            (fingerprint, os.path.abspath(file_path), processor)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log_error(f"Database write error: {e}")
