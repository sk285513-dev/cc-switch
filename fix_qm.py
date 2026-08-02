import os

with open('C:/LocalAI_Workstation/LexMind_Code_Backup_v5.0_Ultimate_20260725_221055/Workstation_Scripts/scripts/quota_manager.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix 1: try-except sys.stdout
old_stdout = "sys.stdout.reconfigure(encoding='utf-8', errors='replace')"
new_stdout = """try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass"""
code = code.replace(old_stdout, new_stdout)

# Fix 2: RLock
old_lock = "self.lock = threading.Lock()"
new_lock = "self.lock = threading.RLock()"
code = code.replace(old_lock, new_lock)

# Fix 3: exclusive arg in handle_error
old_sig = "def handle_error(self, e: Exception, current_key: str, consecutive_429: int):"
new_sig = "def handle_error(self, e: Exception, current_key: str, consecutive_429: int, exclusive: bool = False):"
code = code.replace(old_sig, new_sig)

with open('C:/LocalAI_Workstation/scripts/quota_manager.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("QuotaManager fully restored and patched safely.")
