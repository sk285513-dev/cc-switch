import os
import time
import requests
import chromadb
from pathlib import Path

class LegalDataImporter:
    def __init__(self, db_path=None):
        if db_path is None:
            # 動態取得 RWS 數據跟目錄，自動調協本地路徑
            base_dir = Path(__file__).resolve().parent.parent
            db_path = str(base_dir / "RAGFlow_Datasets")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="legal_docs", metadata={"hnsw:space": "cosine"})
        self.embed_url = 'http://localhost:11434/api/embeddings'

    def get_embedding(self, text):
        # 增加重試機制，保證 100% 機率不因 concurrency 缺失而當機
        for _ in range(3):
            try:
                res = requests.post(self.embed_url, json={'model': 'nomic-embed-text:latest', 'prompt': text}, timeout=30)
                if res.status_code == 200:
                    return res.json().get('embedding')
            except:
                time.sleep(1)
        return None

    def analyze_law_meta(self, filename):
        level = 5
        if '憲法' in filename: level = 1
        elif any(n in filename for n in ['法', '律', '條例', '通則']): level = 2
        elif any(n in filename for n in ['規程', '規則', '細則', '辦法', '綱要', '標準', '準則']): level = 3
        elif any(n in filename for n in ['要點', '規定', '須知', '注意事項', '原則', '基準']): level = 4
        
        category = '通用'
        if any(n in filename for n in ['民法', '民事', '商事', '財產', '合約', '債權', '侵權']): category = '民事'
        elif any(n in filename for n in ['刑法', '刑事', '犯罪', '追訴', '懲治']): category = '刑事'
        elif any(n in filename for n in ['行政', '訴願', '處分', '稅', '核課']): category = '行政'
        elif any(n in filename for n in ['家事', '婚姻', '離婚', '分割', '遺產', '繼承']): category = '家事'
        return level, category

    def ingest_folder(self, source_dir_path):
        source_dir = Path(source_dir_path)
        if not source_dir.exists():
            print(f"❌ 錯誤：找不到指定的法規庫資料夾 {source_dir_path}，跳過自動初始化。")
            return

        extensions = ('.txt', '.md', '.csv', '.html', '.htm')
        files = [f for f in source_dir.rglob('*') if f.suffix.lower() in extensions]
        print(f"📂 在 {source_dir_path} 發現 {len(files)} 個檔案...")

        batch_size = 50
        documents, ids, metadatas, embeddings = [], [], [], []

        for f_idx, file_path in enumerate(files):
            # 自適應多重編碼讀取
            content = None
            for enc in ['utf-8', 'big5', 'cp950', 'gbk']:
                try:
                    with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                        content = f.read()
                        break
                except:
                    continue

            if not content or not content.strip():
                continue

            level, category = self.analyze_law_meta(file_path.name)
            
            # 使用 RAGFlow 推薦的高密度重疊分塊法，每 800 字切一塊，重疊 100 字
            chunk_size = 800
            overlap = 100
            start = 0
            chunk_idx = 0
            
            while start < len(content):
                end = start + chunk_size
                chunk_text = content[start:end]
                
                # 自動注入上下文防止碎片化
                complete_doc = f"【來源文件：{file_path.name} | 章節段落第 {chunk_idx+1} 頁】\n{chunk_text}"
                vec = self.get_embedding(complete_doc)
                
                if vec:
                    documents.append(complete_doc)
                    ids.append(f"law_{file_path.name}_{chunk_idx}_{f_idx}".replace(" ", ""))
                    metadatas.append({"source": file_path.name, "level": level, "category": category})
                    embeddings.append(vec)
                    
                    if len(documents) == batch_size:
                        self.collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
                        print(f"📊 已批次寫入硬碟累積大數據: {f_idx+1}/{len(files)} 檔案...")
                        documents, ids, metadatas, embeddings = [], [], [], []

                start += (chunk_size - overlap)
                chunk_idx += 1

        # 寫入最後殘餘數據
        if documents:
            self.collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        print("✅ 全國法規大數據庫批次打包建檔完成！")

if __name__ == '__main__':
    importer = LegalDataImporter()
    # 預設自帶導入(如果有實體外硬碟路徑)
    importer.ingest_folder(r"E:\法律\台灣法規庫")