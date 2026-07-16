import os
import re  # 增加正則表達式模組
from pathlib import Path
import shutil
from datetime import datetime
import requests
import chromadb

# ========================================================
# [MODULE A] File System Tools
# ========================================================
class FileSystemTools:
    def __init__(self, root_path="C:/LocalAI_Workstation"):
        self.root_path = Path(root_path)

    def _get_safe_path(self, relative_path: str) -> Path:
        return self.root_path / relative_path.strip()

    def backup_and_diff(self, target_path: str, new_content: str):
        full_path = self._get_safe_path(target_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = str(full_path) + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M")

        if full_path.exists():
            shutil.copy2(full_path, backup_path)
            backup_msg = f"💾 已備份至：{Path(backup_path).name}"
        else:
            backup_msg = "ℹ️ 無舊版本，跳過備份。"

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return (backup_msg + "\n✅ 本地文件已更新成功！"), True
        except Exception as e:
            return f"❌ 寫入失敗：{e}", False

# ========================================================
# [MODULE B] RAG Manager
# ========================================================
class RAGManager:
    def __init__(self, db_path="C:/LocalAI_Workstation/RAGFlow_Datasets"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection_name = "legal_docs" 

    def search(self, query: str, top_k=3):
        try:
            collection = self.client.get_or_create_collection(name=self.collection_name)
            results = collection.query(query_texts=[query], n_results=top_k)
            documents = results['documents'][0] if results['documents'] else []
            return "\n".join(documents) if documents else "知識庫目前為空，請先 ingest 資料。"
        except Exception as e:
            return f"RAG 檢索錯誤: {e}"

# ========================================================
# [MODULE C] LLM Manager
# ========================================================
class LLMManager:
    def __init__(self, model_name="deepseek-r1:7b", api_url="http://localhost:11434/api/chat"):
        self.model_name = model_name
        self.api_url = api_url

    def chat(self, query: str, context: str):
        prompt = (
            f"【上下文證據】:\n{context}\n\n"
            f"【用戶問題】:\n{query}\n\n"
            f"請直接提供修復後的完整代碼。請將代碼包裹在 ```powershell 標記中。"
        )
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1} # 降低隨機性，提高代碼穩定度
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            if response.status_code != 200:
                return f"ERROR_SERVER: LLM 伺服器錯誤 ({response.status_code})。"
            return response.json()['message']['content']
        except Exception as e:
            return f"ERROR_EXCEPTION: LLM 呼叫失敗: {e}"

# ========================================================
# [MODULE D] Agent Supervisor
# ========================================================
def extract_code(text: str) -> str:
    """
    從 LLM 的回答中提取 ```powershell ... ``` 之間的代碼
    如果找不到代碼塊，則返回空字符串
    """
    pattern = r"```(?:powershell|ps1|bash|python)?\s*(.*?)\s*```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return matches[0] # 返回第一個找到的代碼塊
    return ""

def run_agent_flow(query: str):
    print("\n<<< [REAL AGENT] 啟動【智能代碼提取】工作流 >>>")
    
    rag = RAGManager()
    llm = LLMManager()
    fs = FileSystemTools()

    print("\n[PHASE 1] 檢索知識庫...")
    context = rag.search(query)
    print(f"=> 檢索結果: {context[:100]}...")

    print("\n[PHASE 2] 呼叫 LLM 推理...")
    full_response = llm.chat(query, context)
    
    if full_response.startswith("ERROR_"):
        print(f"\n❌ [CRITICAL ERROR] {full_response}")
        return

    # 🛡️ 【核心改進】：從回答中提取代碼
    clean_code = extract_code(full_response)
    
    if not clean_code:
        print("\n❌ [LOGIC ERROR] AI 回傳了文字但沒有提供代碼塊 (```)。")
        print("🛑 停止物理修改，以防止將說明文字寫入腳本文件。")
        print(f"AI 回傳內容摘要: \n{full_response[:100]}...")
        return

    print(f"=> 已成功提取代碼 (長度: {len(clean_code)} 字符)")

    print("\n[PHASE 3] 執行物理修改...")
    target_file = "Data/SourceFiles/test_source/buggy_script.ps1"
    result_msg, success = fs.backup_and_diff(target_file, clean_code)

    if success:
        print(f"\n{result_msg}")
        print("\n✅ [FINAL] 流程成功完成！")
    else:
        print(f"\n❌ [FAILED] {result_msg}")

if __name__ == "__main__":
    run_agent_flow("請分析並修復本地的 PowerShell 腳本漏洞")
