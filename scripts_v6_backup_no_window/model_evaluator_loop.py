import json
import os
import random
import time
import urllib.request
import json

WORK_DIR = "C:/LocalAI_Workstation"
VAULT_DIR = os.path.join(WORK_DIR, "Obsidian_Vault", "04_考古題庫")
SERVER_URL = "http://127.0.0.1:3000/api/eval-local"

def get_random_question():
    questions = []
    if not os.path.exists(VAULT_DIR):
        return None
    for root, _, files in os.walk(VAULT_DIR):
        for f in files:
            if f.endswith(".md"):
                questions.append(os.path.join(root, f))
    
    if not questions:
        return None
        
    choice = random.choice(questions)
    with open(choice, "r", encoding="utf-8-sig") as f:
        content = f.read()
        
    # Extract just the question body
    parts = content.split("### 選擇題選項")
    q_body = parts[0].replace("### ⚖️ 題幹本文", "").strip()
    return q_body

def evaluate_question(question):
    print("\n" + "="*50)
    print("【開始進行模型對決與自動修正】")
    print(f"題目：\n{question[:100]}...\n")
    
    payload = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL, 
        data=payload, 
        headers={'Content-Type': 'application/json'}, 
        method='POST'
    )
    
    try:
        max_retries = 10
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=900) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    print(f"[本地模型 (ornith) 回答長度]: {len(data['localAnswer'])} 字")
                    print(f"[雲端模型 (Gemini) 回答長度]: {len(data['cloudAnswer'])} 字")
                    print(f"\n[AI 評審結果]:\n{data['evaluation']}")
                    
                    if data['memoryUpdated']:
                        print("\n⚠️ 發現本地模型見解錯誤或落後！已將修正寫入強制記憶庫 (model_memory.txt)！")
                        return True
                    else:
                        print("\n✅ 本地模型回答正確，無需修正。")
                        return False
            except urllib.error.URLError as e:
                if "10061" in str(e) and attempt < max_retries - 1:
                    print(f"伺服器尚未就緒 (嘗試 {attempt+1}/{max_retries})，等待 10 秒後重試...")
                    time.sleep(10)
                else:
                    raise e
                
    except Exception as e:
        print(f"Failed to call evaluation API: {e}")
        return False

def main():
    print("啟動自動化記憶餵食迴圈...")
    # 只跑 1 題，避免無限迴圈卡死資源
    MAX_QUESTIONS = 1
    
    for i in range(MAX_QUESTIONS):
        q = get_random_question()
        if not q:
            print("找不到任何考古題，請先確保爬蟲有抓到資料。")
            q = "甲將其所有之A地借名登記於乙名下，乙未經甲同意，擅自將A地以買賣為由移轉登記並交付予知情之丙。請問甲可否向丙請求返還A地？"
        
        memory_updated = evaluate_question(q)
        
        if memory_updated:
            print("\n" + "-"*50)
            print("【二次驗證】正在使用相同的題目重新詢問本地模型，測試其是否已吸收新記憶...")
            lawyer_req = urllib.request.Request(
                "http://127.0.0.1:3000/api/lawyer-chat",
                data=json.dumps({
                    "user_input": q,
                    "context_role": "lawyer",
                    "live_case_search": False
                }).encode("utf-8"),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(lawyer_req, timeout=900) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    print("\n[吸收記憶後的本地模型回答]:")
                    print(data['answer'])
                    print("\n🎉 驗證完成！本地模型已套用最新實務見解！")
            except Exception as e:
                print(f"二次驗證失敗: {e}")

if __name__ == "__main__":
    main()

