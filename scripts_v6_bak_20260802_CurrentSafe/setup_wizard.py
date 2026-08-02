# -*- coding: utf-8 -*-
import json
import os
import sys
import shutil
import re
import json
from datetime import datetime
try:
    import google.auth
    from google.auth.transport.requests import Request
    import urllib.request
except ImportError:
    pass

# 設定系統編碼以支援中文輸出
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8-sig')

CONFIG_PATH = r"C:\LocalAI_Workstation\config.yaml"
VERTEX_KEY_DEST = r"C:\LocalAI_Workstation\vertex_key.json"
KEYS_YAML_DEST = r"C:\LocalAI_Workstation\config\keys.yaml"

def print_header(text):
    print("\n" + "="*50)
    print(f" 🚀 {text}")
    print("="*50)

def ensure_security():
    """確保高機密檔案不被 Git 追蹤"""
    print("\n[🛡️ 資安防護機制啟動] 正在檢查 Git 狀態與忽略清單...")
    
    files_to_ignore = [
        "vertex_key.json",
        "config/keys.yaml",
        "config/quota_state.json",
        ".env"
    ]
    
    repo_paths = [
        r"C:\LocalAI_Workstation",
        r"C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站"
    ]
    
    for repo in repo_paths:
        if not os.path.exists(repo):
            continue
            
        gitignore_path = os.path.join(repo, ".gitignore")
        
        # 讀取現有內容
        existing_lines = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8-sig") as f:
                existing_lines = [line.strip() for line in f.readlines()]
                
        # 補齊漏掉的
        missing_files = []
        for file in files_to_ignore:
            if file not in existing_lines:
                missing_files.append(file)
                
        if missing_files:
            with open(gitignore_path, "a", encoding="utf-8-sig") as f:
                f.write("\n# Auto-added by Setup Wizard for Security\n")
                for m in missing_files:
                    f.write(f"{m}\n")
            print(f"  ✅ 已自動將機密檔案加入 {repo} 的 .gitignore 中！防外洩就緒。")
        else:
            print(f"  ✅ {repo} 的資安防護已是最嚴密狀態。")

def update_config(key, new_value):
    """使用正則表達式更新 config.yaml，不破壞註解"""
    if not os.path.exists(CONFIG_PATH):
        print(f"找不到設定檔: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        content = f.read()

    # 處理布林值與字串
    if isinstance(new_value, bool):
        value_str = "true" if new_value else "false"
        pattern = rf'^(\s*){key}:\s*(true|false|"[^"]*"|\'[^\']*\')'
        replacement = rf'\1{key}: {value_str}'
    else:
        pattern = rf'^(\s*){key}:\s*(true|false|"[^"]*"|\'[^\']*\')'
        replacement = rf'\1{key}: "{new_value}"'

    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    with open(CONFIG_PATH, "w", encoding="utf-8-sig") as f:
        f.write(new_content)

def get_current_strategy_status():
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            cfg = yaml.safe_load(f)
        stt = cfg.get("settings", {}).get("stt_engine", "gemini")
        merge = cfg.get("settings", {}).get("merge_engine", "gemini")
        model = cfg.get("api", {}).get("gemini_model_high_accuracy", "gemini-2.5-flash")
        
        if stt == "gemini" and merge == "gemini":
            return f"🟢 目前狀態：【策略 A (純免費)】 (STT: {stt}, Merge: {merge}, Model: {model})"
        elif stt == "gemini" and merge == "vertexai":
            return f"🟡 目前狀態：【策略 B (混合雙打)】 (STT: {stt}, Merge: {merge}, Model: {model})"
        elif stt == "local_whisper" and merge == "gemini":
            return f"🟢 目前狀態：【策略 C (本地免流)】 (STT: {stt}, Merge: {merge}, Model: {model})"
        elif stt == "vertexai" and merge == "vertexai":
            return f"🔴 目前狀態：【策略 D (尊榮企業)】 (STT: {stt}, Merge: {merge}, Model: {model})"
        elif stt == "gemini" and merge == "gemini" and model == "gemini-2.5-pro":
            return f"🌟 目前狀態：【策略 E (隱藏版：解封 Pro)】 (STT: {stt}, Merge: {merge}, Model: {model})"
        else:
            return f"⚪ 目前狀態：【自訂狀態】 (STT: {stt}, Merge: {merge}, Model: {model})"
    except Exception as e:
        return "⚪ 目前狀態：未知 (無法讀取設定檔)"

# 策略設定矩陣 (Strategy Configuration Matrix)
# 透過此矩陣統一管理所有策略，未來的擴充或修改只需調整此處。
STRATEGY_MATRIX = {
    "1": {
        "desc": "1. 策略 A【純個人帳號 雲端免費金鑰池流(強烈推薦)】：STT 與精校全走 AI Studio 免費金鑰池 (完全 0 成本)",
        "stt_engine": "gemini",
        "merge_engine": "gemini",
        "gemini_model_high_accuracy": "gemini-2.5-flash",
        "success_msg": "✅ 已切換至【策略 A: 純免費金鑰池 (0 成本)】"
    },
    "2": {
        "desc": "2. 策略 B【混合雙打 免費企業試用版 Vertex AI 的專屬雲端免費金鑰,無任何折抵免費金鑰(有帳單風險)】：STT 免費池 + 精校 Vertex AI  不能用2.5-pro",
        "stt_engine": "gemini",
        "merge_engine": "vertexai",
        "gemini_model_high_accuracy": "gemini-2.5-flash",
        "success_msg": "✅ 已切換至【策略 B: 混合雙打 (無折抵金，鎖定 Flash 避免暴增費用)】"
    },
    "3": {
        "desc": "3. 策略 C【混合雙打 免費企業試用版Vertex AI 的專屬雲端免費金鑰且有9000元折抵免費金鑰解封 Pro(有帳單風險)】：STT 免費池 + 精校 Vertex AI能用2.5-pro",
        "stt_engine": "gemini",
        "merge_engine": "vertexai",
        "gemini_model_high_accuracy": "gemini-2.5-pro",
        "success_msg": "✅ 已切換至【策略 C: 混合雙打 (使用 9000 元折抵金解封 Pro)】"
    },
    "4": {
        "desc": "4. 策略 D【本地無須雲端免費金鑰池流 (純免費)】：STT 本機 Whisper + 精校 AI Studio 免費金鑰池",
        "stt_engine": "local_whisper",
        "merge_engine": "gemini",
        "gemini_model_high_accuracy": "gemini-2.5-flash",
        "success_msg": "✅ 已切換至【策略 D: 本地優先 (0 成本)】"
    },
    "5": {
        "desc": "5. 策略 E【(尊榮企業級通道全程都絕對會產生費用)(極度昂貴)】：STT 與精校全走 Vertex AI 2.5-pro",
        "stt_engine": "vertexai",
        "merge_engine": "vertexai",
        "gemini_model_high_accuracy": "gemini-2.5-pro",
        "success_msg": "✅ 已切換至【策略 E: 全 Vertex 企業級 (巨額帳單模式)】"
    }
}

def strategy_menu():
    print_header("請選擇處理策略 (四大路徑)")
    print(get_current_strategy_status())
    print("-" * 50)
    
    # 動態產生選單
    for key, config in STRATEGY_MATRIX.items():
        print(config["desc"])
    print("0. 回主選單")
    
    choice = input(f"\n請輸入選項 (0-{len(STRATEGY_MATRIX)}): ").strip()
    
    if choice in STRATEGY_MATRIX:
        cfg = STRATEGY_MATRIX[choice]
        update_config("stt_engine", cfg["stt_engine"])
        update_config("merge_engine", cfg["merge_engine"])
        update_config("gemini_model_high_accuracy", cfg["gemini_model_high_accuracy"])
        print(f"\n{cfg['success_msg']}")
    elif choice != "0":
        print("\n❌ 無效的選項，請重新輸入。")
    
    input("按 Enter 鍵繼續...")

def vertex_menu():
    print_header("更換 Vertex AI 帳號 (ADC 安全憑證登入)")
    print("注意：系統已升級，不再依賴實體 JSON 金鑰，將直接透過 gcloud 進行網頁安全登入。")
    
    project_id = input("\n請輸入新的 Google Cloud 專案 ID (例如 trusty-spanner-366704) [直接按 Enter 跳過]: ").strip()
    if project_id:
        # 防呆機制：若使用者貼上整段字，自動擷取 project- 開頭的 ID
        match = re.search(r'project-[\w-]+', project_id)
        if match:
            project_id = match.group(0)
            
        update_config("vertexai_project", project_id)
        update_config("vertexai_credentials_path", "") # 強制清空 JSON 路徑以啟用 ADC
        print(f"✅ 專案 ID 已更新為: {project_id}")
        
        print("\n🚀 正在為您啟動瀏覽器進行最高權限安全登入 (Application Default Credentials)...")
        gcloud_cmd = r"C:\LocalAI_Workstation\gcloud_sdk\google-cloud-sdk\bin\gcloud.cmd"
        if os.path.exists(gcloud_cmd):
            os.system(f'"{gcloud_cmd}" auth application-default login')
            os.system(f'"{gcloud_cmd}" auth application-default set-quota-project {project_id}')
            print("\n✅ 企業級安全憑證設定完成！完全不留痕跡！")
        else:
            print("\n❌ 找不到 gcloud 工具，請確認是否已安裝 Google Cloud SDK 到 gcloud_sdk 資料夾。")
            
    input("\n按 Enter 鍵繼續...")

def gemini_keys_menu():
    print_header("管理 Gemini 免費金鑰池")
    print(f"系統將開啟 {KEYS_YAML_DEST} 供您編輯。")
    print("請直接將新的 AQ... 金鑰貼在清單中，儲存並關閉記事本即可。")
    print("這份檔案受到 Git 嚴格保護，絕不會外洩到任何備份網址！")
    input("\n按 Enter 鍵開啟記事本...")
    
    if not os.path.exists(KEYS_YAML_DEST):
        # 建立預設檔案
        os.makedirs(os.path.dirname(KEYS_YAML_DEST), exist_ok=True)
        with open(KEYS_YAML_DEST, "w", encoding="utf-8-sig") as f:
            f.write("gemini:\n  - AQ.your_key_here\n")
            
    # 使用系統預設文字編輯器開啟
    os.system(f'notepad "{KEYS_YAML_DEST}"')
    
    print("\n✅ 編輯完成！")
    # 安全防護：立即檢查
    ensure_security()
    
    input("按 Enter 鍵繼續...")

def billing_info_menu():
    print_header("查詢 Google Cloud 帳務與授權資訊")
    print(f"🕒 查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    try:
        import google.auth
        from google.auth.transport.requests import Request
        import urllib.request
        import yaml
        
        print("⏳ 正在取得本機 ADC 憑證...")
        credentials, default_project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/cloud-billing']
        )
        credentials.refresh(Request())
        
        # 取得 Email
        token_url = 'https://oauth2.googleapis.com/tokeninfo?access_token=' + credentials.token
        with urllib.request.urlopen(token_url) as res:
            token_info = json.loads(res.read().decode('utf-8'))
            email = token_info.get("email", "未知 (可能為服務帳號)")
            
        print(f"👤 當前授權帳號：{email}")
        
        # 讀取專案 ID
        project_id = ""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f)
                project_id = cfg.get("api", {}).get("vertexai_project", "")
                
        if not project_id:
            project_id = credentials.quota_project_id
        if not project_id:
            project_id = default_project
            
        print(f"🏢 綁定專案 ID：{project_id}")
        
        if not project_id:
            print("❌ 找不到專案 ID，請先在選單 2 設定 Vertex AI 專案。")
            input("\n按 Enter 鍵繼續...")
            return
            
        print("⏳ 正在查詢帳務後台...")
        billing_url = f'https://cloudbilling.googleapis.com/v1/projects/{project_id}/billingInfo'
        req = urllib.request.Request(billing_url)
        req.add_header('Authorization', f'Bearer {credentials.token}')
        
        try:
            with urllib.request.urlopen(req) as res:
                info = json.loads(res.read().decode('utf-8'))
                billing_enabled = info.get("billingEnabled", False)
                billing_name = info.get("billingAccountName", "")
                
                status = "✅ 已啟用" if billing_enabled else "❌ 未啟用"
                print(f"💳 帳單綁定狀態：{status}")
                
                if billing_name:
                    acct_url = f'https://cloudbilling.googleapis.com/v1/{billing_name}'
                    req2 = urllib.request.Request(acct_url)
                    req2.add_header('Authorization', f'Bearer {credentials.token}')
                    with urllib.request.urlopen(req2) as res2:
                        acct_info = json.loads(res2.read().decode('utf-8'))
                        currency = acct_info.get("currencyCode", "未知")
                        print(f"💱 結帳幣別：{currency}")
        except Exception as e:
            print(f"⚠️ 無法取得帳務詳細資訊：可能權限不足 ({e})")
            
        print("-" * 50)
        print("📌 【免費抵免額與實際帳單金額查詢】")
        print("Google API 不提供直接查詢抵免額餘額的功能。")
        print("請點擊下方專屬網址前往您的 Google Cloud 後台查看即時帳務與 $9,564 餘額：")
        print(f"👉 點擊開啟： https://console.cloud.google.com/billing?project={project_id}")
        
    except ImportError:
        print("❌ 系統缺少必要的 google-auth 等套件，請先安裝。")
    except Exception as e:
        print(f"❌ 發生未知的錯誤：{e}")
        
    input("\n按 Enter 鍵繼續...")

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_header("LexMind 互動式設定與資安守護精靈")
        print("1. 🎯 快速切換處理策略 (STT 與 Merge 引擎設定)")
        print("2. 🔑 更換 Vertex AI 企業帳號與金鑰")
        print("3. 💰 管理 Gemini 免費金鑰池 (keys.yaml)")
        print("4. 🛡️ 執行資安防護掃描 (檢查金鑰是否漏防)")
        print("5. 📊 查詢 Google Cloud 帳務與授權資訊")
        print("0. 退出程式")
        
        choice = input("\n請輸入選項 (0-5): ").strip()
        
        if choice == "1":
            strategy_menu()
        elif choice == "2":
            vertex_menu()
        elif choice == "3":
            gemini_keys_menu()
        elif choice == "4":
            ensure_security()
            input("按 Enter 鍵繼續...")
        elif choice == "5":
            billing_info_menu()
        elif choice == "0":
            print("再見！")
            break

if __name__ == "__main__":
    # 啟動時自動進行一次隱式安全掃描
    ensure_security()
    main()

