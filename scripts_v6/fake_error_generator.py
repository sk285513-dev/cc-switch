import os
import time

LOG_FILE = r"C:\LocalAI_Workstation\logs\ui_test_report.log"

def simulate_error_storm():
    print("沙箱攻防測試: 準備灌入假錯誤至 ui_test_report.log...")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Simulate 5 rapid crashes of the same type to trigger deduplication alert
    with open(LOG_FILE, "a", encoding="utf-8-sig") as f:
        for i in range(5):
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            fake_log = f"[{timestamp}] [FAIL] 沙箱模擬錯誤 (FakeException) - 測試 SRE 哨兵彈窗機制\n"
            f.write(fake_log)
            print(f"注入: {fake_log.strip()}")
            f.flush()
            time.sleep(0.5)

    print("沙箱攻防測試完畢。請觀察是否有出現紅色桌面警告視窗 (MessageBox)！")

if __name__ == "__main__":
    simulate_error_storm()
