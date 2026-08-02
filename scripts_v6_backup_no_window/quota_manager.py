import os
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import yaml
import json
import time
import random
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
script_dir = os.path.dirname(os.path.abspath(__file__))
potential_paths = [
    os.path.join(script_dir, ".env"),
    os.path.join(script_dir, "..", ".env"),
    os.path.join(script_dir, "..", "..", ".env"),
    os.path.join(os.getcwd(), ".env"),
    "c:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\.env"
]
for p in potential_paths:
    if os.path.exists(p):
        load_dotenv(p)

class QuotaManager:
    def __init__(self, keys_path: str = "config/keys.yaml", policy_path: str = "config/quota_policy.yaml", state_path: str = "config/quota_state.json"):
        self.keys_path = Path(keys_path)
        self.policy_path = Path(policy_path)
        self.state_path = Path(state_path)
        self.lock_path = str(self.state_path) + ".lock"
        self._load_keys()
        self._load_policy()
        self._load_state()

    def _load_keys(self):
        yaml_keys = []
        
        # 1. Try config/keys.yaml
        try:
            from key_manager import KeyManager
            km_keys = KeyManager.load_keys()
            for item in km_keys:
                val = item.get("value")
                if val and item.get("active", True) and not val.startswith("YOUR_GEMINI_API_KEY") and val != "AUTO_LOAD_FROM_ENV" and val not in yaml_keys:
                    yaml_keys.append(val)
        except Exception as e:
            logging.warning(f"Failed to load keys using KeyManager: {e}")

        # 2. Try GEMINI_API_KEYS (comma-separated env)
        env_keys_str = os.environ.get("GEMINI_API_KEYS")
        if env_keys_str:
            for k in env_keys_str.split(","):
                k_clean = k.strip()
                if k_clean and not k_clean.startswith("YOUR_GEMINI_API_KEY") and k_clean not in yaml_keys:
                    yaml_keys.append(k_clean)

        # 3. Try GEMINI_API_KEY (single env)
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key:
            env_key = env_key.strip()
            if env_key and not env_key.startswith("YOUR_GEMINI_API_KEY") and env_key not in yaml_keys:
                yaml_keys.append(env_key)

        # 4. Try config.yaml api.gemini_api_key or api.gemini_api_keys
        config_yaml_path = Path("config.yaml")
        if config_yaml_path.exists():
            try:
                with open(config_yaml_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if cfg and "api" in cfg:
                    api_cfg = cfg.get("api", {})
                    # 支援單一字串
                    val = api_cfg.get("gemini_api_key")
                    if val and isinstance(val, str):
                        val = val.strip()
                        if val and not val.startswith("YOUR_GEMINI_API_KEY") and val != "AUTO_LOAD_FROM_ENV" and val not in yaml_keys:
                            yaml_keys.append(val)
                    
                    # 支援陣列 (統一由config.yaml管理)
                    keys_list = api_cfg.get("gemini_api_keys")
                    if keys_list and isinstance(keys_list, list):
                        for k in keys_list:
                            k_clean = str(k).strip()
                            if k_clean and not k_clean.startswith("YOUR_GEMINI_API_KEY") and k_clean not in yaml_keys:
                                yaml_keys.append(k_clean)
            except Exception as e:
                logging.warning(f"Failed to load key from config.yaml: {e}")

        self.keys = yaml_keys
        if not self.keys:
            raise ValueError("No valid Gemini API keys found in config/keys.yaml, config.yaml, or environment variables.")
        # status per key
        self.key_status = {k: {"exhausted": False, "retry_count": 0, "last_failed": None} for k in self.keys}
        # Thread-safety: global lock for all state mutations
        self._lock = threading.Lock()
        # Tracks keys currently leased to a running task (exclusive mode)
        self._in_use_keys: set = set()
        # ★ Per-key RPM 限速：每把 key 最多 6 RPM（10 秒/次）
        # 實測：並發=10 + 29 clean keys → 23.5/hr 有效
        self.MAX_RPM = 6
        self._key_last_call: dict = {}   # key → last call timestamp
        self._rpm_lock = threading.Lock()

    def _load_policy(self):
        if not self.policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {self.policy_path}")
        with open(self.policy_path, "r", encoding="utf-8") as f:
            policy = yaml.safe_load(f)
        self.base_backoff = policy.get("base_backoff_seconds", 30)
        self.multiplier = policy.get("backoff_multiplier", 2)
        self.jitter_frac = policy.get("jitter_fraction", 0.2)
        self.daily_cooldown = policy.get("daily_limit_cooldown_seconds", 300)
        self.max_backoff = policy.get("max_backoff_seconds")  # can be None for unlimited

    def _read_update_state(self, callback):
        from filelock import FileLock, Timeout
        import logging

        lock = FileLock(self.lock_path, timeout=15)
        try:
            with lock:
                return callback()
        except Timeout:
            logging.error(f"QuotaManager: [FATAL] 獲取 {self.lock_path} 鎖死超時！防禦性撤退以避免崩潰。")
            return None

    def _load_state(self):
        exhausted_keys = []
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                exhausted_keys = state.get("exhausted_keys", [])
            except Exception as e:
                logging.warning(f"Failed to load quota state: {e}")
        
        for k in self.keys:
            is_exhausted = k in exhausted_keys
            self.key_status[k] = {
                "exhausted": is_exhausted,
                "retry_count": 3 if is_exhausted else 0,
                # 修復：重啟後不把 last_failed 設成「現在」，避免冷卻倒計時無限重置
                # 設 None 讓 key 在重啟後立即嘗試，由真實 429 回應決定是否繼續凍結
                "last_failed": None
            }

    def _save_state(self):
        """Must be called while holding self._lock, or from within a locked method."""
        try:
            exhausted = [k for k, info in self.key_status.items() if info["exhausted"]]
            state = {"exhausted_keys": exhausted}
            os.makedirs(self.state_path.parent, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"Failed to save quota state: {e}")

    def acquire_key(self) -> str:
        """取得任意一把可用金鑰（非排他性，向後兼容舊版呼叫）。"""
        with self._lock:
            for k, info in self.key_status.items():
                if not info["exhausted"]:
                    return k
        raise RuntimeError("All API keys are exhausted. No usable key available.")

    def acquire_key_exclusive(self) -> str:
        """【多工並列專用】為一個 Task 取得排他性金鑰，確保不與其他 Task 共用同一把金鑰。
        同一把金鑰不會被兩個並列 Task 同時持有。
        """
        with self._lock:
            for k, info in self.key_status.items():
                if not info["exhausted"] and k not in self._in_use_keys:
                    self._in_use_keys.add(k)
                    logging.debug(f"QuotaManager: 排他性鎖定金鑰 {k[:8]}...{k[-4:]}")
                    return k
        raise RuntimeError("所有金鑰均已被其他 Task 佔用或耗盡，無法取得排他性金鑰。")

    def throttle_key(self, key: str):
        """★ RPM 限速：確保同一把 key 兩次請求之間最少間隔 60/MAX_RPM 秒。
        在每次 Gemini API 呼叫前呼叫此方法，消除暴衝 429 循環。"""
        min_interval = 60.0 / self.MAX_RPM   # = 6.0 秒
        with self._rpm_lock:
            last = self._key_last_call.get(key, 0)
            wait = min_interval - (time.time() - last)
            if wait > 0:
                logging.debug(f"[RPM Throttle] key ...{key[-4:]}: 等待 {wait:.1f}s")
                time.sleep(wait)
            self._key_last_call[key] = time.time()

    def release_key(self, key: str):
        """【多工並列專用】Task 完成或失敗後釋放排他性金鑰，回到可用池。"""
        with self._lock:
            self._in_use_keys.discard(key)
            logging.debug(f"QuotaManager: 釋放金鑰 {key[:8]}...{key[-4:]}")

    def mark_exhausted(self, key: str):
        with self._lock:
            if key in self.key_status:
                self.key_status[key]["exhausted"] = True
                self._save_state()

    def reset_key(self, key: str):
        with self._lock:
            if key in self.key_status:
                self.key_status[key]["exhausted"] = False
                self.key_status[key]["retry_count"] = 0
                self.key_status[key]["last_failed"] = None
                self._save_state()

    def reset_all_keys(self):
        """在專案級冷卻睡眠結束後，重設所有金鑰的耗盡狀態，使輪替池恢復可用。"""
        with self._lock:
            for k in self.key_status:
                self.key_status[k]["exhausted"] = False
                self.key_status[k]["retry_count"] = 0
                self.key_status[k]["last_failed"] = None
            self._save_state()
        logging.info(f"QuotaManager: 所有 {len(self.keys)} 組金鑰已重設，專案級冷卻完成，繼續輪替。")

    def _parse_error(self, e: Exception):
        """Extract useful info from Gemini exception string.
        Returns (is_daily_limit: bool, retry_delay: float|None)
        """
        err_str = str(e)
        is_daily = False
        retry_delay = None
        try:
            if "{" in err_str:
                import ast
                dict_str = err_str[err_str.find("{") :]
                err_data = ast.literal_eval(dict_str)
                details = err_data.get("error", {}).get("details", [])
                for detail in details:
                    if detail.get("@type") == "type.googleapis.com/google.rpc.QuotaFailure":
                        for violation in detail.get("violations", []):
                            quota_id = violation.get("quotaId", "")
                            if "perday" in quota_id.lower():
                                is_daily = True
                    elif detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                        delay_str = detail.get("retryDelay", "")
                        match = re.search(r"(\d+\.?\d*)", delay_str)
                        if match:
                            retry_delay = float(match.group(1))
        except Exception:
            pass
        # fallback regex for generic messages
        if retry_delay is None:
            import re
            m = re.search(r"Please retry in (\d+\.?\d*)s", err_str)
            if m:
                retry_delay = float(m.group(1))
        return is_daily, retry_delay

    def compute_backoff(self, consecutive_429: int, is_daily_limit: bool, api_retry_delay: float | None) -> float:
        # base sleep from policy or from API suggestion
        base = api_retry_delay if api_retry_delay is not None else self.base_backoff
        # exponential multiplier
        multiplier = min(16, self.multiplier ** (consecutive_429 - 1)) if consecutive_429 > 0 else 1
        sleep_time = (base + 2.0) * multiplier
        if is_daily_limit:
            sleep_time = max(sleep_time, self.daily_cooldown)
        # jitter
        jitter = sleep_time * self.jitter_frac * (random.random() * 2 - 1)  # ± jitter_frac
        sleep_time = sleep_time + jitter
        if self.max_backoff is not None:
            sleep_time = min(sleep_time, self.max_backoff)
        return max(sleep_time, 0)

    def handle_error(self, e: Exception, current_key: str, consecutive_429: int, exclusive: bool = False):
        """Process an exception, decide whether to rotate key and how long to wait."""
        import google.api_core.exceptions as google_exceptions
        
        safe_err_msg = str(e)
        is_429 = (isinstance(e, google_exceptions.ResourceExhausted) or 
                  getattr(e, 'code', None) == 429 or 
                  "429" in safe_err_msg or 
                  "RESOURCE_EXHAUSTED" in safe_err_msg or 
                  "quota" in safe_err_msg.lower())
        is_401 = (isinstance(e, (google_exceptions.Forbidden, google_exceptions.Unauthorized)) or 
                  "401" in safe_err_msg or 
                  "Unauthorized" in safe_err_msg or
                  "UNAUTHENTICATED" in safe_err_msg or
                  "403" in safe_err_msg or
                  "PERMISSION_DENIED" in safe_err_msg)

        is_daily, api_delay = self._parse_error(e)
        sleep_time = self.compute_backoff(consecutive_429, is_daily, api_delay)
        
        # 預設不換金鑰，繼續使用當前金鑰重試
        new_key = current_key
        project_cooldown = False
        
        # ── 401 Unauthorized：金鑰無效，立即永久停用，不浪費重試時間 ──
        if is_401:
            logging.warning(f"[QuotaManager] Key {current_key[:12]}... 返回 401 Unauthorized，永久停用並輪替")
            self.mark_exhausted(current_key)
            self.release_key(current_key)
            try:
                try:
                    new_key = self.acquire_key_exclusive()
                except RuntimeError:
                    new_key = self.acquire_key()
            except RuntimeError:
                new_key = None
                project_cooldown = True
            return {"sleep_time": 0, "new_key": new_key, "project_cooldown": project_cooldown}

        # 當連續 429 達到 3 次時，標記該金鑰為 exhausted 並嘗試取得下一把金鑰
        if is_429 and consecutive_429 >= 3:
            logging.warning(f"Key {current_key[:8]}... marked exhausted after {consecutive_429} consecutive 429s")
            self.mark_exhausted(current_key)
            # 釋放排他鎖（如果有），讓 acquire_key_exclusive 可以找到新金鑰
            self.release_key(current_key)
            try:
                # 嘗試排他性取得新金鑰（多工模式），若失敗則回退到非排他模式
                try:
                    new_key = self.acquire_key_exclusive()
                except RuntimeError:
                    new_key = self.acquire_key()
            except RuntimeError:
                # 輪替池已完全耗盡，必須進入專案級大冷卻
                new_key = None
                
        # 只有在 new_key 為 None (真正全部耗盡) 時才觸發大睡眠冷卻與重設
        if new_key is None:
            project_cooldown = True
            # enforce at least daily_cooldown seconds
            sleep_time = max(sleep_time, self.daily_cooldown)
            logging.warning(f"所有 API 金鑰皆已耗盡！將進行專案級冷卻，強制睡眠 {sleep_time:.2f} 秒...")
            time.sleep(sleep_time)
            # After sleeping, reset all keys so the pool is usable again
            self.reset_all_keys()
            try:
                new_key = self.acquire_key()
            except RuntimeError:
                new_key = None
            # Signal caller that sleep was already done (sleep_time=0)
            sleep_time = 0
        return {"sleep_time": sleep_time, "new_key": new_key, "project_cooldown": project_cooldown}

# Helper to load keys for existing workflow_helper (kept for backward compatibility)
def load_keys_yaml(path: str = "config/keys.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [item["value"] for item in data.get("keys", [])]
