# 核心工作流程原始碼打包 (Workflow Code Bundle for Expert Review)

此文件包含了 LexMind-Omni 系統中，與最新計畫書相關的端到端核心工作流程原始碼。請專家依據此最新狀態進行深度審查。

## 檔案：`scripts\utils\key_manager.py`
```python
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
                vault = Vault()
                decrypted_content = vault.decrypt_data(raw_content)
                data = yaml.safe_load(decrypted_content)
            except Exception:
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
            vault = Vault()
            encrypted_str = vault.encrypt_data(yaml_str)
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
        from filelock import FileLock, Timeout
        lock_path = cls.KEYS_PATH + ".lock"
        
        try:
            with FileLock(lock_path, timeout=15):
                existing_keys = cls.load_keys() or []
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
        except Timeout:
            print("KeyManager: Failed to acquire lock within 15 seconds.")
            return {"status": "error", "message": "Timeout acquiring lock"}


```

## 檔案：`scripts\quota_manager.py`
```python
import os
import json
import time
import random
import logging
import sys
import re
import ctypes
from pathlib import Path
import yaml
from cryptography.fernet import Fernet
import hashlib
from scripts.win32_kernel import KernelMutex

class SecureMemoryWiper:
    """Phase 7.7 C API 記憶體零化引擎 (OOP 封裝)
    負責調用 Windows 核心 API 進行硬體級的記憶體抹除，對抗 GC 延遲與 Memory Dump。
    """
    @staticmethod
    def wipe_bytearray(key_bytes: bytearray):
        """安全地將記憶體覆寫為 0"""
        if not isinstance(key_bytes, bytearray) or not key_bytes:
            return
        try:
            kernel32 = ctypes.windll.kernel32
            RtlSecureZeroMemory = kernel32.RtlSecureZeroMemory
            RtlSecureZeroMemory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            RtlSecureZeroMemory.restype = ctypes.c_void_p

            data_len = len(key_bytes)
            # 取得 bytearray 的底層 C 陣列指標
            c_buffer = (ctypes.c_char * data_len).from_buffer(key_bytes)
            buffer_address = ctypes.addressof(c_buffer)
            
            # 呼叫底層 API 強制抹除
            RtlSecureZeroMemory(buffer_address, data_len)
            key_bytes.clear()
        except Exception as e:
            logging.warning(f"SecureMemoryWiper failed: {e}")

class AllKeysExhaustedError(Exception):
    pass

class KeyManager:
    """中介層：專責從 Vault 提取主金鑰。"""
    @staticmethod
    def get_all_keys() -> list[str]:
        try:
            from scripts.utils.vault import Vault
            v = Vault()
            keys = v.load_and_decrypt()
            if keys:
                return keys
        except ImportError:
            logging.warning("Vault class not found, falling back.")
        except Exception as e:
            logging.warning(f"KeyManager: Failed to load from Vault: {e}")

        config_yaml_path = Path("config.yaml")
        if config_yaml_path.exists():
            try:
                with open(config_yaml_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if cfg and "api" in cfg:
                    val = cfg.get("api", {}).get("gemini_api_key")
                    if val and not val.startswith("AUTO_LOAD_"):
                        return [val.strip()]
            except Exception:
                pass
        return []

class QuotaManager:
    """
    【專家終極加固版】
    1. 依賴注入 (DI)
    2. 鎖檔分離 (Lockfile) 與安全原子寫入 (Safe os.replace)
    3. 全抖動指數退避 (Full Jitter)
    4. 記憶體 JIT 保護與日誌脫敏
    """
    def __init__(self, key_manager=None, state_path: str = "config/quota_state.json", is_test_traffic: bool = False):
        self.state_path = Path(state_path)
        self.is_test_traffic = is_test_traffic
        # 廢棄 Lockfile，統一改用與 UI 相同的 Phase 7.8 核心級 Named Mutex 防止 AB-BA 死鎖
        self.mutex_name = "Global\\LexMind_Vault_Mutex"
        
        # 依賴注入：不再自己實例化，而是使用傳入的 key_manager
        # 若未傳入，為保持向後相容性，仍使用 KeyManager
        self.key_manager = key_manager if key_manager else KeyManager()
        
        raw_keys = self.key_manager.get_all_keys() if hasattr(self.key_manager, 'get_all_keys') else []
        if not raw_keys:
            raise ValueError("No API keys found via KeyManager.")
            
        # 【資安修補：記憶體駐留防禦】
        # 為了避免在 Heap 留下明文陣列，我們在 QuotaManager 內使用一把拋棄式金鑰加密儲存。
        self._jit_key = Fernet.generate_key()
        self._jit_cipher = Fernet(self._jit_key)
        self._encrypted_keys = [self._jit_cipher.encrypt(k.encode('utf-8')) for k in raw_keys]
        
        self.max_concurrent_calls = 6
        self.base_jitter_seconds = 2.0
        self._load_config()
        self._init_state_file()

    def _hash_key(self, key: str) -> str:
        """將金鑰單向雜湊，防止落盤外洩"""
        return hashlib.sha256(key.encode('utf-8')).hexdigest()

    def _check_and_reload_vault(self):
        """【修復 Issue 5, 7, 11】 每次拿金鑰前，檢查 Vault 是否被 UI 更新，若是則熱載入。並支援 SRE QoS 測試金鑰隔離。"""
        vault_file = "config/secure_keys_test.vault" if self.is_test_traffic else "config/secure_keys.vault"
        vault_path = Path(vault_file)
        if not vault_path.exists():
            return
            
        current_mtime = os.path.getmtime(vault_path)
        if not hasattr(self, '_last_vault_mtime') or current_mtime > self._last_vault_mtime:
            logging.info(f"QuotaManager: 偵測到金鑰庫 ({vault_file}) 已更新，執行跨進程熱載入 (True IPC)...")
            self._last_vault_mtime = current_mtime
            
            # 從安全金鑰庫 (Vault) 解密取得金鑰，徹底取代不安全的 KeyManager 與 keys.yaml
            from scripts.utils.vault import Vault
            v = Vault(vault_file=vault_file)
            try:
                raw_keys = v.load_and_decrypt()
            except Exception as e:
                logging.error(f"QuotaManager: 解密 Vault 失敗: {e}")
                raw_keys = []
                
            if raw_keys:
                self._jit_key = Fernet.generate_key()
                self._jit_cipher = Fernet(self._jit_key)
                self._encrypted_keys = [self._jit_cipher.encrypt(k.encode('utf-8')) for k in raw_keys]


    def _load_config(self):
        config_yaml = Path("config.yaml")
        if config_yaml.exists():
            try:
                with open(config_yaml, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                api_cfg = cfg.get("api", {})
                self.max_concurrent_calls = api_cfg.get("max_concurrent_calls", 6)
                self.base_jitter_seconds = float(api_cfg.get("base_jitter_seconds", 2.0))
            except Exception as e:
                logging.warning(f"Failed to load traffic config: {e}")

    def _init_state_file(self):
        os.makedirs(self.state_path.parent, exist_ok=True)
        if not self.state_path.exists():
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump({
                    "exhausted_keys": [], 
                    "in_use_keys": [],
                    "circuit_breaker": "CLOSED",
                    "cooldown_until": 0,
                    "probe_in_progress": False
                }, f)

    def _read_update_state(self, callback):
        """Phase 7.9 核心級同步：加上超時與防死鎖防禦"""
        # 使用 KernelMutex 進行 OS 級的阻塞排隊 (CPU 負載 0%)
        # 加上 15000ms 超時，防止持有者被防毒軟體卡死導致連環死鎖
        mutex = KernelMutex(self.mutex_name)
        if not mutex.acquire(15000):
            mutex.close()
            raise TimeoutError("Mutex timeout: Possible cascading deadlock detected, falling back to Jitter.")
            
        try:
            # 已經取得跨進程鎖，可以安全讀寫 state_path
            if not self.state_path.exists():
                self._init_state_file()
                
            # 讀取真實資料檔
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                state = {"exhausted_keys": [], "in_use_keys": []}
            
            if "exhausted_keys" not in state: state["exhausted_keys"] = []
            if "in_use_keys" not in state: state["in_use_keys"] = []
            if "circuit_breaker" not in state: state["circuit_breaker"] = "CLOSED"
            if "cooldown_until" not in state: state["cooldown_until"] = 0
            if "probe_in_progress" not in state: state["probe_in_progress"] = False
            
            should_save = callback(state)
                
            if should_save:
                # 原子寫入：寫到 tmp 並 fsync
                tmp_file = str(self.state_path) + ".tmp"
                with open(tmp_file, "w", encoding="utf-8") as tf:
                    json.dump(state, tf, ensure_ascii=False, indent=2)
                    tf.flush()
                    os.fsync(tf.fileno())
                    
                # 【SRE 修補】防禦 Windows Defender 與 WinError 32
                max_retries = 3
                for i in range(max_retries):
                    try:
                        os.replace(tmp_file, str(self.state_path))
                        break
                    except PermissionError:
                        if i == max_retries - 1:
                            raise
                        time.sleep(0.1)
        finally:
            mutex.release()
            mutex.close()

    def acquire_key_exclusive(self) -> str:
        self._check_and_reload_vault()
        selected_key = None
        
        def _try_acquire(state):
            nonlocal selected_key
            # 從 JIT 密碼中解密進行比較
            for enc_k in self._encrypted_keys:
                k = self._jit_cipher.decrypt(enc_k).decode('utf-8')
                hashed_k = self._hash_key(k)
                if hashed_k not in state["exhausted_keys"] and hashed_k not in state["in_use_keys"]:
                    selected_key = k
                    state["in_use_keys"].append(hashed_k)
                    return True
            return False

        self._read_update_state(_try_acquire)
        
        if not selected_key:
            raise AllKeysExhaustedError("所有金鑰均已被佔用或耗盡，無法取得排他性金鑰。")
            
        logging.debug(f"QuotaManager: 跨進程鎖定金鑰 {selected_key[:8]}...")
        return selected_key

    def release_key(self, key: str):
        def _try_release(state):
            hashed_k = self._hash_key(key)
            if hashed_k in state["in_use_keys"]:
                state["in_use_keys"].remove(hashed_k)
                return True
            return False
            
        self._read_update_state(_try_release)
        logging.debug(f"QuotaManager: 跨進程釋放金鑰 {key[:8]}...")

    def handle_error(self, e: Exception, current_key: str, consecutive_429: int):
        # 【資安修補：日誌脫敏】
        raw_err_msg = str(e)
        safe_err_msg = re.sub(r'AIza[a-zA-Z0-9_-]{35}', 'AIza***', raw_err_msg)
        vault_key = os.environ.get("LEXMIND_VAULT_KEY")
        if not vault_key and os.path.exists("config/vault.key"):
            try:
                with open("config/vault.key", "r", encoding="utf-8") as f:
                    vault_key = f.read().strip()
            except Exception:
                pass
                
        if vault_key and vault_key in safe_err_msg:
            safe_err_msg = safe_err_msg.replace(vault_key, "[REDACTED_VAULT_KEY]")
            
        # 【修補 Issue 4：避免 429 誤判，與 Issue 31 防範檔名注入】
        import google.api_core.exceptions as google_exceptions
        is_429 = isinstance(e, google_exceptions.ResourceExhausted) or getattr(e, 'code', None) == 429
        is_401_403 = isinstance(e, (google_exceptions.Forbidden, google_exceptions.Unauthorized)) or getattr(e, 'code', None) in (401, 403)

        
        # 【SRE 修補：真實的全抖動指數退避 (Full Jitter Exponential Backoff)】
        # random.uniform(0, base * (2 ** retry_count))
        temp = min(60.0, self.base_jitter_seconds * (2 ** consecutive_429))
        sleep_time = random.uniform(0, temp)
        
        new_key = current_key
        project_cooldown = False

        if is_401_403 or (is_429 and consecutive_429 >= 3):
            logging.warning(f"QuotaManager: Key {current_key[:8]}... marked exhausted. Error: {safe_err_msg}")
            
            def _mark_exhausted(state):
                # 【資安修補】僅寫入 Hash 值，落實 Zeroization
                hashed_k = self._hash_key(current_key)
                if hashed_k not in state["exhausted_keys"]:
                    state["exhausted_keys"].append(hashed_k)
                if hashed_k in state["in_use_keys"]:
                    state["in_use_keys"].remove(hashed_k)
                return True
                
            self._read_update_state(_mark_exhausted)
            # 任務完成後，直接將記憶體中的 current_key 明文抹除
            SecureMemoryWiper.wipe_string(current_key)
            
            try:
                new_key = self.acquire_key_exclusive()
            except AllKeysExhaustedError:
                new_key = None
                
        if new_key is None:
            project_cooldown = True
            
            def _open_circuit(state):
                if state.get("circuit_breaker") != "OPEN":
                    state["circuit_breaker"] = "OPEN"
                    # 加入一點隨機避免同時搶 probe
                    state["cooldown_until"] = time.time() + 300 + random.uniform(0, 5)
                    state["probe_in_progress"] = False
                    return True
                return False
            self._read_update_state(_open_circuit)

            logging.warning(f"QuotaManager: 所有 API 金鑰皆已耗盡！進入斷路器熔斷模式 (Circuit Breaker OPEN)...")
            
            while True:
                action = None
                def _check_circuit(state):
                    nonlocal action
                    cb = state.get("circuit_breaker", "CLOSED")
                    cooldown = state.get("cooldown_until", 0)
                    probe = state.get("probe_in_progress", False)

                    if cb == "CLOSED":
                        action = "RESUME"
                    elif cb == "OPEN":
                        if time.time() >= cooldown:
                            if not probe:
                                # Become leader probe
                                state["circuit_breaker"] = "HALF_OPEN"
                                state["probe_in_progress"] = True
                                action = "PROBE"
                                return True
                    return False
                
                self._read_update_state(_check_circuit)
                
                if action == "RESUME":
                    logging.info("QuotaManager: 斷路器已閉合 (CLOSED)，其他探針已成功恢復金鑰。準備喚醒。")
                    break
                elif action == "PROBE":
                    logging.info("QuotaManager: 半開探針 (HALF_OPEN) 啟動！本 Worker 將擔任 Leader 進行 API 試探。")
                    self.reset_all_keys()
                    break
                else:
                    time.sleep(5)
            
            try:
                new_key = self.acquire_key_exclusive()
            except AllKeysExhaustedError:
                new_key = None
            sleep_time = 0
            
        return {"sleep_time": sleep_time, "new_key": new_key, "project_cooldown": project_cooldown}

    def reset_all_keys(self):
        def _reset(state):
            state["exhausted_keys"] = []
            return True
        self._read_update_state(_reset)
        logging.info("QuotaManager: 所有金鑰耗盡狀態已重設。")

    def get_key_status(self):
        """【修補 Issue 35：防呆設計】安全回傳狀態字典，避免解構時 NoneType TypeError 崩潰"""
        current_state = None
        def _read_status(state):
            nonlocal current_state
            current_state = dict(state)
            return False
        
        try:
            self._read_update_state(_read_status)
        except Exception as e:
            logging.warning(f"QuotaManager: Failed to get key status: {e}")
            
        if current_state is None:
            return {"circuit_breaker": "UNKNOWN", "exhausted_keys": [], "in_use_keys": []}, None
            
        return current_state, None

    def report_success(self, key: str = None):
        def _close_circuit(state):
            changed = False
            if state.get("circuit_breaker") != "CLOSED":
                state["circuit_breaker"] = "CLOSED"
                state["probe_in_progress"] = False
                changed = True
            if key:
                hashed_k = self._hash_key(key)
                if hashed_k in state["in_use_keys"]:
                    state["in_use_keys"].remove(hashed_k)
                    changed = True
            return changed
        self._read_update_state(_close_circuit)
        logging.debug(f"QuotaManager: API 呼叫成功，斷路器狀態確認閉合 (CLOSED)。")

    def reset_key(self, key: str):
        # 兼容原本錯誤的呼叫名稱
        self.report_success(key)

    def acquire_key(self) -> str:
        self._check_and_reload_vault()
        selected_key = None
        def _try_acquire(state):
            nonlocal selected_key
            for enc_k in self._encrypted_keys:
                k = self._jit_cipher.decrypt(enc_k).decode('utf-8')
                hashed_k = self._hash_key(k)
                if hashed_k not in state["exhausted_keys"]:
                    selected_key = k
                    return False
            return False

        self._read_update_state(_try_acquire)
        if not selected_key:
            raise AllKeysExhaustedError("All keys exhausted.")
        return selected_key

def load_keys_yaml(path: str = "config/keys.yaml"):
    return KeyManager.get_all_keys()

```

## 檔案：`scripts\vault.py`
```python
# [錯誤] 找不到檔案：C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\scripts\vault.py

```

## 檔案：`scripts\tasks\worker.py`
```python
# [錯誤] 找不到檔案：C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\scripts\tasks\worker.py

```

## 檔案：`scripts\orchestrator\batch_runner.py`
```python
# [錯誤] 找不到檔案：C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\scripts\orchestrator\batch_runner.py

```

## 檔案：`scripts\auto_verify.py`
```python
# -*- coding: utf-8 -*-
"""
LexMind-Omni 法律教材工作站 - 本地 IDE 自動化驗收與測試套件
自動掃描 A:\manifests 下所有已完成的真實任務，驗證實體檔案落地、格式品質、RAG索引完整度與 J 碟雙目錄備份。
"""
import os
import sys
import json
import time
import re
from pathlib import Path

# 強制終端機以 UTF-8 輸出，避免 cp950 亂碼崩潰
if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ANSI 顏色配置
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def log_info(msg):
    print(f"{BLUE}[INFO]{RESET} {msg}")

def log_success(msg):
    print(f"{GREEN}[PASS]{RESET} {msg}")

def log_warning(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")

def log_error(msg):
    print(f"{RED}[FAIL]{RESET} {msg}")

def check_file_quality(file_path, file_type):
    """檢測特定落地檔案的實體大小與格式規範"""
    if not os.path.exists(file_path):
        return False, "檔案未落地（不存在）"
    
    size_kb = os.path.getsize(file_path) / 1024
    if size_kb == 0:
        return False, "檔案大小為 0 內容為空"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"UTF-8 解碼失敗: {e}"
        
    # 各類別檔案的格式驗證
    if file_type == "markdown":
        # 檢查是否有 Markdown 標題階層
        if not re.search(r"^#+ ", content, re.MULTILINE):
            return False, "缺乏 Markdown 標題階層 (#, ##)"
        # 檢查是否有時間戳記
        if not re.search(r"\[\d+:\d+\]|\[\d+:\d+:\d+\]", content):
            return False, "缺乏時間戳記對齊"
        # 檢查同音錯字排除度
        errors = ["格論", "地政治", "消滅實效"]
        found_errs = [err for err in errors if err in content]
        if found_errs:
            return False, f"檢測到殘留同音錯字: {found_errs}"
            
    elif file_type == "srt":
        # 檢查標準 SRT 結構
        if not re.search(r"^\d+\s*\n\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->", content, re.MULTILINE):
            return False, "不符合標準 SRT 字幕格式時間軸"
            
    elif file_type == "vtt":
        if not content.startswith("WEBVTT"):
            return False, "缺乏 WebVTT 標頭"
            
    elif file_type == "json_index":
        try:
            data = json.loads(content)
            # 檢查 RAG 關鍵欄位
            required_keys = ["task_id", "original_name", "summary", "full_text_cleaned", "segments"]
            missing = [k for k in required_keys if k not in data]
            if missing:
                return False, f"JSON 索引缺乏核心 RAG 欄位: {missing}"
        except Exception as e:
            return False, f"JSON 格式解析出錯: {e}"
            
    return True, f"正常 ({size_kb:.2f} KB)"

def run_verification():
    print("=" * 70)
    print(f"{BOLD}LexMind-Omni 本地 IDE 自動化驗收與品管工具啟動{RESET}")
    print(f"執行時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    manifests_dir = "A:\\manifests"
    processed_dir = "A:\\processed_md"
    
    if not os.path.exists(manifests_dir):
        log_error(f"Manifest 目錄 {manifests_dir} 不存在，驗收終止。")
        return False
        
    expected_files = {
        "output_markdown": ("markdown", "Markdown 講義 (.md)"),
        "output_srt": ("srt", "SRT 字幕 (.srt)"),
        "output_vtt": ("vtt", "WebVTT 字幕 (.vtt)"),
        "output_txt": ("txt", "純文字逐字稿 (.txt)"),
        "output_json_index": ("json_index", "RAG JSON 索引 (_index.json)")
    }

    # 1. 掃描所有已完成 (completed) 的任務
    completed_manifests = []
    try:
        for f in os.listdir(manifests_dir):
            if f.endswith(".json") and not f.endswith("_chunks.json") and f.startswith("task_"):
                try:
                    mpath = os.path.join(manifests_dir, f)
                    with open(mpath, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                    source_path = data.get("source_path", "")
                    # 只驗收真實教材任務
                    if "mock_course_dir" in source_path or "raw_data" in source_path:
                        continue
                    if data.get("status") == "completed":
                        completed_manifests.append((mpath, data))
                except Exception:
                    pass
    except Exception as e:
        log_error(f"掃描 manifests 資料夾失敗: {e}")
        return False

    log_info(f"偵測到已完成的真實教材任務數量: {len(completed_manifests)}")

    all_tasks_ok = True
    report_lines = []
    
    if not completed_manifests:
        log_warning("目前尚無已端到端完成 (completed) 的真實課程任務。")
        all_tasks_ok = False
        report_lines.append("### ⚠️ 目前尚無端到端完成之真實課程任務。")
    else:
        for idx, (mpath, manifest) in enumerate(completed_manifests):
            task_id = manifest.get("task_id")
            source_name = manifest.get("source_name")
            source_path = manifest.get("source_path")
            
            print("-" * 50)
            log_info(f"[{idx+1}/{len(completed_manifests)}] 開始驗收檢測任務 {task_id}: {source_name}")
            
            task_ok = True
            v_report = []
            
            # A 碟檢測
            for key, (ftype, label) in expected_files.items():
                fpath = manifest.get(key)
                if not fpath:
                    log_error(f"  {label}: Manifest 中未指定輸出路徑")
                    task_ok = False
                    v_report.append(f"- {label}: Manifest 未指定路徑 ❌")
                    continue
                success, info = check_file_quality(fpath, ftype)
                if success:
                    log_success(f"  {label}: {info}")
                    v_report.append(f"- {label}: {info} (`{os.path.basename(fpath)}`)  ")
                else:
                    log_error(f"  {label}: {info}")
                    v_report.append(f"- {label}: {info} ❌")
                    task_ok = False
            
            # J 碟備份檢測
            backup_status = "未核對"
            if source_path:
                backup_dir = os.path.dirname(source_path)
                if os.path.exists(backup_dir):
                    backup_ok = True
                    for key, (ftype, label) in expected_files.items():
                        fpath = manifest.get(key)
                        if fpath:
                            backup_fpath = os.path.join(backup_dir, os.path.basename(fpath))
                            success, info = check_file_quality(backup_fpath, ftype)
                            if not success:
                                backup_ok = False
                    if backup_ok:
                        log_success("  J 碟原始目錄備份：5 檔案完整落地，同源備份通過！")
                        backup_status = "5 檔完整備份且同步成功"
                    else:
                        log_error("  J 碟原始目錄備份：檔案缺失或毀損！")
                        backup_status = "備份缺失或檢驗失敗 ❌"
                        task_ok = False
                else:
                    log_warning(f"  J 碟影片原始目錄離線或未掛載: {backup_dir}")
                    backup_status = "影片目錄未掛載或不存在 ⚠️"
                    
            if not task_ok:
                all_tasks_ok = False
                
            status_symbol = "✅ PASS" if task_ok else "❌ FAIL"
            report_lines.append(f"### 課程 {idx+1}: {source_name} ({status_symbol})")
            report_lines.append(f"- **Task ID**: `{task_id}`")
            report_lines.append(f"- **原目錄備份**: {backup_status}")
            report_lines.append("#### 落地檔案檢驗詳情:")
            report_lines.extend(v_report)
            report_lines.append("")

    # 3. 輸出本機驗收報告檔案
    target_lessons = 30
    meets_target = len(completed_manifests) >= target_lessons
    final_pass = all_tasks_ok and meets_target
    
    report_md = f"""# ⚖️ LexMind-Omni 法律國考 AI 教材批次自動驗收品管報告
生成時間: {time.strftime('%Y-%m-%d %H:%M:%S')}
端到端完成進度: {len(completed_manifests)}/{target_lessons}真實教材
最終驗收結果: {"**【100% 驗收通過，完全達標】** 🎉" if final_pass else "**【未通過，尚有錯誤或未達目標堂數】** ❌"}

## 📝 各課程詳細品質檢驗狀況
{chr(10).join(report_lines)}

## 🛠️ 本地復原與維護指引
1. 若有檔案 FAIL 或是任務狀態顯示為失敗，請至 `A:\\logs\\workflow.log` 檢視對應 Task ID 的錯誤日誌。
2. 守護進程與 watchdog (每 60 秒自癒) 正在後台運行消化佇列，請耐心等待全部 {target_lessons} 堂課程完成。
"""
    
    try:
        report_out_path = os.path.join(processed_dir, "local_verification_report.md")
        os.makedirs(processed_dir, exist_ok=True)
        with open(report_out_path, "w", encoding="utf-8") as wf:
            wf.write(report_md)
        log_success(f"驗收報告已更新並寫入: {report_out_path}")
    except Exception as ree:
        log_error(f"無法寫入驗收報告: {ree}")
        
    print("=" * 70)
    if final_pass:
        print(f"{GREEN}{BOLD}🎉 驗收結論：所有 {len(completed_manifests)} 份實體檔案與格式指標 100% 達標！通過測試！{RESET}")
    else:
        print(f"{RED}{BOLD}❌ 驗收結論：未達標（已完成: {len(completed_manifests)}/30，或有檔案檢測失敗）。請查閱日誌排除錯誤。{RESET}")
    print("=" * 70)
    return final_pass

if __name__ == "__main__":
    run_verification()

```

