# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: run_workflow.py, stt_runner.py, merge_transcript.py, markdown_formatter.py
# Shared State: task manifests (*.json), chunks manifests (*_chunks.json)
#
# [LexMind V6 Ironclad Compliance]
# - Rule 3 : 本檔案以 UTF-8-SIG 儲存
# - Rule 4 : 讀檔一律 errors="replace"
# - Rule 5 : 不硬抓 JSON 欄位
# - Rule 11: JSON 寫入 ensure_ascii=True
# - JSON 寫入為純淨 utf-8（黃金基準步驟四），含 flush + fsync + os.replace 原子替換 + PermissionError 指數退避與抖動

import json
import os
import random
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

    def __init__(self, manifest_path, timeout: int = 30):
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

    def read(self):
        """
        [Rule 4] utf-8-sig + errors="replace"（可同時容忍 BOM 與非 BOM 檔案）。
        讀取失敗回傳 {}，不拋例外；呼叫端可用 `mm.read() or []` 處理清單型 manifest。
        """
        if not self.manifest_path.exists():
            return {}
        try:
            with open(self.manifest_path, "r", encoding="utf-8-sig", errors="replace") as f:
                return json.load(f)
        except Exception as e:
            try:
                print(f"[ManifestManager] Warning: failed to read {self.manifest_path}: {e}")
            except Exception:
                pass
            return {}

    def write(self, data):
        """
        [Rule 11] ensure_ascii=True
        純淨 utf-8（無 BOM，黃金基準步驟四）+ flush + fsync + os.replace + PermissionError 指數退避與隨機抖動。
        """
        pid = os.getpid()
        tid = threading.get_ident()
        tmp_path = self.manifest_path.with_suffix(f'.json.tmp.{pid}.{tid}')

        replaced = False
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass

            # Retry loop for Windows (Antivirus or search indexer might briefly hold the file)
            retries = 30
            for i in range(retries):
                try:
                    os.replace(tmp_path, self.manifest_path)
                    replaced = True
                    return
                except PermissionError as e:
                    if i == retries - 1:
                        try:
                            print(f"[ManifestManager] Fatal: Could not replace file after {retries} retries: {e}")
                        except Exception:
                            pass
                        raise
                    sleep_time = (0.05 * (1.2 ** i)) + random.uniform(0.01, 0.05)
                    time.sleep(min(sleep_time, 2.0))
        finally:
            # [V3] .tmp 檔案清道夫：任何失敗路徑都不得留下殘骸
            if not replaced and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def update_manifest(manifest_path, update_fn) -> bool:
    """
    唯一合法的「讀取 -> 修改 -> 寫入」入口。
    整段流程都在 file lock + thread lock 之內完成，
    禁止呼叫端自行 open() -> json.load() -> 修改 -> 覆寫。
    """
    try:
        with ManifestManager(manifest_path) as mm:
            data = mm.read()
            if not data:
                return False
            update_fn(data)
            mm.write(data)
            return True
    except Timeout:
        try:
            print(f"[ManifestManager] Error: Timeout waiting for lock on {manifest_path}")
        except Exception:
            pass
        return False
    except Exception as e:
        try:
            print(f"[ManifestManager] Error: update_manifest failed on {manifest_path}: {e}")
        except Exception:
            pass
        return False
