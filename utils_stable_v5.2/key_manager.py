import os
import yaml
import datetime
import shutil
import urllib.request
import urllib.error
import re
from utils.vault import Vault
from cryptography.fernet import InvalidToken

class KeyManager:
    """金鑰管理中樞：負責 Schema 驗證、自動備份與還原、狀態標記與 API 測試"""
    
    KEYS_PATH = r"C:\LocalAI_Workstation\config\keys.yaml"
    BACKUP_DIR = r"C:\LocalAI_Workstation\config\backups"

    @classmethod
    def _ensure_schema(cls, key_data):
        """確保單筆金鑰符合嚴格的 Object Schema"""
        if isinstance(key_data, str):
            return {
                "active": True,
                "account": "",
                "value": key_data,
                "added_date": datetime.date.today().isoformat(),
                "expiry_date": "",
                "notes": ""
            }
        elif isinstance(key_data, dict):
            return {
                "active": bool(key_data.get("active", True)),
                "account": str(key_data.get("account", "")),
                "value": str(key_data.get("value", "")),
                "added_date": str(key_data.get("added_date", datetime.date.today().isoformat())),
                "expiry_date": str(key_data.get("expiry_date", "")),
                "notes": str(key_data.get("notes", ""))
            }
        return None

    @classmethod
    def load_keys(cls):
        """讀取並驗證 keys.yaml"""
        if not os.path.exists(cls.KEYS_PATH):
            return []
        try:
            with open(cls.KEYS_PATH, 'r', encoding='utf-8-sig') as f:
                raw_content = f.read()
                
            try:
                decrypted_content = Vault.decrypt_data(raw_content)
                data = yaml.safe_load(decrypted_content)
            except InvalidToken:
                data = yaml.safe_load(raw_content)

            if not data or "keys" not in data or not isinstance(data["keys"], list):
                return []
            validated_keys = []
            for k in data["keys"]:
                valid_k = cls._ensure_schema(k)
                if valid_k and valid_k["value"]:
                    validated_keys.append(valid_k)
            return validated_keys
        except Exception as e:
            print(f"KeyManager: Failed to load keys - {e}")
            return []

    @classmethod
    def backup_keys(cls):
        """在寫入前建立時間戳記備份"""
        if not os.path.exists(cls.KEYS_PATH):
            return
        os.makedirs(cls.BACKUP_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(cls.BACKUP_DIR, f"keys_backup_{timestamp}.yaml")
        try:
            shutil.copy2(cls.KEYS_PATH, backup_path)
            backups = sorted([f for f in os.listdir(cls.BACKUP_DIR) if f.startswith("keys_backup_")])
            while len(backups) > 10:
                oldest = backups.pop(0)
                os.remove(os.path.join(cls.BACKUP_DIR, oldest))
        except Exception as e:
            print(f"KeyManager: Failed to create backup - {e}")

    @classmethod
    def save_keys(cls, keys_list):
        """安全寫回 keys.yaml，強制 utf-8-sig，並在寫入前自動備份"""
        validated_keys = []
        for k in keys_list:
            valid_k = cls._ensure_schema(k)
            if valid_k and valid_k["value"]:
                validated_keys.append(valid_k)
        cls.backup_keys()
        os.makedirs(os.path.dirname(cls.KEYS_PATH), exist_ok=True)
        try:
            yaml_str = yaml.dump({"keys": validated_keys}, allow_unicode=True, default_flow_style=False, sort_keys=False)
            encrypted_str = Vault.encrypt_data(yaml_str)
            with open(cls.KEYS_PATH, 'w', encoding='utf-8-sig') as f:
                f.write(encrypted_str)
            return True
        except Exception as e:
            print(f"KeyManager: Failed to save keys - {e}")
            return False

    @classmethod
    def get_backup_list(cls):
        """取得備份清單"""
        if not os.path.exists(cls.BACKUP_DIR):
            return []
        backups = sorted([f for f in os.listdir(cls.BACKUP_DIR) if f.startswith("keys_backup_")], reverse=True)
        return backups

    @classmethod
    def restore_backup(cls, backup_filename):
        """還原指定的備份"""
        backup_path = os.path.join(cls.BACKUP_DIR, backup_filename)
        if not os.path.exists(backup_path):
            return False
        try:
            cls.backup_keys()
            shutil.copy2(backup_path, cls.KEYS_PATH)
            return True
        except Exception as e:
            print(f"KeyManager: Failed to restore backup - {e}")
            return False

    @classmethod
    def add_keys_from_cli(cls, raw_keys_text: str) -> dict:
        """提供後台 Agent 與 CLI 使用的安全匯入介面 (軌道 B)"""
        from filelock import FileLock
        lock_path = cls.KEYS_PATH + ".lock"

        with FileLock(lock_path, timeout=15):
            # 防禦 load_keys() 回傳 None 的邊界狀況
            existing_keys = cls.load_keys() or []

            # 安全取值防禦 KeyError
            existing_values = {
                k.get("value") for k in existing_keys 
                if isinstance(k, dict) and k.get("value")
            }

            parsed = cls.parse_raw_text(raw_keys_text) if hasattr(cls, 'parse_raw_text') else []
            added_count = 0

            for pk in parsed:
                val = pk.get("value")
                if val and val not in existing_values:
                    existing_keys.append(pk)
                    existing_values.add(val)
                    added_count += 1

            if added_count > 0:
                cls.save_keys(existing_keys)

            return {"status": "success", "added": added_count, "total": len(existing_keys)}

if __name__ == '__main__':
    import argparse
    import datetime
    
    parser = argparse.ArgumentParser(description="LexMind-Omni CLI Key Manager (Secure Vault)")
    parser.add_argument("--add", type=str, help="Add a new API key to the Vault")
    parser.add_argument("--list", action="store_true", help="List all loaded API keys (Masked for security)")
    args = parser.parse_args()
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    if args.add:
        keys = KeyManager.load_keys()
        existing = [k for k in keys if k.get("value") == args.add]
        if existing:
            print("❌ The API Key already exists in the Vault.")
        else:
            new_key = {
                "account": "CLI_Import",
                "value": args.add,
                "added_date": datetime.date.today().isoformat(),
                "expiry_date": "",
                "active": True,
                "notes": "Added via CLI"
            }
            keys.append(new_key)
            if KeyManager.save_keys(keys):
                print("✅ Successfully added and encrypted the new API key.")
            else:
                print("❌ Failed to save the key to the Vault.")
                
    elif args.list:
        keys = KeyManager.load_keys()
        print(f"Total Keys: {len(keys)}")
        for i, k in enumerate(keys):
            val = k.get("value", "")
            masked = val[:8] + "*" * 10 + val[-4:] if len(val) > 12 else "***"
            status = "✅ Active" if k.get("active") else "🔴 Inactive"
            print(f"[{i+1}] {masked} | {status} | {k.get('notes', '')}")
            
    else:
        parser.print_help()

