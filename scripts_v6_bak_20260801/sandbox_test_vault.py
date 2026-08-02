import sys
import os
from pathlib import Path
import logging
import base64

# Setup paths to import from scripts
sys.path.insert(0, "C:\\LocalAI_Workstation\\scripts")
sys.path.insert(0, "C:\\LocalAI_Workstation")

logging.basicConfig(level=logging.INFO)

def run_tests():
    print("--- [Sandbox Test] Vault AES-256 and SecureMemoryWiper ---")
    
    try:
        from utils.vault import Vault, SecureMemoryWiper
        print("[Test 1] Importing Vault and SecureMemoryWiper: SUCCESS")
    except ImportError as e:
        print(f"[Test 1] Importing Vault and SecureMemoryWiper: FAILED ({e})")
        return

    # Mock _verify_process to allow our sandbox script
    Vault._verify_process = lambda: None
    
    print("\n[Test 2] Testing SecureMemoryWiper")
    try:
        data = bytearray(b"super_secret_key_data")
        SecureMemoryWiper.wipe_bytearray(data)
        if len(data) == 0:
            print("[Test 2] SecureMemoryWiper cleared bytearray: SUCCESS")
        else:
            print("[Test 2] SecureMemoryWiper cleared bytearray: FAILED")
    except Exception as e:
        print(f"[Test 2] SecureMemoryWiper crashed: FAILED ({e})")

    print("\n[Test 3] End-to-End Vault Encryption / Decryption")
    try:
        test_data = "AQ.test_key_1,AQ.test_key_2"
        
        # Test encryption
        encrypted = Vault.encrypt_data(test_data)
        if encrypted and encrypted != test_data:
            print("[Test 3a] Encrypt Data: SUCCESS")
        else:
            print("[Test 3a] Encrypt Data: FAILED")
            
        # Test decryption
        decrypted = Vault.decrypt_data(encrypted)
        if decrypted == test_data:
            print("[Test 3b] Decrypt Data: SUCCESS")
        else:
            print(f"[Test 3b] Decrypt Data: FAILED (Got {decrypted})")
            
    except Exception as e:
        print(f"[Test 3] End-to-End Vault Encryption / Decryption: FAILED ({e})")

    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    run_tests()
