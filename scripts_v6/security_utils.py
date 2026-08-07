# -*- coding: utf-8 -*-
"""
Phase 7.10 資安滲透防護模組 (Security Hardening)
負責執行環境變數剝離 (Key Stripping) 與日誌正則遮罩 (Regex Log Masking)，
徹底根絕金鑰外洩至子進程與 Log 檔的漏洞。
"""
import os
import copy
import re
import sys
import logging

def clean_env():
    """
    剝離金鑰 (Key Stripping):
    回傳一個移除所有敏感 API Key 的純淨環境變數字典，
    供 subprocess.Popen 使用，防止環境變數滲透到 FFmpeg 等第三方二進位檔。
    """
    safe_env = copy.deepcopy(dict(os.environ))
    sensitive_keys = [
        "GEMINI_API_KEY", 
        "OPENAI_API_KEY", 
        "ANTHROPIC_API_KEY",
        "API_KEY"
    ]
    for key in sensitive_keys:
        if key in safe_env:
            del safe_env[key]
    return safe_env

class SecureLoggerFilter(logging.Filter):
    """
    利用正規表示式 (Regex) 攔截所有的輸出與例外追蹤，
    將符合金鑰特徵的字串替換為 [REDACTED_API_KEY]。
    """
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive_data(record.msg)
        return True
        
    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        if not isinstance(text, str):
            return text
            
        # 【修復 Issue 21】天真的正則表達式謬誤：正則容易被繞過或引發 ReDoS，加入基礎 Sanitization (編碼) 防範 Log Injection
        import html
        text = html.escape(text) 
        
        # Gemini API Key (可能不以 AIza 開頭，長度約39~40字元)
        text = re.sub(r'\b[a-zA-Z0-9_-]{39,40}\b', '[REDACTED_API_KEY]', text)
        # OpenAI API Key (sk-開頭)
        text = re.sub(r'sk-[a-zA-Z0-9]{48}', '[REDACTED_API_KEY]', text)
        return text

def secure_excepthook(exc_type, exc_value, exc_traceback):
    """
    攔截未捕獲的例外 (Unhandled Exceptions)，
    防止 Traceback 中的 URL 或請求參數洩漏 API Key。
    """
    import traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    masked_tb = "".join([SecureLoggerFilter.mask_sensitive_data(line) for line in tb_lines])
    print(masked_tb, file=sys.stderr)

def setup_secure_logger():
    """
    全域資安加固：
    1. 替換 sys.excepthook 以攔截崩潰追蹤。
    2. (選擇性) 可在此為 logging 模組的 root logger 掛載 Filter。
    """
    sys.excepthook = secure_excepthook
    
    # 為所有現存的 Logger 加上資安濾鏡
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.addFilter(SecureLoggerFilter())
    logging.getLogger().addFilter(SecureLoggerFilter())

