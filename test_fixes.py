import os
import sys
import json
import time
from datetime import datetime

# Add scripts directory to path to import
sys.path.append(r"C:\LocalAI_Workstation\scripts_v6")

def test_bom_read():
    print("--- 測試 1: UTF-8 BOM 讀取測試 ---")
    test_file = "test_bom_manifest.json"
    try:
        # Create a file WITH a UTF-8 BOM
        with open(test_file, 'w', encoding='utf-8-sig') as f:
            f.write('{"status": "chunked", "test": "ok"}')
        
        # Try to read it using the fix (utf-8-sig)
        # We will simulate stt_runner.py's exact line:
        with open(test_file, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            print(f"[PASS] 成功讀取含 BOM 的 JSON: {data}")
    except Exception as e:
        print(f"[FAIL] 讀取失敗: {e}")
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_watchdog_rate_limit():
    print("\n--- 測試 2: SRE Watchdog 彈窗防洪與 ctypes 測試 ---")
    try:
        old_stdout = sys.stdout
        import sre_watchdog
        sys.stdout = old_stdout
        
        # We will mock ctypes.windll.user32.MessageBoxTimeoutW to just count calls
        call_count = 0
        def mock_msgbox(*args):
            nonlocal call_count
            call_count += 1
            print(f"       [Mock API] MessageBoxTimeoutW 真的被呼叫了! (次數: {call_count})")
        
        # Replace the real API with our mock so we don't actually pop up during test
        # (Though even if we didn't, the real one is non-blocking with timeout)
        original_msgbox = sre_watchdog.ctypes.windll.user32.MessageBoxTimeoutW
        sre_watchdog.ctypes.windll.user32.MessageBoxTimeoutW = mock_msgbox
        
        print("連環呼叫 show_toast 5 次 (模擬多個任務同時崩潰)...")
        for i in range(5):
            sre_watchdog.show_toast(f"Test {i}", f"Message {i}")
            # wait a tiny bit to simulate tight loop
            time.sleep(0.1)
            
        # Give daemon threads a moment to run
        time.sleep(1)
        
        if call_count == 1:
            print("[PASS] 防洪機制生效！5 次呼叫只觸發了 1 次彈窗。")
        else:
            print(f"[FAIL] 防洪機制失效！觸發了 {call_count} 次彈窗。")
            
        # Restore API
        sre_watchdog.ctypes.windll.user32.MessageBoxTimeoutW = original_msgbox
        
    except Exception as e:
        print(f"[FAIL] Watchdog 測試發生錯誤: {e}")

if __name__ == "__main__":
    test_bom_read()
    test_watchdog_rate_limit()
