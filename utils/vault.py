import os
import keyring
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

class SecureMemoryWiper:
    @staticmethod
    def wipe_bytearray(key_bytes: bytearray):
        if not isinstance(key_bytes, bytearray) or not key_bytes: return
        import ctypes
        kernel32 = ctypes.windll.kernel32
        try:
            RtlSecureZeroMemory = kernel32.RtlSecureZeroMemory
        except AttributeError:
            RtlSecureZeroMemory = kernel32.RtlZeroMemory
        RtlSecureZeroMemory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        RtlSecureZeroMemory.restype = ctypes.c_void_p

        data_len = len(key_bytes)
        c_buffer = (ctypes.c_char * data_len).from_buffer(key_bytes)
        RtlSecureZeroMemory(ctypes.addressof(c_buffer), data_len)
        del c_buffer
        key_bytes.clear()

class Vault:
    """金鑰保險箱：整合 Windows 認證管理員 (Credential Manager) 與備援機制 (AES-256-GCM)"""
    
    SERVICE_NAME = "LexMindVault"
    KEY_ID = "MasterKeyGCM"

    @classmethod
    def _verify_process(cls):
        import psutil
        pid = os.getpid()
        try:
            p = psutil.Process(pid)
            cmdline = p.cmdline()
            # 檢查 cmdline 是否包含被允許的腳本名稱
            allowed_scripts = ["api_proxy", "key_manager", "stt_runner", "merge_transcript", "markdown_formatter", "run_workflow", "migrate_keys_to_gcm", "auto_ingest_bot", "ingest_law", "process_multimodal_file", "preprocess_media", "dashboard", "file_watcher"]
            if not any(arg in cmd for arg in allowed_scripts for cmd in cmdline):
                raise Exception(f"Access Denied: {cmdline} is not allowed to access the vault.")
        except Exception as e:
            raise Exception(f"Access Denied: {e}")

    @classmethod
    def _get_or_create_key(cls):
        cls._verify_process()
        """從 Windows 認證管理員讀取，若無則生成 32-bytes (256-bit) 新金鑰並存入"""
        key_str = keyring.get_password(cls.SERVICE_NAME, cls.KEY_ID)
        
        if not key_str:
            # 生成 32 bytes 隨機金鑰
            raw_key = AESGCM.generate_key(bit_length=256)
            key_str = base64.b64encode(raw_key).decode('utf-8')
            keyring.set_password(cls.SERVICE_NAME, cls.KEY_ID, key_str)
            
            # 將還原碼寫出給使用者 (僅第一次生成時)
            recovery_file = os.path.abspath("RECOVERY_KEY_GCM_DO_NOT_SHARE.txt")
            with open(recovery_file, "w", encoding="utf-8") as rf:
                rf.write("【LexMind-Omni 災難還原碼 (AES-256-GCM)】\n")
                rf.write("請將下方字串複製到您的 Google 密碼管理員、1Password 或安全筆記中。\n")
                rf.write("萬一重灌電腦，這將是您唯一能找回 API Keys 的方法。\n")
                rf.write("備份完成後，請務必刪除此檔案！\n\n")
                rf.write("=========================================\n")
                rf.write(f"{key_str}\n")
                rf.write("=========================================\n")
            print(f"⚠️ [警告] 已生成新的 AES-256-GCM 主金鑰！請查看 {recovery_file} 並備份您的還原碼！")
            
        return key_str.encode('utf-8')

    @classmethod
    def encrypt_data(cls, data: str) -> str:
        """將純文字字串以 AES-256-GCM 加密並轉為 Base64 (nonce + ciphertext)"""
        # key_str is base64 encoded
        key_str = cls._get_or_create_key()
        master_key = bytearray(base64.b64decode(key_str))
        plain_bytes = bytearray(data.encode('utf-8'))
        try:
            aesgcm = AESGCM(bytes(master_key))
            nonce = os.urandom(12)
            cipher_text = aesgcm.encrypt(nonce, bytes(plain_bytes), None)
            
            # return base64(nonce + ciphertext)
            payload = nonce + cipher_text
            return base64.b64encode(payload).decode('utf-8')
        finally:
            SecureMemoryWiper.wipe_bytearray(master_key)
            SecureMemoryWiper.wipe_bytearray(plain_bytes)

    @classmethod
    def decrypt_data(cls, data: str) -> str:
        """將 Base64 格式的 AES-256-GCM (nonce + ciphertext) 解密為純文字字串"""
        key_str = cls._get_or_create_key()
        master_key = bytearray(base64.b64decode(key_str))
        try:
            payload = base64.b64decode(data.encode('utf-8'))
            nonce = payload[:12]
            cipher_text = payload[12:]
            
            aesgcm = AESGCM(bytes(master_key))
            decrypted = aesgcm.decrypt(nonce, cipher_text, None)
            
            decrypted_bytes = bytearray(decrypted)
            try:
                return decrypted_bytes.decode('utf-8')
            finally:
                SecureMemoryWiper.wipe_bytearray(decrypted_bytes)
        except InvalidTag:
            raise Exception("InvalidToken: Decryption failed, possibly corrupted data or wrong key.")
        finally:
            SecureMemoryWiper.wipe_bytearray(master_key)

