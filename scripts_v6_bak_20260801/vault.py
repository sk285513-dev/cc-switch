import os
import keyring
from cryptography.fernet import Fernet, InvalidToken

class SecureMemoryWiper:
    @staticmethod
    def wipe_bytearray(key_bytes: bytearray):
        if not isinstance(key_bytes, bytearray) or not key_bytes: return
        import ctypes
        
        # 使用 ctypes 取出 bytearray 真正的記憶體指標並以 memset 抹除
        c_char_array = (ctypes.c_char * len(key_bytes)).from_buffer(key_bytes)
        ctypes.memset(ctypes.byref(c_char_array), 0, len(key_bytes))

class Vault:
    """金鑰保險箱：整合 Windows 認證管理員 (Credential Manager) 與備援機制"""
    
    SERVICE_NAME = "LexMindVault"
    KEY_ID = "MasterKey"

    @classmethod
    def _get_or_create_key(cls):
        """從 Windows 認證管理員讀取，若無則生成新金鑰並存入"""
        key_str = keyring.get_password(cls.SERVICE_NAME, cls.KEY_ID)
        
        if not key_str:
            # 只有在完全沒有金鑰時才生成
            key = Fernet.generate_key()
            key_str = key.decode('utf-8')
            keyring.set_password(cls.SERVICE_NAME, cls.KEY_ID, key_str)
            
            # 將還原碼寫出給使用者 (僅第一次生成時)
            recovery_file = os.path.abspath("RECOVERY_KEY_DO_NOT_SHARE.txt")
            with open(recovery_file, "w", encoding="utf-8") as rf:
                rf.write("【LexMind-Omni 災難還原碼】\n")
                rf.write("請將下方字串複製到您的 Google 密碼管理員、1Password 或安全筆記中。\n")
                rf.write("萬一重灌電腦，這將是您唯一能找回 API Keys 的方法。\n")
                rf.write("備份完成後，請務必刪除此檔案！\n\n")
                rf.write("=========================================\n")
                rf.write(f"{key_str}\n")
                rf.write("=========================================\n")
            print(f"⚠️ [警告] 已生成新的主金鑰！請查看 {recovery_file} 並備份您的還原碼！")
            
        return key_str.encode('utf-8')

    @classmethod
    def encrypt_data(cls, data: str) -> str:
        """將純文字字串加密為 Fernet 格式字串"""
        fernet = Fernet(cls._get_or_create_key())
        encrypted = fernet.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')

    @classmethod
    def decrypt_data(cls, data: str) -> str:
        """將 Fernet 格式字串解密為純文字字串"""
        fernet = Fernet(cls._get_or_create_key())
        # 若傳入的 data 不是有效的 Fernet Token，此處會噴 InvalidToken
        decrypted = fernet.decrypt(data.encode('utf-8'))
        return decrypted.decode('utf-8')
