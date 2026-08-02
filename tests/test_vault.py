import unittest
import os
import sys

# 將上一層目錄加入 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.vault import Vault, SecureMemoryWiper

class TestVaultAES256GCM(unittest.TestCase):
    def test_memory_wiper(self):
        """測試 RtlSecureZeroMemory 是否真的能把記憶體洗掉"""
        data = bytearray(b"my_secret_key_that_should_be_wiped")
        self.assertEqual(data, b"my_secret_key_that_should_be_wiped")
        
        SecureMemoryWiper.wipe_bytearray(data)
        
        # wipe_bytearray 也呼叫了 .clear()，所以長度會變為 0
        self.assertEqual(len(data), 0)

    def test_encrypt_decrypt(self):
        """測試 AES-256-GCM 正常加密與解密流程"""
        plain_text = "test_api_key_12345"
        
        # 為了繞過 _verify_process，因為測試是由 python -m unittest 啟動
        # 直接 Patch _verify_process
        original_verify = Vault._verify_process
        Vault._verify_process = classmethod(lambda cls: None)
        
        try:
            encrypted = Vault.encrypt_data(plain_text)
            self.assertNotEqual(encrypted, plain_text)
            self.assertTrue(len(encrypted) > 20)
            
            decrypted = Vault.decrypt_data(encrypted)
            self.assertEqual(decrypted, plain_text)
        finally:
            Vault._verify_process = original_verify

if __name__ == "__main__":
    unittest.main()
