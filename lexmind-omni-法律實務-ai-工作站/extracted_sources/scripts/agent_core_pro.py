import os
import re
import requests
import chromadb
import json
from pathlib import Path

class LegalRWSAnalyzer:
    def __init__(self, context_role="lawyer"):
        self.context_role = context_role
        self.const_patterns = [r"\d{3}\s*年\s*憲判字第\s*\d+\s*號", r"(司法院)?釋字第\s*\d+\s*號"]
        self.defense_keywords = ["消滅時效", "時效抗辯", "時效中斷", "過失相抵", "同時履行抗辯", "罹於時效", "時效起算", "追訴權時效", "追訴期"]

    def calculate_score(self, text: str) -> float:
        """核心 RWS 權重算法 (0.0 ~ 1.0)"""
        weight = 20
        text_clean = text.replace(" ", "")

        # 1. 識別憲法與釋字 (Level 1 最高級)
        if any(re.search(p, text) for p in self.const_patterns):
            weight = 95 + (5 if self.context_role in ["lawyer", "judge"] else 0)
        # 2. 識別黃金條文
        elif "民法" in text_clean and any(f"第{n}條" in text_clean for n in ["126", "179", "184", "197", "226", "227", "767"]):
            weight = 110
        elif "刑法" in text_clean and any(f"第{n}條" in text_clean for n in ["80", "185-3", "271", "320", "321", "339"]):
            weight = 110
        elif "行政程序法" in text_clean and any(f"第{n}條" in text_clean for n in ["92", "111", "131"]):
            weight = 110
        # 3. 識別一般法律 (Level 2)
        elif any(x in text_clean for x in ["民法", "刑法", "民事訴訟法", "刑事訴訟法", "行政訴訟法"]):
            weight = 90
        # 4. 識別命令與細則 (Level 3/4)
        elif "細則" in text_clean or "施行細則" in text_clean:
            weight = 50
        elif any(x in text_clean for x in ["要點", "注意事項", "基準", "須知"]):
            weight = 20

        # 5. 時效與核心抗辯加權
        if any(kw in text_clean for kw in self.defense_keywords):
            weight += 20 if self.context_role in ["lawyer", "judge"] else 10

        return min(weight, 120) / 120.0

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

class LocalLegalAgent:
    def __init__(self, context_role="lawyer", db_path=None):
        self.role = context_role
        self.analyzer = LegalRWSAnalyzer(context_role=context_role)
        
        # 動態判定專案根目錄，完美相容本機任何磁碟與目錄路徑
        self.base_dir = Path(__file__).resolve().parent.parent
        
        if db_path is None:
            db_path = str(self.base_dir / "RAGFlow_Datasets")
            
        # 絕對路徑校正
        self.abs_db_path = os.path.abspath(db_path)
        self.chroma_client = chromadb.PersistentClient(path=self.abs_db_path)
        
        # 建立持久化二維 RAG 集合 (改用 Ollama embedding function 以徹底繞過 ONNXRuntime 在 Windows 上的加載崩潰)
        ollama_ef = OllamaEmbeddingFunction()
        self.law_coll = self.chroma_client.get_or_create_collection(
            name="legal_docs", 
            metadata={"hnsw:space": "cosine"},
            embedding_function=ollama_ef
        )
        self.intel_coll = self.chroma_client.get_or_create_collection(
            name="legal_intelligence_vault",
            embedding_function=ollama_ef
        )
        
        self.history_file = str(self.base_dir / "history.json")
        self.memory = self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_memory(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ 記憶檔儲存失敗: {e}")

    def _get_embedding(self, text: str):
        try:
            res = requests.post('http://localhost:11434/api/embeddings', json={'model': 'nomic-embed-text:latest', 'prompt': text}, timeout=30)
            if res.status_code == 200:
                return res.json().get('embedding')
        except Exception as e:
            print(f"⚠️ Embedding API 調用異常: {e}")
        return None

    def _condense_query(self, current_input: str) -> str:
        """多輪對話歷史語意壓縮重構"""
        if not self.memory:
            return current_input
        
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in self.memory[-4:]])
        prompt = (
            "你是一個法律案情文本提煉助手。請將以下的歷史對話紀錄與使用者新提問結合，"
            "壓縮還原成一個包含具體法律糾紛事實、對稱主體與爭點的單一精準檢索句。只需輸出最終檢索句，不要加入多餘旁白。\n\n"
            f"對話歷史：\n{history_text}\n"
            f"最新提問：\n{current_input}"
        )
        try:
            res = requests.post('http://localhost:11434/api/chat', 
                                json={'model': 'deepseek-r1:7b', 'messages': [{'role': 'user', 'content': prompt}], 'stream': False}, timeout=45)
            if res.status_code == 200:
                return res.json()['message']['content'].strip()
        except:
            pass
        return current_input

    def search_hybrid(self, query: str, category_hint: str = "通用", n_results: int = 15):
        """雙重資料庫檢索 + RWS 權重重新排序 (Re-ranking)"""
        query_vec = self._get_embedding(query)
        if not query_vec:
            return []

        # 進行相似度檢索
        res_law = self.law_coll.query(query_embeddings=[query_vec], n_results=n_results)
        res_intel = self.intel_coll.query(query_embeddings=[query_vec], n_results=5)

        combined = []
        
        # 1. 處理法條庫召回
        if res_law and res_law['documents'] and res_law['documents'][0]:
            for d, m, dist in zip(res_law['documents'][0], res_law['metadatas'][0], res_law['distances'][0]):
                sim = 1.0 - dist
                rws = self.analyzer.calculate_score(d)
                # 類別對位加成
                if category_hint != "通用" and m.get('category') == category_hint:
                    rws = min(rws + 0.15, 1.0)
                
                final_score = (0.4 * sim) + (0.6 * rws)
                combined.append({
                    "text": d,
                    "score": round(final_score, 4),
                    "source": m.get('source', '法條'),
                    "level": m.get('level', 5)
                })

        # 2. 處理經驗與智商庫
        if res_intel and res_intel['documents'] and res_intel['documents'][0]:
            for d, m in zip(res_intel['documents'][0], res_intel['metadatas'][0]):
                # 經驗文檔賦予極高權重，引導 AI 養成思考
                combined.append({
                    "text": f"【歷史經驗智商晶片】\n{d}",
                    "score": 1.0,
                    "source": m.get('source', '智商庫'),
                    "level": 1
                })

        # 重新排序
        combined.sort(key=lambda x: x['score'], reverse=True)
        return combined[:5]

    def chat_with_rws(self, user_input: str) -> tuple:
        condensed = self._condense_query(user_input)
        
        # 簡單判定大類
        category_hint = "通用"
        if any(w in condensed for w in ["侵權", "撞", "損害賠償", "欠錢", "返還", "不當得利", "契約"]):
            category_hint = "民事"
        elif any(w in condensed for w in ["告訴", "罪", "被告人", "檢察", "詐欺", "公訴", "起訴"]):
            category_hint = "刑事"
        elif any(w in condensed for w in ["罰單", "處分", "扣押", "訴願", "稅", "核課"]):
            category_hint = "行政"
            
        evidence = self.search_hybrid(condensed, category_hint=category_hint)
        context_str = "\n".join([f"[{i+1}] {e['text']} (RWS 綜效得分: {e['score']})" for i, e in enumerate(evidence)])

        system_instruction = (
            "你是一位精通臺灣裁判實務、擁有「老律師與老法官靈魂」的資深 AI 法律特助。\n"
            f"目前你採取『{self.role}』的訴訟視角進行邏輯涵攝與答辯策略推論。\n"
            "請基於下方由 RWS 系統篩選、按重要性高低排序的法律事件證據、判例摘要及條文：\n\n"
            f"{context_str}\n\n"
            "【警示規則與法意要求】：\n"
            "1. 若證據中包含『消滅時效』且經對位本案事實過期，你必須直接在回答的第一段最開頭以『紅字或極度醒目格式』發出最嚴厲的法律截止警告，提醒當事人程序的程序保命符。\n"
            "2. 答題必須採取正統的法律實務「三段論法」（找爭點 -> 敘明適用法規 -> 涵攝事實給出結論與下一步救濟途徑）。\n"
            "3. 確保使用台灣繁體中文法律用語。嚴禁使用大陸詞彙如『公安』、『檢察院』、『被告人』。"
        )

        messages = [
            {"role": "system", "content": system_instruction}
        ]
        # 追加最近幾輪歷史
        messages.extend(self.memory[-6:])
        messages.append({"role": "user", "content": user_input})

        try:
            res = requests.post('http://localhost:11434/api/chat', 
                                json={'model': 'deepseek-r1:7b', 'messages': messages, 'stream': False}, timeout=120)
            if res.status_code == 200:
                reply = res.json()['message']['content']
                # 追加到歷史紀錄中
                self.memory.append({"role": "user", "content": user_input})
                self.memory.append({"role": "assistant", "content": reply})
                self._save_memory()
                return reply, evidence
        except Exception as e:
            return f"❌ 呼叫 LLM 服務失敗，請確認本地 Ollama (deepseek-r1:7b) 正在運行：{e}", []

        return "（未取得本地 LLM 回應，請確認連接正常。）", []