import os
import yaml
from datetime import datetime, timezone

sandbox_dir = r"C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\sandbox_ssot"
os.makedirs(sandbox_dir, exist_ok=True)
keys_yaml_path = os.path.join(sandbox_dir, "keys.yaml")

# 1. 模擬舊版 keys.yaml (只有字串)
old_keys_data = {
    "gemini_keys": [
        "AIzaSyA-fake-key-1-active",
        "AIzaSyB-fake-key-2-will-429",
        "AIzaSyC-fake-key-3-will-401"
    ]
}

with open(keys_yaml_path, 'w', encoding='utf-8') as f:
    yaml.dump(old_keys_data, f)

print("--- 步驟 1: 建立舊版 keys.yaml (純字串) ---")
with open(keys_yaml_path, 'r', encoding='utf-8') as f:
    print(f.read())


# 2. 模擬 SSOT 金鑰管理器 (升級與讀寫)
class SSOTKeyManager:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path

    def load_and_upgrade_keys(self):
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        raw_keys = data.get("gemini_keys", [])
        upgraded_keys = []
        
        for k in raw_keys:
            if isinstance(k, str):
                # 升級為字典格式
                upgraded_keys.append({
                    "value": k,
                    "status": "active",
                    "last_checked": datetime.now(timezone.utc).isoformat()
                })
            elif isinstance(k, dict):
                if "status" not in k:
                    k["status"] = "active"
                upgraded_keys.append(k)
                
        # 寫回升級後的格式
        data["gemini_keys"] = upgraded_keys
        with open(self.yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False)
            
        return upgraded_keys

    def mark_key_status(self, key_value, new_status, reason=""):
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            
        for k in data.get("gemini_keys", []):
            if isinstance(k, dict) and k.get("value") == key_value:
                k["status"] = new_status
                k["last_checked"] = datetime.now(timezone.utc).isoformat()
                if reason:
                    k["notes"] = reason
                break
                
        with open(self.yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False)

manager = SSOTKeyManager(keys_yaml_path)

print("--- 步驟 2: SSOT 管理器讀取並自動升級結構 ---")
keys = manager.load_and_upgrade_keys()
with open(keys_yaml_path, 'r', encoding='utf-8') as f:
    print(f.read())

print("--- 步驟 3: 模擬遇到 429 耗盡 與 401 死亡 ---")
print("[Quota Manager] Key 2 回報 429 Resource Exhausted")
manager.mark_key_status("AIzaSyB-fake-key-2-will-429", "exhausted", "HTTP 429 Quota Exceeded")

print("[test_keys.py] Key 3 回報 401 Unauthorized (API KEY INVALID)")
manager.mark_key_status("AIzaSyC-fake-key-3-will-401", "dead", "HTTP 401 API Key Invalid")

print("--- 步驟 4: 最終 SSOT keys.yaml 狀態 (金鑰數量未減少，但狀態已被精準標記) ---")
with open(keys_yaml_path, 'r', encoding='utf-8') as f:
    print(f.read())
