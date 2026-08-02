import os
import sys
import requests
import time
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


import yaml

def test_all_keys():
    # 載入 keys.yaml 檔案
    keys_path = r"C:\LocalAI_Workstation\config\keys.yaml"
    if not os.path.exists(keys_path):
        print(f"找不到 {keys_path}")
        return

    with open(keys_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    keys = []
    for item in data.get('keys', []):
        keys.append((item['name'], item['value']))
            
    print(f"🔍 在 keys.yaml 中找到了 {len(keys)} 把 API 金鑰，準備進行 1 對 1 真實連線測試...")
    
    valid_keys = 0
    exhausted_keys = 0
    error_keys = 0
    
    for idx, (env_name, api_key) in enumerate(keys, 1):
        # 建立極輕量級的 API 請求，測試 gemini-1.5-flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": "hi"}]}]
        }
        
        masked_key = f"{api_key[:8]}...{api_key[-4:]}"
        print(f"[{idx}/{len(keys)}] 測試 {env_name} ({masked_key})... ", end="")
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✅ 可用 (200 OK)")
                valid_keys += 1
            elif response.status_code == 429:
                print("❌ 枯竭 (429 Quota Exceeded)")
                exhausted_keys += 1
            elif response.status_code == 403:
                print("❌ 權限不足/禁用 (403 Forbidden)")
                error_keys += 1
            else:
                print(f"⚠️ 異常 (HTTP {response.status_code}) - {response.text[:50]}")
                error_keys += 1
                
        except Exception as e:
            print(f"⚠️ 連線錯誤: {str(e)[:50]}")
            error_keys += 1
            
        # 避免打得太快被鎖 IP，改成間隔 5 秒
        time.sleep(5)

    print("\n" + "="*50)
    print(f"📊 測試總結:")
    print(f"  總共測試: {len(keys)} 把")
    print(f"  ✅ 可正常使用: {valid_keys} 把")
    print(f"  ❌ 額度枯竭 (429): {exhausted_keys} 把")
    print(f"  ⚠️ 其他異常 (403/錯誤): {error_keys} 把")
    print("="*50)

if __name__ == "__main__":
    test_all_keys()
