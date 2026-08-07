# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 3: 金鑰安全與保險箱 (Security & Vault)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 3】。
# 負責 Vertex AI / Gemini 金鑰加密解密與 429 斷路器輪替。絕不可破壞此處的保護機制。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import os
import base64
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecureMemoryWiper:
    @staticmethod
    def wipe_bytearray(key_bytes: bytearray):
        if not isinstance(key_bytes, bytearray) or not key_bytes: return
        import ctypes
        import os
        try:
            data_len = len(key_bytes)
            c_buffer = (ctypes.c_char * data_len).from_buffer(key_bytes)
            buffer_address = ctypes.addressof(c_buffer)
            
            # 【修補 Issue 34：跨平台相容】防呆處理 Windows API 強綁定
            if os.name == 'nt':
                kernel32 = ctypes.windll.kernel32
                RtlSecureZeroMemory = kernel32.RtlSecureZeroMemory
                RtlSecureZeroMemory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                RtlSecureZeroMemory.restype = ctypes.c_void_p
                RtlSecureZeroMemory(buffer_address, data_len)
            else:
                libc = ctypes.CDLL(None)
                memset = libc.memset
                memset.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
                memset.restype = ctypes.c_void_p
                memset(buffer_address, 0, data_len)
        except Exception:
            pass
        finally:
            key_bytes.clear()

class Vault:
    """
    Vault 負責本機端安全金鑰的加解密 (Expert Sweeps 終極加固版)。
    
    盲點防禦：
    1. KDF 衍生：將任意字串密碼轉換為 AESGCM 要求的 32-byte 金鑰。
    2. 隨機 Salt：寫入時生成隨機 16-byte salt，並前綴於密文。
    3. 環境變數抹除：讀取完立刻抹除，防止子進程繼承外洩。
    """
    def __init__(self, vault_file="config/secure_keys.vault"):
        self.vault_file = vault_file
        self.local_key_file = "config/vault.key"
        self._raw_pass = self._load_master_key()

    def _load_master_key(self) -> bytes:
        # 第一優先：從作業系統環境變數讀取
        env_key = os.environ.get("LEXMIND_VAULT_KEY")
        if env_key:
            logging.info("Vault: Successfully loaded master key from Environment Variable.")
            # 【資安修補】：立刻抹除，避免被 subprocess (如 FFmpeg) 繼承外洩
            os.environ.pop("LEXMIND_VAULT_KEY", None)
            return env_key.encode('utf-8')
            
        # 第二優先：從本地開發檔案讀取 (不建議在生產環境使用)
        if os.path.exists(self.local_key_file):
            logging.warning("Vault: Using local vault.key file. This is NOT recommended for production!")
            with open(self.local_key_file, "rb") as f:
                raw_data = f.read().strip()
                # 【修復 Issue 23】Vault 缺乏信任根，使用 Windows DPAPI 解密 Master Key (綁定當前使用者)
                try:
                    import win32crypt
                    _, decrypted_key = win32crypt.CryptUnprotectData(raw_data, None, None, None, 0)
                    return decrypted_key
                except Exception:
                    # 相容舊版未加密的 Key
                    return raw_data
                
        logging.error("Vault: Master key not found! Please set LEXMIND_VAULT_KEY.")
        return None

    def _derive_256bit_key(self, salt: bytes) -> bytes:
        """使用 PBKDF2HMAC 將原始密碼衍生為合法的 AES-256 金鑰"""
        if not self._raw_pass:
            raise ValueError("Master key is missing.")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return kdf.derive(self._raw_pass)

    def generate_and_save_new_master_key(self):
        """
        生成全新隨機密碼 (非 Fernet Key，而是一般高強度字串)，並存入實體檔案。
        """
        new_pass = base64.urlsafe_b64encode(os.urandom(32))
        os.makedirs(os.path.dirname(self.local_key_file), exist_ok=True)
        
        # 【修復 Issue 23】Vault 缺乏信任根，使用 Windows DPAPI 加密 Master Key
        try:
            import win32crypt
            protected_pass = win32crypt.CryptProtectData(new_pass, "LexMind Vault Master Key", None, None, None, 0)
        except Exception:
            protected_pass = new_pass
            
        with open(self.local_key_file, "wb") as f:
            f.write(protected_pass)
        self._raw_pass = new_pass
        return new_pass.decode('utf-8')

    def encrypt_and_save(self, api_keys: list):
        if not self._raw_pass:
            raise ValueError("Vault is not initialized with a master key.")
        
        salt = os.urandom(16)
        key_256 = self._derive_256bit_key(salt)
        aesgcm = AESGCM(key_256)
        nonce = os.urandom(12)
        
        plain_bytes = bytearray(",".join(api_keys).encode('utf-8'))
        # 【修補 Issue 32：確保即使加密報錯也能抹除 Heap 中的金鑰明文】
        try:
            cipher_text = aesgcm.encrypt(nonce, bytes(plain_bytes), None)
        finally:
            SecureMemoryWiper.wipe_bytearray(plain_bytes)
        
        final_payload = salt + nonce + cipher_text
        os.makedirs(os.path.dirname(self.vault_file), exist_ok=True)
        
        import tempfile
        dir_name = os.path.dirname(self.vault_file)
        with tempfile.NamedTemporaryFile('wb', dir=dir_name, delete=False) as tf:
            tf.write(final_payload)
            tf.flush()
            os.fsync(tf.fileno())
            temp_name = tf.name
            
        os.replace(temp_name, self.vault_file)

    def load_and_decrypt(self) -> list:
        if not self._raw_pass:
            logging.error("Vault: Cannot decrypt. Master key missing.")
            return []
            
        if not os.path.exists(self.vault_file):
            return []
            
        try:
            with open(self.vault_file, "rb") as f:
                payload = f.read()
            
            if len(payload) < 28:
                raise ValueError("Payload too short to contain salt and nonce.")
                
            salt = payload[:16]
            nonce = payload[16:28]
            cipher_text = payload[28:]
            
            key_256 = self._derive_256bit_key(salt)
            aesgcm = AESGCM(key_256)
            plain_bytes = bytearray(aesgcm.decrypt(nonce, cipher_text, None))
            # 【修補 Issue 32：確保即使解碼報錯也能抹除】
            try:
                plain_text = plain_bytes.decode('utf-8')
            finally:
                SecureMemoryWiper.wipe_bytearray(plain_bytes)
            
            if not plain_text:
                return []
            return plain_text.split(",")
        except Exception as e:
            logging.error(f"Vault: Decryption failed - {str(e)}")
            return []

    def encrypt_data(self, plain_text: str) -> str:
        """供外部系統使用的一般字串加密 (Issue 8 對接)"""
        if not self._raw_pass:
            raise ValueError("Vault is not initialized.")
        salt = os.urandom(16)
        key_256 = self._derive_256bit_key(salt)
        aesgcm = AESGCM(key_256)
        nonce = os.urandom(12)
        
        plain_bytes = bytearray(plain_text.encode('utf-8'))
        # 【修補 Issue 32】
        try:
            cipher_text = aesgcm.encrypt(nonce, bytes(plain_bytes), None)
        finally:
            SecureMemoryWiper.wipe_bytearray(plain_bytes)
        
        payload = salt + nonce + cipher_text
        return base64.b64encode(payload).decode('utf-8')

    def decrypt_data(self, encrypted_str: str) -> str:
        """供外部系統使用的一般字串解密 (Issue 8 對接)"""
        if not self._raw_pass:
            raise ValueError("Vault is not initialized.")
        try:
            payload = base64.b64decode(encrypted_str)
            if len(payload) < 28:
                return encrypted_str
            salt = payload[:16]
            nonce = payload[16:28]
            cipher_text = payload[28:]
            key_256 = self._derive_256bit_key(salt)
            aesgcm = AESGCM(key_256)
            plain_bytes = bytearray(aesgcm.decrypt(nonce, cipher_text, None))
            # 【修補 Issue 32】
            try:
                res = plain_bytes.decode('utf-8')
            finally:
                SecureMemoryWiper.wipe_bytearray(plain_bytes)
            return res
        except Exception:
            return encrypted_str

