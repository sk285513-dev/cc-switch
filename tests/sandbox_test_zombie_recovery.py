import os
import json
import time
import sys
import psutil
from streamlit.testing.v1 import AppTest

sys.path.insert(0, "C:\\LocalAI_Workstation")

STATE_FILE = "C:\\LocalAI_Workstation\\ingest_state.json"

def create_zombie_state():
    # 使用確定不存在的 PID（Windows 上限約 4194304，9999999 必然不存在）
    # 這樣才能正確觸發 app.py 中的 psutil.NoSuchProcess 分支，真實模擬幽靈場景
    state = {
        "status": "running",
        "total_files": 10,
        "processed_count": 5,
        "current_file": "test.mp4",
        "current_action": "Processing...",
        "last_heartbeat": time.time() - 600,  # 10分鐘前 (超過5分鐘的 TTL)
        "worker_pid": 9999999,
        "worker_start_time": time.time() - 86400  # 是晨天的時戳
    }

    with open(STATE_FILE, "w", encoding="utf-8-sig") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print("Created zombie state with non-existent PID=9999999")

def run_test():
    print("Running zombie recovery test...")
    create_zombie_state()
    
    at = AppTest.from_file("C:\\LocalAI_Workstation\\app.py", default_timeout=45)
    
    # 模擬進入 tab2
    # 注意: Streamlit test runner 可能不會自動渲染 fragment，但 app.py 初次載入時可能會載入。
    at.run()
    
    def find_errors(element_list):
        errors = []
        for e in getattr(element_list, 'error', []):
            errors.append(e.value)
        
        for name in dir(element_list):
            if name in ['tabs', 'columns', 'expander', 'container', 'sidebar']:
                try:
                    children = getattr(element_list, name)
                    for child in children:
                        errors.extend(find_errors(child))
                except Exception:
                    pass
        return errors

    all_errors = find_errors(at)
    
    recovered = False
    for msg in all_errors:
        if "背景進程已經死亡" in msg or "系統自動修復" in msg or "crashed unexpectedly" in msg:
            recovered = True
            print(f"✅ Success! Auto-healing message found: {msg}")
            break
            
    if not recovered:
        print("❌ Failed! Auto-healing message not found.")
        print("Current errors in UI:")
        for msg in all_errors:
            print(f" - {msg}")
            
    # 驗證 disk 狀態是否被重置為 error
    try:
        with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
            state = json.load(f)
            if state.get("status") == "error":
                print("✅ Success! State file was updated to status=error")
            else:
                print(f"❌ Failed! State file status is {state.get('status')}")
    except Exception as e:
        print(f"❌ Failed to read state file: {e}")

if __name__ == "__main__":
    run_test()
