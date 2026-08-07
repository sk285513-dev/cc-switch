import os
import yaml
import requests
import logging

def get_latest_models(api_key: str):
    """
    動態探測 Google Gemini API，找出支援 generateContent 的最新 flash 與 pro 模型。
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logging.error(f"Failed to fetch models: {response.text}")
            return None, None
            
        data = response.json()
        models = data.get("models", [])
        
        flash_models = []
        pro_models = []
        
        for m in models:
            name = m.get("name", "").replace("models/", "")
            methods = m.get("supportedGenerationMethods", [])
            
            if "generateContent" not in methods:
                continue
                
            # 過濾掉 vision 或 embedding 模型，專注於通用生成模型
            if "vision" in name.lower() or "embedding" in name.lower() or "aqa" in name.lower():
                continue
                
            if "flash" in name.lower() and "exp" not in name.lower() and "8b" not in name.lower():
                flash_models.append(name)
            elif "pro" in name.lower() and "exp" not in name.lower() and "vision" not in name.lower():
                pro_models.append(name)
                
        # 簡單排序，取最新的版號
        flash_models.sort(reverse=True)
        pro_models.sort(reverse=True)
        
        latest_flash = flash_models[0] if flash_models else "gemini-1.5-flash" # fallback
        latest_pro = pro_models[0] if pro_models else "gemini-1.5-pro" # fallback
        
        return latest_flash, latest_pro
        
    except Exception as e:
        logging.error(f"Exception during model discovery: {e}")
        return None, None

def resolve_models():
    """
    從 config 讀取可用金鑰並探測模型。若無金鑰則回傳預設值。
    """
    try:
        keys_path = os.path.join("config", "keys.yaml")
        if os.path.exists(keys_path):
            with open(keys_path, "r", encoding="utf-8") as f:
                keys_data = yaml.safe_load(f)
            
            # 讀取 keys.yaml 找一把金鑰
            # 格式: keys: - value: <key>
            google_keys = keys_data.get("keys", [])
            active_key = None
            if google_keys and len(google_keys) > 0:
                # 拿第一把金鑰來測試
                active_key = google_keys[0].get("value")
                    
            if active_key:
                flash, pro = get_latest_models(active_key)
                if flash and pro:
                    return flash, pro
                    
        return "gemini-3.5-flash", "gemini-3.6-pro"
        
    except Exception:
        return "gemini-3.5-flash", "gemini-3.6-pro"

if __name__ == "__main__":
    # 測試執行
    flash, pro = resolve_models()
    print(f"Discovered Flash Model: {flash}")
    print(f"Discovered Pro Model: {pro}")

