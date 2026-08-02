import json
import json
import os
import threading
import time
from pathlib import Path
from filelock import FileLock, Timeout

_thread_locks = {}
_thread_locks_lock = threading.Lock()

def get_thread_lock(path_str):
    # Normalize path to ensure all variations point to the same lock
    norm_path = os.path.normpath(os.path.abspath(path_str))
    with _thread_locks_lock:
        if norm_path not in _thread_locks:
            _thread_locks[norm_path] = threading.Lock()
        return _thread_locks[norm_path]

class ManifestManager:
    """
    A unified manager for reading and writing task manifest JSON files.
    Uses filelock to prevent race conditions across multiple processes.
    Uses threading.Lock to prevent race conditions across threads in the same process.
    Uses atomic replace to prevent file corruption during writes, with retries for Windows AV locks.
    """
    def __init__(self, manifest_path: str | Path, timeout: int = 30):
        self.manifest_path = Path(manifest_path)
        self.lock_path = self.manifest_path.with_suffix('.json.lock')
        self.timeout = timeout
        
        self.file_lock = FileLock(str(self.lock_path), timeout=self.timeout)
        self.thread_lock = get_thread_lock(str(self.manifest_path))

    def __enter__(self):
        self.thread_lock.acquire()
        try:
            self.file_lock.acquire()
        except Exception:
            self.thread_lock.release()
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.file_lock.release()
        finally:
            self.thread_lock.release()
        
    def read(self) -> dict:
        if not self.manifest_path.exists():
            return {}
        try:
            return json.load(self.manifest_path)
        except Exception as e:
            print(f"[ManifestManager] Warning: failed to read {self.manifest_path}: {e}")
            return {}
            
    def write(self, data: dict):
        pid = os.getpid()
        tid = threading.get_ident()
        tmp_path = self.manifest_path.with_suffix(f'.json.tmp.{pid}.{tid}')
        
        with open(tmp_path, "w", encoding="utf-8-sig") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
        # Retry loop for Windows (Antivirus or search indexer might briefly hold the file)
        retries = 20
        for i in range(retries):
            try:
                os.replace(tmp_path, self.manifest_path)
                break
            except PermissionError as e:
                if i == retries - 1:
                    print(f"[ManifestManager] Fatal: Could not replace file after {retries} retries: {e}")
                    raise
                time.sleep(0.05)

def update_manifest(manifest_path: str | Path, update_fn) -> bool:
    try:
        with ManifestManager(manifest_path) as mm:
            data = mm.read()
            if not data:
                return False
            update_fn(data)
            mm.write(data)
            return True
    except Timeout:
        print(f"[ManifestManager] Error: Timeout waiting for lock on {manifest_path}")
        return False

