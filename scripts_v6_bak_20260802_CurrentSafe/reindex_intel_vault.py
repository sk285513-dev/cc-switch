import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8-sig', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8-sig', errors='replace')
import json
import time
import requests
import chromadb
from pathlib import Path
import re

def reindex_all_md_files():
    base_dir = Path(r"C:\LocalAI_Workstation")
    processed_dir = Path(r"A:\processed_md")
    db_path = str(base_dir / "vector_db")
    
    # 初始化 ChromaDB
    try:
        client = chromadb.PersistentClient(path=db_path)
        # 強制清空舊有的 collection，確保 768 維度的 Gemini 向量空間乾淨無污染
        try:
            print("正在嘗試刪除舊有資料庫...")
            client.delete_collection(name="legal_intelligence_vault")
            print("🗑️ 已清空舊有資料庫集合 (legal_intelligence_vault)。")
        except Exception as e:
            print(f"嘗試刪除失敗 (可能原本就不存在): {e}")
            pass
        print("準備建立新資料庫...")
        intel_coll = client.get_or_create_collection(name="legal_intelligence_vault")
        print("✅ 建立成功！")
    except Exception as e:
        print(f"❌ 無法連接或建立向量資料庫: {e}")
        return

    # 載入 QuotaManager 進行金鑰輪替，繞過免費層次數限制
    try:
        sys.path.append(r"C:\LocalAI_Workstation")
        from scripts_v6.quota_manager import QuotaManager
        qm = QuotaManager()
        qm.reset_all_keys()
    except Exception as e:
        print(f"❌ 無法載入 QuotaManager: {e}")
        return

    def _get_embedding(text, retry=10):
        for _ in range(retry):
            try:
                key = qm.acquire_key()
                res = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={key}",
                    json={"model": "models/gemini-embedding-2", "content": {"parts": [{"text": text}]}},
                    timeout=10
                )
                if res.status_code == 200:
                    return res.json().get('embedding', {}).get('values')
                else:
                    print(f"⚠️ Gemini API 錯誤 ({res.status_code}): {res.text}")
                    if "401" in res.text or "403" in res.text:
                        qm.mark_exhausted(key)
                    elif "429" in res.text:
                        time.sleep(10)
            except Exception as e:
                print(f"⚠️ 獲取向量失敗: {e}")
                time.sleep(2)
        return None

    if not processed_dir.exists():
        print(f"❌ 找不到目錄: {processed_dir}")
        return

    md_files = list(processed_dir.rglob("*.md"))
    total_files = len(md_files)
    print(f"🔍 找到 {total_files} 個已處理的 Markdown 檔案。準備注入向量資料庫...")

    success_cnt = 0

    for idx, fpath in enumerate(md_files):
        stem = fpath.stem
        
        # 解析檔名 [class_name_lesson_name]_...
        # 例如: [民事訴訟法ˋ_ch10]_預約 10 2024-09-30 14-02-24-012
        m = re.match(r'\[(.*?)_(.*?)\]_(.*)', stem)
        if m:
            class_name = m.group(1).replace("ˋ", "").strip()
            lesson_name = m.group(2).strip()
        else:
            class_name = "未分類課程"
            lesson_name = stem
            
        print(f"[{idx+1}/{total_files}] 正在處理: {class_name} - {lesson_name}...")
        
        try:
            with open(fpath, "r", encoding="utf-8-sig", errors="ignore") as file:
                content = file.read()
        except Exception as e:
            print(f"❌ 讀取檔案失敗: {fpath} - {e}")
            continue

        # 為了讓 Dashboard 統計正確且不重複，我們為每個檔案插入一個代表性的 Chunk。
        # 由於原始檔案已經具備 RAG 摘要，我們只取前 2000 字作為核心特徵。
        safe_text = content[:2000]
        doc_content = f"【教材精華紀錄】\n{class_name} - {lesson_name}\n\n{safe_text}"
        
        # 檢查是否已存在
        try:
            existing = intel_coll.get(where={"source": stem})
            if existing and existing.get("ids") and len(existing["ids"]) > 0:
                print(f"ℹ️ 已存在於資料庫，跳過。")
                success_cnt += 1
                continue
        except:
            pass
        
        doc_embedding = _get_embedding(doc_content)
        if doc_embedding:
            try:
                intel_coll.add(
                    ids=[f"local_ref_{stem}_{int(time.time())}"],
                    documents=[doc_content],
                    embeddings=[doc_embedding],
                    metadatas=[{
                        "source": stem,
                        "class_name": class_name,
                        "lesson_name": lesson_name,
                        "type": "summary",
                        "status": "reindexed"
                    }]
                )
                success_cnt += 1
            except Exception as e:
                print(f"❌ 寫入資料庫失敗: {stem} - {e}")

    print(f"\n✅ 重新建檔完成！成功注入 {success_cnt} / {total_files} 筆紀錄。")
    print("👉 請重新整理 Streamlit UI，各科別智商分佈可視框的「已建檔」數量應已更新。")

if __name__ == "__main__":
    reindex_all_md_files()

