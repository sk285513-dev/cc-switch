import sys
import re

path = r'C:\Users\temp\.gemini\antigravity\brain\9ccc4726-3ac1-4fe6-bcb7-aa2c09335f30\implementation_plan.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The section we want to replace
bad_block = """### 6.5 核心資安架構重構 (Windows DPAPI 信任根與記憶體優化)
#### [MODIFY] `C:\\LocalAI_Workstation\\utils\\vault.py`
* **狀態**：⚠️ 待實作 (User Review Required)。
* **實作細節**：完全遵照 135 項計畫之 Issue 23 與 Issue 122 指示。
  1. **導入 DPAPI 信任根 (Issue 23)**：原本 `vault.py` 在初次生成主金鑰時，會將還原碼 (`RECOVERY_KEY`) 以明文寫入實體檔案，存在極高的外洩風險。現在改呼叫 Windows 內建的 DPAPI (`win32crypt.CryptProtectData`) 將 Master Key 加密後，再寫入實體檔案，確保只有本機使用者帳號能解密。
  2. **拔除無效的記憶體清洗 (Issue 122)**：承認 Python 字串不可變（Immutable）的生命週期特性，移除無效的 `SecureMemoryWiper` 與 `ctypes.memset` C API 呼叫，避免產生安全幻覺。改為依賴系統級憑證庫（Credential Manager）的即用即棄。

### 6.6 驗證計畫 (Vault Refactoring Verification Plan)
1. 刪除系統中現有的 `MasterKey` 憑證與還原檔，觸發金鑰重新生成。
2. 驗證產生的還原檔內，資料已是經過 DPAPI 加密後的亂碼（二進位編碼），而非原本的明文字串。
3. 撰寫一段簡單的解密腳本呼叫 `win32crypt.CryptUnprotectData`，確認能還原出正確的金鑰。"""

# The correct section based on user's exact specification
correct_block = """### 6.5 核心資安架構重構 (真 AES-256-GCM 與 Bytearray 實體抹除)
#### [MODIFY] `C:\\LocalAI_Workstation\\utils\\vault.py`
* **狀態**：⚠️ 待實作 (User Review Required)。
* **實作細節**：將 Fernet 升級為標準的 AES-256-GCM，並實作正確的 bytearray 記憶體抹除，防止核心金鑰殘留。
  * **記憶體抹除 (RtlSecureZeroMemory)**：
    ```python
    class SecureMemoryWiper:
        @staticmethod
        def wipe_bytearray(key_bytes: bytearray):
            if not isinstance(key_bytes, bytearray) or not key_bytes: return
            import ctypes
            kernel32 = ctypes.windll.kernel32
            RtlSecureZeroMemory = kernel32.RtlSecureZeroMemory
            RtlSecureZeroMemory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            RtlSecureZeroMemory.restype = ctypes.c_void_p

            data_len = len(key_bytes)
            c_buffer = (ctypes.c_char * data_len).from_buffer(key_bytes)
            RtlSecureZeroMemory(ctypes.addressof(c_buffer), data_len)
            key_bytes.clear()
    ```
  * **AES-256-GCM 落地加密**：
    ```python
    def encrypt_and_save(self, api_keys: list):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key_256 = self._derive_256bit_key(salt) 
        aesgcm = AESGCM(key_256)
        nonce = os.urandom(12)

        # 轉為 bytearray 處理
        plain_bytes = bytearray(",".join(api_keys).encode('utf-8'))

        # AES-256-GCM authenticated encryption
        cipher_text = aesgcm.encrypt(nonce, plain_bytes, None) 

        # 立即從實體記憶體中抹除明文金鑰
        SecureMemoryWiper.wipe_bytearray(plain_bytes)
    ```

### 6.6 驗證計畫 (AES-256-GCM Verification Plan)
1. 於沙盒環境撰寫 `tests/test_vault.py` 進行測試，確認 `AESGCM` 的加密與解密能正確運作。
2. 驗證 `SecureMemoryWiper.wipe_bytearray` 呼叫後，`plain_bytes` 是否確實被清空，確保 `RtlSecureZeroMemory` 未崩潰。"""

if bad_block in content:
    content = content.replace(bad_block, correct_block)
    print("Replaced successfully!")
else:
    print("Could not find bad block!")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
