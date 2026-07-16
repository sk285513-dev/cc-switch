import os
import time
import requests
import chromadb
from pathlib import Path

class OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model_name="nomic-embed-text:latest", host="http://localhost:11434"):
        self.model_name = model_name
        self.host = host

    def __call__(self, input: list) -> list:
        embeddings = []
        for text in input:
            try:
                import requests
                res = requests.post(f'{self.host}/api/embeddings', json={'model': self.model_name, 'prompt': text}, timeout=30)
                if res.status_code == 200:
                    embeddings.append(res.json().get('embedding'))
                else:
                    embeddings.append([0.0] * 768)
            except Exception as e:
                print(f"⚠️ Custom Ollama Embedding Error: {e}")
                embeddings.append([0.0] * 768)
        return embeddings

class LawDigesterPro:
    def __init__(self, db_path=None):
        if db_path is None:
            # 動態消化數據路徑調整
            base_dir = Path(__file__).resolve().parent.parent
            db_path = str(base_dir / "RAGFlow_Datasets")
        self.client = chromadb.PersistentClient(path=db_path)
        ollama_ef = OllamaEmbeddingFunction()
        self.intel_coll = self.client.get_or_create_collection(
            name="legal_intelligence_vault",
            embedding_function=ollama_ef
        )
        self.embed_url = 'http://localhost:11434/api/embeddings'
        self.llm_url = 'http://localhost:11434/api/chat'

    def _get_embedding(self, text):
        try:
            res = requests.post(self.embed_url, json={'model': 'nomic-embed-text:latest', 'prompt': text}, timeout=30)
            return res.json().get('embedding')
        except:
            return None

    def digest_large_asset(self, text, source_name, chunk_size=2000, overlap=150):
        """對於長篇判例或巨量錄音逐字稿，採用安全遞歸切塊與背景上下文防忘機制"""
        if not text or not text.strip():
            return
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += (chunk_size - overlap)
            
        print(f"🧠 發現長文本 {source_name} (原長 {len(text)} 字)，自適應切割為 {len(chunks)} 段進行遞歸深度消化...")

        for idx, chunk in enumerate(chunks):
            context_prefix = f"【材料來源：{source_name} | 連續軌跡第 {idx+1}/{len(chunks)} 頁】\n"
            
            prompt = (
                f"{context_prefix}\n"
                "你是一位擁有一雙火眼金睛的老律師。請閱讀上述法律文本斷章，"
                "並用最凝聚的台灣實務語感將其「消化」成晶片式的經驗摘要。\n"
                "請明確整理出：\n"
                "1. 核心法律爭點為何：\n"
                "2. 法官/教授的推理邏輯與引用法條：\n"
                "3. 最關鍵的實務定調結論：\n"
                f"\n本段原文：\n{chunk}"
            )
            try:
                # 調用本地 deepseek 推理
                res = requests.post(self.llm_url, 
                                    json={'model': 'deepseek-r1:7b', 'messages': [{'role': 'user', 'content': prompt}], 'stream': False},
                                    timeout=90)
                if res.status_code == 200:
                    digested_text = res.json()['message']['content']
                    
                    # 進行嵌入並寫入智商庫
                    combo_text = f"【消化精華晶片：{source_name}】\n{digested_text}\n\n【原始段落軌跡】：\n{chunk}"
                    vec = self._get_embedding(combo_text)
                    if vec:
                        self.intel_coll.add(
                            ids=[f"digested_{source_name}_{idx}_{os.urandom(2).hex()}"],
                            embeddings=[vec],
                            documents=[combo_text],
                            metadatas=[{"source": source_name, "type": "intelligence", "chunk_idx": idx}]
                        )
                # 微歇以冷卻 GPU 
                time.sleep(0.5)
            except Exception as e:
                print(f"❌ 消化區段 {idx} 出現故障: {e}")

    def run_folder_digestion(self, folder_path):
        folder = Path(folder_path)
        if not folder.exists():
            return
        for f in folder.rglob("*.txt"):
            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                self.digest_large_asset(file.read(), f.name)