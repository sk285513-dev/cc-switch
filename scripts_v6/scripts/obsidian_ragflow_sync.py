#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian → RAGFlow 自動同步引擎
================================
掃描 Obsidian Vault，將新增/修改的 .md 檔案同步上傳到 RAGFlow 知識庫。
使用 SHA-256 hash 進行增量同步，避免重複上傳。

Usage:
  python obsidian_ragflow_sync.py                    # 單次同步
  python obsidian_ragflow_sync.py --watch             # 持續監控模式
  python obsidian_ragflow_sync.py --full-resync       # 全量重新同步
  python obsidian_ragflow_sync.py --status            # 查看同步狀態
"""

import os
import sys
import json
import hashlib
import time
import argparse
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --- 第三方套件 ---
try:
    import requests
except ImportError:
    print("需要安裝 requests: pip install requests")
    sys.exit(1)

# ── 路徑設定 ──────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent  # LexMind-Omni 根目錄
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = DATA_DIR / "obsidian_sync_config.json"
INDEX_PATH = DATA_DIR / "obsidian_sync_index.json"
LOG_PATH = DATA_DIR / "obsidian_sync.log"

# ── 日誌設定 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        ConcurrentRotatingFileHandler(LOG_PATH, mode=\"a\", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("obsidian-ragflow-sync")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 設定管理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_config() -> dict:
    """讀取並驗證設定檔"""
    if not CONFIG_PATH.exists():
        log.error(f"找不到設定檔: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # 驗證必要欄位
    missing = []
    if not cfg.get("vault_path"):
        missing.append("vault_path")
    if not cfg.get("ragflow_base_url"):
        missing.append("ragflow_base_url")
    if not cfg.get("api_key"):
        missing.append("api_key")
    if missing:
        log.error(f"設定檔缺少必要欄位: {', '.join(missing)}")
        log.error("請先在 data/obsidian_sync_config.json 填入 api_key")
        sys.exit(1)

    vault = Path(cfg["vault_path"])
    if not vault.exists():
        log.error(f"Obsidian Vault 路徑不存在: {vault}")
        sys.exit(1)

    return cfg


def load_index() -> dict:
    """讀取同步狀態索引"""
    if not INDEX_PATH.exists():
        return {"files": {}, "last_full_scan": None, "sync_stats": {
            "total_synced": 0, "total_deleted": 0, "total_errors": 0, "last_sync_at": None
        }}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(index: dict):
    """儲存同步狀態索引"""
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. RAGFlow API 客戶端
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class RAGFlowClient:
    """RAGFlow HTTP API 封裝"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def test_connection(self) -> bool:
        """測試 API 連線與金鑰有效性"""
        try:
            resp = self.session.get(f"{self.base_url}/api/v1/datasets", params={"page": 1, "page_size": 1})
            if resp.status_code == 200:
                log.info("✅ RAGFlow API 連線成功")
                return True
            elif resp.status_code == 401:
                log.error("❌ RAGFlow API Key 無效 (401 Unauthorized)")
                return False
            else:
                log.error(f"❌ RAGFlow API 回傳異常狀態碼: {resp.status_code}")
                return False
        except requests.ConnectionError:
            log.error(f"❌ 無法連線到 RAGFlow: {self.base_url}")
            return False

    def list_datasets(self) -> list:
        """列出所有知識庫"""
        resp = self.session.get(f"{self.base_url}/api/v1/datasets", params={"page": 1, "page_size": 100})
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    def create_dataset(self, name: str, description: str = "") -> str:
        """建立新知識庫，回傳 dataset_id"""
        resp = self.session.post(f"{self.base_url}/api/v1/datasets", json={
            "name": name,
            "description": description,
        })
        resp.raise_for_status()
        data = resp.json()
        dataset_id = data.get("data", {}).get("id", "")
        log.info(f"  ✅ 建立知識庫 \"{name}\" -> {dataset_id}")
        return dataset_id

    def upload_document(self, dataset_id: str, file_path: Path, metadata: dict = None) -> str:
        """上傳文件到指定知識庫，回傳 document_id"""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"

        # 使用 multipart 上傳
        headers = {"Authorization": self.session.headers["Authorization"]}
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "text/markdown")}
            resp = requests.post(url, headers=headers, files=files)

        resp.raise_for_status()
        data = resp.json()
        docs = data.get("data", [])
        if docs and isinstance(docs, list):
            doc_id = docs[0].get("id", "")
        elif isinstance(docs, dict):
            doc_id = docs.get("id", "")
        else:
            doc_id = ""
        return doc_id

    def delete_documents(self, dataset_id: str, doc_ids: list):
        """刪除知識庫中的文件"""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"
        resp = self.session.delete(url, json={"ids": doc_ids})
        resp.raise_for_status()

    def trigger_parsing(self, dataset_id: str, doc_ids: list):
        """觸發文件解析 (chunking + embedding)"""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks"
        resp = self.session.post(url, json={"document_ids": doc_ids})
        resp.raise_for_status()

    def list_documents(self, dataset_id: str) -> list:
        """列出知識庫中的所有文件"""
        resp = self.session.get(
            f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
            params={"page": 1, "page_size": 1000}
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("docs", [])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 同步引擎
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def compute_hash(file_path: Path) -> str:
    """計算檔案 SHA-256"""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def classify_file(rel_path: str, folder_map: dict) -> str:
    """根據路徑分類到對應的 dataset 類型"""
    parts = Path(rel_path).parts
    for part in parts:
        part_lower = part.lower()
        for keyword, dataset_type in folder_map.items():
            if keyword.lower() in part_lower:
                return dataset_type
    return "default"


def scan_vault(vault_path: Path, extensions: list, ignore_patterns: list) -> dict:
    """掃描 Obsidian Vault，回傳 {相對路徑: 絕對路徑}"""
    found = {}
    for root, dirs, files in os.walk(vault_path):
        # 過濾忽略的目錄
        dirs[:] = [d for d in dirs if not any(
            p.lower() in d.lower() for p in ignore_patterns
        )]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                abs_path = Path(root) / fname
                rel_path = str(abs_path.relative_to(vault_path)).replace("\\", "/")
                found[rel_path] = abs_path
    return found


def ensure_datasets(client: RAGFlowClient, config: dict) -> dict:
    """確保所有需要的 RAGFlow 知識庫存在，回傳更新後的 dataset_map"""
    dataset_map = config.get("dataset_map", {})
    existing = client.list_datasets()
    existing_names = {ds.get("name", ""): ds.get("id", "") for ds in existing}

    dataset_defs = {
        "default": ("LexMind-Obsidian-通用", "Obsidian 通用筆記"),
        "legal": ("LexMind-Obsidian-法律", "Obsidian 法律筆記"),
        "code": ("LexMind-Obsidian-程式碼", "Obsidian 程式碼與開發筆記"),
        "research": ("LexMind-Obsidian-研究", "Obsidian 研究筆記"),
    }

    updated = False
    for key, (name, desc) in dataset_defs.items():
        if not dataset_map.get(key):
            if name in existing_names:
                dataset_map[key] = existing_names[name]
                log.info(f"  📎 找到現有知識庫 \"{name}\" -> {dataset_map[key]}")
            else:
                dataset_map[key] = client.create_dataset(name, desc)
            updated = True

    if updated:
        config["dataset_map"] = dataset_map
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    return dataset_map


def run_sync(config: dict, full_resync: bool = False):
    """執行一次同步"""
    vault_path = Path(config["vault_path"])
    client = RAGFlowClient(config["ragflow_base_url"], config["api_key"])

    # 測試連線
    if not client.test_connection():
        return {"success": False, "error": "RAGFlow 連線失敗"}

    # 確保知識庫存在
    dataset_map = ensure_datasets(client, config)
    folder_map = config.get("folder_to_dataset", {})

    # 載入索引
    index = load_index()
    if full_resync:
        log.info("🔄 全量重新同步模式 - 清除索引")
        index["files"] = {}

    # 掃描 Vault
    extensions = config.get("watch_extensions", [".md"])
    ignore_patterns = config.get("ignore_patterns", [".obsidian", ".trash"])
    vault_files = scan_vault(vault_path, extensions, ignore_patterns)
    log.info(f"📂 掃描到 {len(vault_files)} 個 Markdown 檔案")

    stats = {"uploaded": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}

    # --- 同步新增/修改 ---
    for rel_path, abs_path in vault_files.items():
        try:
            file_hash = compute_hash(abs_path)
            file_size = abs_path.stat().st_size

            # 跳過空檔案
            if file_size == 0:
                stats["skipped"] += 1
                continue

            existing = index["files"].get(rel_path)
            dataset_type = classify_file(rel_path, folder_map)
            target_dataset_id = dataset_map.get(dataset_type, dataset_map.get("default", ""))

            if not target_dataset_id:
                log.warning(f"  ⚠️ 找不到 dataset_id for type={dataset_type}, 跳過: {rel_path}")
                stats["skipped"] += 1
                continue

            if existing and existing.get("hash") == file_hash:
                stats["skipped"] += 1
                continue  # Hash 相同，不需同步

            # 如果是更新（hash 變了），先刪除舊的
            if existing and existing.get("doc_id"):
                old_dataset_id = existing.get("dataset_id", target_dataset_id)
                try:
                    client.delete_documents(old_dataset_id, [existing["doc_id"]])
                    log.info(f"  🗑️ 刪除舊版: {rel_path}")
                except Exception as e:
                    log.warning(f"  ⚠️ 刪除舊版失敗: {e}")

            # 上傳新版
            log.info(f"  📤 上傳: {rel_path} → {dataset_type}")
            doc_id = client.upload_document(target_dataset_id, abs_path)

            if doc_id:
                # 觸發解析
                try:
                    client.trigger_parsing(target_dataset_id, [doc_id])
                    log.info(f"  ⚙️ 觸發解析: {rel_path}")
                except Exception as e:
                    log.warning(f"  ⚠️ 觸發解析失敗 (文件已上傳): {e}")

                index["files"][rel_path] = {
                    "doc_id": doc_id,
                    "dataset_id": target_dataset_id,
                    "dataset_type": dataset_type,
                    "hash": file_hash,
                    "size": file_size,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
                if existing:
                    stats["updated"] += 1
                else:
                    stats["uploaded"] += 1
            else:
                log.error(f"  ❌ 上傳失敗（無 doc_id）: {rel_path}")
                stats["errors"] += 1

        except Exception as e:
            log.error(f"  ❌ 同步失敗 [{rel_path}]: {e}")
            stats["errors"] += 1

    # --- 同步刪除（Vault 中已不存在的檔案）---
    indexed_paths = set(index["files"].keys())
    vault_paths = set(vault_files.keys())
    deleted_paths = indexed_paths - vault_paths

    for rel_path in deleted_paths:
        try:
            entry = index["files"][rel_path]
            if entry.get("doc_id") and entry.get("dataset_id"):
                client.delete_documents(entry["dataset_id"], [entry["doc_id"]])
                log.info(f"  🗑️ Vault 中已刪除，同步移除: {rel_path}")
            del index["files"][rel_path]
            stats["deleted"] += 1
        except Exception as e:
            log.error(f"  ❌ 刪除同步失敗 [{rel_path}]: {e}")
            stats["errors"] += 1

    # 更新統計
    index["last_full_scan"] = datetime.now(timezone.utc).isoformat()
    index["sync_stats"]["total_synced"] += stats["uploaded"] + stats["updated"]
    index["sync_stats"]["total_deleted"] += stats["deleted"]
    index["sync_stats"]["total_errors"] += stats["errors"]
    index["sync_stats"]["last_sync_at"] = datetime.now(timezone.utc).isoformat()
    save_index(index)

    log.info(f"✅ 同步完成: 新增={stats['uploaded']}, 更新={stats['updated']}, "
             f"刪除={stats['deleted']}, 跳過={stats['skipped']}, 錯誤={stats['errors']}")
    return {"success": True, "stats": stats}


def show_status():
    """顯示目前同步狀態"""
    index = load_index()
    files = index.get("files", {})
    stats = index.get("sync_stats", {})
    print("\n" + "=" * 60)
    print("📊 Obsidian → RAGFlow 同步狀態")
    print("=" * 60)
    print(f"  已索引檔案:   {len(files)} 筆")
    print(f"  累計同步:     {stats.get('total_synced', 0)} 次")
    print(f"  累計刪除:     {stats.get('total_deleted', 0)} 次")
    print(f"  累計錯誤:     {stats.get('total_errors', 0)} 次")
    print(f"  最後同步時間: {stats.get('last_sync_at', '從未')}")
    print(f"  最後全量掃描: {index.get('last_full_scan', '從未')}")
    print()
    if files:
        # 按 dataset_type 分組統計
        by_type = {}
        for path, info in files.items():
            t = info.get("dataset_type", "unknown")
            by_type.setdefault(t, []).append(path)
        print("  📂 按知識庫類型分佈:")
        for t, paths in sorted(by_type.items()):
            print(f"     {t}: {len(paths)} 筆")
    print("=" * 60 + "\n")


def watch_mode(config: dict):
    """持續監控模式"""
    interval = config.get("sync_interval_seconds", 30)
    log.info(f"👁️ 啟動持續監控模式 (每 {interval} 秒掃描)")
    log.info("   按 Ctrl+C 停止\n")
    try:
        while True:
            run_sync(config)
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("\n⏹️ 監控已停止")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. CLI 入口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    parser = argparse.ArgumentParser(description="Obsidian → RAGFlow 自動同步引擎")
    parser.add_argument("--watch", action="store_true", help="持續監控模式")
    parser.add_argument("--full-resync", action="store_true", help="全量重新同步")
    parser.add_argument("--status", action="store_true", help="查看同步狀態")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    config = load_config()

    if args.watch:
        watch_mode(config)
    else:
        result = run_sync(config, full_resync=args.full_resync)
        if not result.get("success"):
            sys.exit(1)


if __name__ == "__main__":
    main()
