import os
import re
import requests
import chromadb
import json
import hashlib
import math
from pathlib import Path

DEFAULT_MERMAID = "graph TD\n    A[\"人: 申訴人\"] -->|諮詢| B[\"事: 法律案件\"]"

# 載入全局 config.json 的單一真理源配置
try:
    from scripts.config_loader import apply_hardware_config
    cfg = apply_hardware_config()
    DEFAULT_LLM_MODEL = cfg.get("ollama_model", "deepseek-r1:7b")
    OLLAMA_HOST = cfg.get("ollama_host", "http://localhost:11434")
except Exception:
    DEFAULT_LLM_MODEL = "deepseek-r1:7b"
    OLLAMA_HOST = "http://localhost:11434"

EMBEDDING_DIM = 768

_CHROMA_CLIENTS = {}

def get_chroma_client(path):
    abs_path = os.path.abspath(path)
    if abs_path not in _CHROMA_CLIENTS:
        _CHROMA_CLIENTS[abs_path] = chromadb.PersistentClient(path=abs_path)
    return _CHROMA_CLIENTS[abs_path]

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
                print(f"[WARNING] Custom Ollama Embedding Error: {e}")
                embeddings.append([0.0] * 768)
        return embeddings

class LocalLegalAgent:
    def __init__(self, context_role="lawyer", db_path=None):
        self.role = context_role
        self.analyzer = LegalRWSAnalyzer(context_role=context_role)
        self.const_patterns = [r"\d{3}\s*年\s*憲判字第\s*\d+\s*號", r"(司法院)?釋字第\s*\d+\s*號"]
        
        # 動態判定專案根目錄，完美相容本機任何磁碟與目錄路徑
        self.base_dir = Path(__file__).resolve().parent.parent
        
        if db_path is None:
            db_path = str(self.base_dir / "RAGFlow_Datasets")
            
        # 絕對路徑校正
        self.abs_db_path = os.path.abspath(db_path)
        self.chroma_client = get_chroma_client(self.abs_db_path)
        
        # 檢測與自動升級 384-dim 到 768-dim (以相容 nomic-embed-text:latest)
        try:
            coll_docs = self.chroma_client.get_collection(name="legal_docs")
            try:
                # 測試 768 維度查詢是否相容
                coll_docs.query(query_embeddings=[[0.0] * 768], n_results=1)
            except Exception as e:
                if "dimension" in str(e).lower() or "expecting embedding" in str(e).lower():
                    print("Deleting old 384-dim legal_docs collection to upgrade to 768-dim nomic-embed-text...")
                    self.chroma_client.delete_collection(name="legal_docs")
                    coll_docs = self.chroma_client.create_collection(name="legal_docs", metadata={"hnsw:space": "cosine"})
            self.law_coll = coll_docs
        except Exception:
            try:
                self.law_coll = self.chroma_client.create_collection(name="legal_docs", metadata={"hnsw:space": "cosine"})
            except Exception:
                self.law_coll = self.chroma_client.get_or_create_collection(name="legal_docs")

        try:
            coll_intel = self.chroma_client.get_collection(name="legal_intelligence_vault")
            try:
                # 測試 768 維度查詢是否相容
                coll_intel.query(query_embeddings=[[0.0] * 768], n_results=1)
            except Exception as e:
                if "dimension" in str(e).lower() or "expecting embedding" in str(e).lower():
                    print("Deleting old 384-dim legal_intelligence_vault collection to upgrade to 768-dim nomic-embed-text...")
                    self.chroma_client.delete_collection(name="legal_intelligence_vault")
                    coll_intel = self.chroma_client.create_collection(name="legal_intelligence_vault")
            self.intel_coll = coll_intel
        except Exception:
            try:
                self.intel_coll = self.chroma_client.create_collection(name="legal_intelligence_vault")
            except Exception:
                self.intel_coll = self.chroma_client.get_or_create_collection(name="legal_intelligence_vault")
        
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
                json.dump(self.memory[-10:], f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[WARNING] Failed to save memory file: {e}")

    def _get_embedding(self, text: str):
        if getattr(self, '_ollama_offline', False):
            return None
        # 使用 nomic-embed-text:latest 進行向量化，提升語意檢索效能
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        try:
            res = requests.post(f"{host}/api/embeddings", json={'model': 'nomic-embed-text:latest', 'prompt': text}, timeout=2)
            if res.status_code == 200:
                return res.json().get('embedding')
        except Exception as e:
            print(f"[WARNING] Ollama Embedding Error: {e}. Disabling future embedding calls.")
            self._ollama_offline = True
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
            res = requests.post(f'{os.environ.get("OLLAMA_HOST", "http://localhost:11434")}/api/chat',
                                json={'model': os.environ.get("OLLAMA_MODEL", DEFAULT_LLM_MODEL), 'messages': [{'role': 'user', 'content': prompt}], 'stream': False, 'options': {'num_ctx': 32768}}, timeout=45)
            if res.status_code == 200:
                return res.json().get('message', {}).get('content', current_input).strip()
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
                cos_sim = 1.0 - (dist / 2.0)
                sim_score = max(cos_sim, 0.0)
                
                # 基於位階標記的 RWS 權重 (憲法=1.0, 法律=0.8, 命令=0.6, 規則=0.4, 預設=0.2)
                level = int(m.get('level', 5))
                if level == 1:
                    rws_weight = 1.0
                elif level == 2:
                    rws_weight = 0.8
                elif level == 3:
                    rws_weight = 0.6
                elif level == 4:
                    rws_weight = 0.4
                else:
                    rws_weight = 0.2

                # 憲法與釋字強制置頂
                if any(re.search(p, d) for p in self.const_patterns):
                    rws_weight = 1.0

                # 時效強制置頂 (命中「消滅時效」、「追訴權時效」且 query 包含時效相關字眼，權重強制拉滿 1.0)
                if "時效" in d and any(k in query for k in ["時效", "過期", "抗辯"]):
                    rws_weight = 1.0

                cat_match = 1.0 if m.get('category') == category_hint else 0.8
                final_score = (0.4 * sim_score) + (0.6 * rws_weight) * cat_match
                
                combined.append({
                    "text": d,
                    "score": round(final_score, 4),
                    "source": m.get('source', '法條'),
                    "level": level
                })

        # 2. 處理經驗與智商庫
        if res_intel and res_intel['documents'] and res_intel['documents'][0]:
            for d, m in zip(res_intel['documents'][0], res_intel['metadatas'][0]):
                # 經驗文檔賦予極高權重，置頂於最前端，引導 AI 避開邏輯陷阱
                combined.append({
                    "text": f"【經驗智商晶片】\n{d}",
                    "score": 1.2,
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
            res = requests.post(f'{OLLAMA_HOST}/api/chat',
                                json={'model': DEFAULT_LLM_MODEL, 'messages': messages, 'stream': False, 'options': {'num_ctx': 32768}}, timeout=120)
            if res.status_code == 200:
                reply = res.json().get('message', {}).get('content', 'API 回應格式異常')
                # 追加到歷史紀錄中
                self.memory.append({"role": "user", "content": user_input})
                self.memory.append({"role": "assistant", "content": reply})
                self._save_memory()
                
                # 自動提煉人事時地物關係並寫入 Obsidian 與 ChromaDB
                mermaid_code = DEFAULT_MERMAID
                try:
                    mermaid_code = self._save_to_obsidian_and_chromadb(user_input, reply)
                except Exception as e_mem:
                    print(f"[WARNING] Error writing to Obsidian and relation graph: {e_mem}")
                
                return reply, evidence, mermaid_code
        except Exception as e:
            return f"❌ 呼叫 LLM 服務失敗，請確認本地 Ollama ({DEFAULT_LLM_MODEL}) 正在運行：{e}", [], DEFAULT_MERMAID

        return "（未取得本地 LLM 回應，請確認連接正常。）", [], DEFAULT_MERMAID

    def _save_to_obsidian_and_chromadb(self, user_input: str, reply: str) -> str:
        import datetime
        
        # 預設備份關係圖代碼
        mermaid_code = DEFAULT_MERMAID
        
        # 1. 呼叫 Ollama 對對話進行 人、事、時、地、物 關係提煉 (包含 Mermaid 關係圖)
        prompt = f"""請根據以下對話內容，提煉出這一次互動的「人事時地物」關係，並生成一篇簡明扼要的 Obsidian 法律事件記憶筆記（包含 Mermaid.js 關係流程圖）。
要求：
1. 必須使用繁體中文。
2. 輸出格式必須是完整的 Markdown，包含以下內容：
   # 法律事件記憶 - [主題或簡短案件名稱]
   - **時間 (When)**: [具體時間或對話日期]
   - **人物 (Who)**: [涉及的申訴人、被告或相關人]
   - **事件 (What)**: [糾紛事實、法律問題]
   - **地點 (Where)**: [如果對話中有提到地點，否則填無]
   - **核心物/標的 (Why/Object)**: [例如賠償金額、合約、車禍車輛等]
   - **AI 建議與行動點 (Action Points)**: [對話中給出的核心法律建議或下一步行動]
   
   ## 關係圖面 (Mermaid)
   ```mermaid
   graph TD
     A["人: 申訴人"] -->|關係| B["事: 法律案件"]
   ```
3. 關係圖的節點標籤必須使用雙引號括住，例如 A["人: 申訴人"]，以防止 Mermaid 渲染出錯。
4. 僅輸出 Markdown 內容，不要包含任何前言、解釋、引導詞或思考標籤。

對話內容：
使用者：{user_input}
AI 回應：{reply}
"""
        try:
            res = requests.post(f'{OLLAMA_HOST}/api/chat', 
                                json={'model': DEFAULT_LLM_MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False, 'options': {'num_ctx': 32768}}, 
                                timeout=60)
            if res.status_code == 200:
                memory_md = res.json().get('message', {}).get('content', '').strip()
                
                # 移除思考過程
                if "<think>" in memory_md:
                    memory_md = re.sub(r"<think>.*?</think>", "", memory_md, flags=re.DOTALL).strip()
                
                # 從生成的 Markdown 中提取 Mermaid 流程圖代碼
                mermaid_match = re.search(r"```mermaid\s*(.*?)\s*```", memory_md, re.DOTALL)
                if mermaid_match:
                    mermaid_code = mermaid_match.group(1).strip()
            else:
                memory_md = f"# 法律事件記憶\n- **時間 (When)**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- **人物 (Who)**: 申訴人與AI\n- **事件 (What)**: 法律案件諮詢\n- **對話**: {user_input[:100]}...\n"
        except Exception as e:
            print(f"Failed to generate Obsidian memory: {e}")
            memory_md = f"# 法律事件記憶 (產生失敗)\n- **時間 (When)**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- **錯誤**: {e}\n- **對話**: {user_input[:100]}...\n"
            
        # 2. 定位 Obsidian Vault 路徑
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memory_{timestamp}.md"
        
        vault_dir = os.path.join(self.base_dir, "Obsidian_Vault")
        target_dir = os.path.join(vault_dir, "03_法律與案件")
        
        # 確保 Obsidian_Vault/03_法律與案件 目錄存在
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            print(f"Failed to create directory {target_dir}: {e}")
            target_dir = str(self.base_dir)
            
        file_path = os.path.join(target_dir, filename)
        
        # 3. 寫入 markdown 檔案至 Obsidian
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(memory_md)
            print(f"[OK] Successfully wrote memory and relation graph to Obsidian note: {file_path}")
        except Exception as e:
            print(f"Failed to write memory note to Obsidian: {e}")
            
        # 4. 同步索引至 ChromaDB，確保下次對話可通過嵌入語意進行聯想檢索
        try:
            vec = self._get_embedding(memory_md)
            if vec:
                self.intel_coll.add(
                    ids=[f"obsidian_memory_{timestamp}"],
                    documents=[memory_md],
                    embeddings=[vec],
                    metadatas=[{"source": f"Obsidian記憶 ({filename})", "type": "obsidian_memory"}]
                )
                print(f"[OK] Indexed Obsidian memory and relation graph in ChromaDB")
        except Exception as e:
            print(f"Failed to index memory in ChromaDB: {e}")
            
        return mermaid_code

    def chat(self, user_input):
        """相容規格書規定的 chat 介面"""
        reply, evidence = self.chat_with_rws(user_input)[:2]
        return reply, evidence

    SUBJECT_PROMPTS = {
        "民法": "你是一位民法專家，專精契約、物權與侵權行為等民事法律關係與實務爭議解析。",
        "刑法": "你是一位刑法與刑事訴訟專家，專精犯罪要件、量刑基準與訴訟防禦策略。",
        "行政程序法": "你是一位行政法學與公法實務專家，專精行政處分要件、行政爭訟與訴願程序合規。",
        "專利法": "你是一位專利代理人與智慧財產權專家，專精專利三要件（新穎性、進步性、產業利用性）與侵權分析。",
        "商標法": "你是一位商標審查與爭議救濟專家，專精商標近似、商品類似、混淆誤認之虞判定及商標侵權。",
        "著作權法": "你是一位著作權法專家，專精著作原創性、合理使用要件、重製與合理授權分析。",
        "營業秘密法": "你是一位企業營業秘密防護專家，專精營業秘密三要件（秘密性、經濟價值、合理保密措施）及競業禁止糾紛。",
        "個資法": "你是一位個人資料保護法與資料治理專家，專精個資蒐集、處理、利用之合法要件與合規評估。",
        "選罷法": "你是一位公職人員選舉罷免法專家，專精選罷規範、選舉無效訴訟與選罷罰則。",
        "證券交易法": "你是一位證交法與金融犯罪分析專家，專精內線交易、財報不實、操縱股價之要件認定與實務見解。",
        "所得稅法": "你是一位稅務規劃與租稅實務專家，專精綜合所得稅、營利事業所得稅核課與稅務訴訟糾紛。",
        "金融法規": "你是一位銀行與金融監理專家，專精洗錢防制、銀行法合規與金融消費者保護法實務。",
        "RealtyLex 不動產法律": "你是一位不動產與土地法專家，專精房地買賣、房屋租賃、借名登記與都市更新糾紛分析。",
        "國考": "你是一位國家考試（司法官與律師）輔導專家，引導使用者使用 IRAC 結構剖析國考歷屆考題與爭點。"
    }

    def verify_judgment_citations(self, reply: str) -> str:
        # 正則表達式抓取判決案號：如最高法院 112 年度台上字第 1234 號
        pattern = r"(最高法院\s*\d+\s*年度?\s*\w+字第\s*\d+\s*號)"
        matches = list(set(re.findall(pattern, reply)))
        
        verified_reply = reply
        for citation in matches:
            citation_clean = re.sub(r"\s+", "", citation)
            found = False
            try:
                # 模糊檢索本地法條與判決庫
                res = self.law_coll.query(query_texts=[citation], n_results=1)
                if res and res['documents'] and res['documents'][0]:
                    best_doc = res['documents'][0][0]
                    # 如果匹配度高，或者文件內容包含該案號
                    if citation_clean in best_doc.replace(" ", ""):
                        found = True
            except Exception:
                pass
            
            if found:
                label = f" {citation} `[✅ 判決真實性已確認]`"
            else:
                label = f" {citation} `[⚠️ 案號未載於本機資料庫]`"
                
            verified_reply = verified_reply.replace(citation, label)
            
        return verified_reply

    def chat_subject_qa(self, subject: str, query: str) -> tuple:
        # 獲取特定學科提示詞
        sub_prompt = self.SUBJECT_PROMPTS.get(subject, "你是一位精通臺灣實務的資深 AI 法律特助。")
        
        # 進行 RAG 檢索
        evidence = self.search_hybrid(query, category_hint=subject[:2])
        context_str = "\n".join([f"[{i+1}] {e['text']}" for i, e in enumerate(evidence)])
        
        system_instruction = (
            f"{sub_prompt}\n"
            "請基於以下經 RWS 篩選的法規與關聯資料進行專業解答，確保用語符合中華民國（臺灣）法律實務，避免大陸用語：\n\n"
            f"{context_str}\n"
        )
        
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": query}
        ]
        
        try:
            res = requests.post(f'{OLLAMA_HOST}/api/chat',
                                json={'model': DEFAULT_LLM_MODEL, 'messages': messages, 'stream': False}, timeout=120)
            if res.status_code == 200:
                reply = res.json().get('message', {}).get('content', 'API 回應格式異常')
                reply = self.verify_judgment_citations(reply)
                return reply, evidence
        except Exception as e:
            return f"❌ 呼叫學科問答服務失敗：{e}", []
            
        return "（未取得本地 LLM 回應，請確認連接正常。）", []

    def review_contract(self, contract_text: str) -> str:
        prompt = (
            "你是一位資深的法律合規與契約審查專家（老律師魂）。請幫我針對以下契約文字，進行深度的風險評估與審查。\n"
            "請特別注意並找出以下潛在風險與條款缺失：\n"
            "1. 違約責任與賠償限額（是否有顯失公平之高額違約金或對等性缺失）。\n"
            "2. 契約管轄權與準據法（是否有管轄法院不便或境外司法管轄瑕疵）。\n"
            "3. 終止與解約條款（是否有單方任意解約且無須補償之不平等約定）。\n"
            "4. 標的物交付與驗收標準（條款是否含糊不清、缺少確切驗收期）。\n"
            "5. 保密與智慧財產權歸屬（是否有過度轉讓、缺少合理免責例外）。\n\n"
            "請以條列式結構輸出：\n"
            "## 🕵️ LexMind-Review 契約合規審查報告\n"
            "### 一、 核心風險評估（Risk Assessment）\n"
            "[分析契約中具有法律風險的具體段落並給出理由]\n"
            "### 二、 缺失與建議增補條款（Missing & Proposed Clauses）\n"
            "[分析缺少了什麼保護性條款，並給出建議的具體合約文字]\n\n"
            f"契約內容：\n{contract_text}"
        )
        
        messages = [
            {"role": "system", "content": "你是一位資深法律合規與契約審查專家，請使用繁體中文法律用語進行分析。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            res = requests.post(f'{OLLAMA_HOST}/api/chat',
                                json={'model': DEFAULT_LLM_MODEL, 'messages': messages, 'stream': False}, timeout=120)
            if res.status_code == 200:
                reply = res.json().get('message', {}).get('content', 'API 回應格式異常')
                return reply
        except Exception as e:
            return f"❌ 執行契約審查失敗：{e}"
        return "（未取得本地 LLM 回應，請確認連接正常。）"
