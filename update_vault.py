import os
import re

file_path = r'C:\LocalAI_Workstation\utils\vault.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

secure_wiper = '''
class SecureMemoryWiper:
    @staticmethod
    def wipe_bytearray(key_bytes: bytearray):
        if not isinstance(key_bytes, bytearray) or not key_bytes: return
        import ctypes
        c_char_array = (ctypes.c_char * len(key_bytes)).from_buffer(key_bytes)
        ctypes.memset(ctypes.byref(c_char_array), 0, len(key_bytes))

class Vault:
'''

if 'class SecureMemoryWiper:' not in content:
    content = content.replace('class Vault:', secure_wiper.strip())

# Allow key_manager in _verify_process
verify_code = '''
            if not any(arg in cmd for arg in ["api_proxy", "key_manager"] for cmd in cmdline):
                raise Exception("Access Denied: 只有 api_proxy.py 或 key_manager.py 可以存取金鑰保險箱。")
'''
if 'key_manager' not in content:
    content = re.sub(
        r'if not any\("api_proxy" in arg for arg in cmdline\):\s*raise Exception\("Access Denied: 只有 api_proxy.py 可以存取金鑰保險箱。"\)',
        verify_code.strip(),
        content
    )

# Use SecureMemoryWiper in encrypt_data and decrypt_data
encrypt_old = '''
    @classmethod
    def encrypt_data(cls, data: str) -> str:
        """將純文字字串加密為 Fernet 格式字串"""
        fernet = Fernet(cls._get_or_create_key())
        encrypted = fernet.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')
'''
encrypt_new = '''
    @classmethod
    def encrypt_data(cls, data: str) -> str:
        """將純文字字串加密為 Fernet 格式字串"""
        master_key = bytearray(cls._get_or_create_key())
        try:
            fernet = Fernet(bytes(master_key))
            encrypted = fernet.encrypt(data.encode('utf-8'))
            return encrypted.decode('utf-8')
        finally:
            SecureMemoryWiper.wipe_bytearray(master_key)
'''

decrypt_old = '''
    @classmethod
    def decrypt_data(cls, data: str) -> str:
        """將 Fernet 格式字串解密為純文字字串"""
        fernet = Fernet(cls._get_or_create_key())
        # 若傳入的 data 不是有效的 Fernet Token，此處會噴 InvalidToken
        decrypted = fernet.decrypt(data.encode('utf-8'))
        return decrypted.decode('utf-8')
'''
decrypt_new = '''
    @classmethod
    def decrypt_data(cls, data: str) -> str:
        """將 Fernet 格式字串解密為純文字字串"""
        master_key = bytearray(cls._get_or_create_key())
        try:
            fernet = Fernet(bytes(master_key))
            # 若傳入的 data 不是有效的 Fernet Token，此處會噴 InvalidToken
            decrypted = fernet.decrypt(data.encode('utf-8'))
            return decrypted.decode('utf-8')
        finally:
            SecureMemoryWiper.wipe_bytearray(master_key)
'''

content = content.replace(encrypt_old.strip(), encrypt_new.strip())
content = content.replace(decrypt_old.strip(), decrypt_new.strip())

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated utils/vault.py")
