import sqlite3
import json
import time
import asyncio

class SQLiteTaskQueue:
    def __init__(self, db_path="A:\\logs\\task_queue.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        # timeout=5.0：遇到併發寫入鎖定時，自動重試等待 5 秒，不直接報錯
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        
        # 【核心關鍵】開啟 WAL 模式，大幅提升多進程併發讀寫效能
        conn.execute("PRAGMA journal_mode=WAL;")
        # NORMAL 模式能在效能與安全間取得平衡，比預設的 FULL 更快
        conn.execute("PRAGMA synchronous=NORMAL;")
        # 增加一點快取記憶體 (例如 10000 頁) 提升查詢速度
        conn.execute("PRAGMA cache_size=-10000;") 
        return conn

    def _init_db(self):
        """初始化資料表與索引"""
        with self._get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    payload TEXT NOT NULL,
                    worker_id TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            ''')
            # 建立複合索引：加速尋找 pending 任務與依時間排序
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status_created 
                ON tasks(status, created_at)
    async def push(self, payload_dict: dict, max_queue_size: int = 1000):
        """將新任務推入佇列 (相當於改寫 JSON)"""
        # 【修補 Issue 33：系統效能】移除 time.sleep(5) 避免阻塞非同步池，全面非同步化
        while True:
            with self._get_conn() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
                count = cursor.fetchone()[0]
                if count < max_queue_size:
                    break
            print(f"⚠️ [Backpressure] 佇列已滿 ({count} >= {max_queue_size})，觸發應用層背壓防護，暫停接收新任務...")
            await asyncio.sleep(5)
            
        payload_str = json.dumps(payload_dict)
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO tasks (payload, created_at, updated_at) VALUES (?, ?, ?)",
                (payload_str, now, now)
            )

    def pop(self, worker_id: str):
        """
        【原子化搶任務】
        取代 Mutex：保證只有一個 worker 能搶到該筆資料。
        (注意: UPDATE ... RETURNING 需要 SQLite 3.35.0+, Python 3.10+ 預設皆支援)
        """
        now = time.time()
        with self._get_conn() as conn:
            cursor = conn.execute('''
                UPDATE tasks 
                SET status = 'processing', worker_id = ?, updated_at = ?
                WHERE id = (
                    SELECT id FROM tasks 
                    WHERE status = 'pending' 
                    ORDER BY created_at ASC 
                    LIMIT 1
                )
                RETURNING id, payload;
            ''', (worker_id, now))
            
            row = cursor.fetchone()
            if row:
                return {"id": row["id"], "payload": json.loads(row["payload"])}
            return None

    def complete(self, task_id: int):
        """標記任務完成"""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'completed', updated_at = ? WHERE id = ?",
                (now, task_id)
            )

    def fail(self, task_id: int):
        """標記任務失敗"""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'failed', updated_at = ? WHERE id = ?",
                (now, task_id)
            )
            
    def requeue_dead_tasks(self, timeout_seconds=3600):
        """將崩潰卡在 processing 太久的任務拉回 pending"""
        threshold = time.time() - timeout_seconds
        with self._get_conn() as conn:
            conn.execute('''
                UPDATE tasks 
                SET status = 'pending', worker_id = NULL
                WHERE status = 'processing' AND updated_at < ?
            ''', (threshold,))

