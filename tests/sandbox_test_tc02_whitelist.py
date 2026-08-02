import sys
sys.path.insert(0, "C:\\LocalAI_Workstation")
from streamlit.testing.v1 import AppTest

def find_deep_anomalies(element_list, seen=None):
    if seen is None:
        seen = set()
        
    anomalies = []
    # 1. 抓取原生的 error / warning / exception
    for t in ['error', 'warning', 'exception']:
        for e in getattr(element_list, t, []):
            if id(e) not in seen:
                seen.add(id(e))
                anomalies.append((t, e.value if hasattr(e, 'value') else str(e)))
    
    # 2. 啟發式抓取文字標籤內的錯誤關鍵字
    for t in ['markdown', 'text', 'caption', 'info', 'success']:
        for e in getattr(element_list, t, []):
            if id(e) not in seen:
                seen.add(id(e))
                val = e.value if hasattr(e, 'value') else str(e)
                for kw in ["Traceback", "Exception:", "卡死", "異常中斷", "系統自動修復"]:
                    if kw in val:
                        anomalies.append(('heuristic_error', val))
                    
    # 遞迴深入各層級容器
    for name in dir(element_list):
        if name in ['tabs', 'columns', 'expander', 'container', 'sidebar']:
            try:
                children = getattr(element_list, name)
                for child in children:
                    if id(child) not in seen:
                        seen.add(id(child))
                        anomalies.extend(find_deep_anomalies(child, seen))
            except Exception:
                pass
    return anomalies

def test_tc02_logic():
    print("Running sandbox test for TC-0.2 Whitelist & Recursive Traversal...")
    at = AppTest.from_file("C:\\LocalAI_Workstation\\tests\\mock_app_tc02.py", default_timeout=15)
    at.run()
    
    all_anomalies = find_deep_anomalies(at)
    
    has_ui_error = False
    ui_error_msgs = []
    whitelist_triggered = []
    
    for atype, msg in all_anomalies:
        is_whitelisted = False
        # 白名單關鍵字
        for kw in ["尚未實作", "開發中", "敬請期待", "設定頁面", "🚧"]:
            if kw in msg:
                whitelist_triggered.append(msg)
                is_whitelisted = True
                break
                
        if not is_whitelisted and atype in ['error', 'exception', 'heuristic_error']:
            has_ui_error = True
            ui_error_msgs.append(f"[{atype}] {msg}")
        elif not is_whitelisted and atype == 'warning':
            has_ui_error = True
            ui_error_msgs.append(f"[{atype}] {msg}")
            
    print(f"\n[Whitelist Triggered]: {whitelist_triggered}")
    print(f"[Actual Errors Detected]: {ui_error_msgs}")
    
    # 驗證斷言
    assert len(whitelist_triggered) == 1, "Should catch exactly 1 whitelisted warning from the expander."
    assert "尚未實作設定頁面" in whitelist_triggered[0], "Whitelist warning content mismatch."
    
    assert len(ui_error_msgs) == 2, "Should catch exactly 2 errors (1 top level error, 1 deep markdown heuristic error)."
    
    assert any("這是一個頂層的 Error" in msg for msg in ui_error_msgs), "Failed to detect top level error."
    assert any("這裡發生了 Traceback 錯誤！" in msg for msg in ui_error_msgs), "Failed to detect deep heuristic error in tab."
    
    print("\n✅ Sandbox test passed: Recursive Traversal and Whitelist logic are fully operational.")

if __name__ == "__main__":
    test_tc02_logic()
