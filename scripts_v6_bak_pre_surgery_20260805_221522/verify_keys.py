import os
import sys
import json
import time
import requests
import ctypes
from pathlib import Path
from quota_manager import QuotaManager
from workflow_helper import log_workflow

def alert_and_beep(message):
    """彈出 Windows 警告視窗並播放提示音"""
    MB_ICONWARNING = 0x30
    try:
        ctypes.windll.user32.MessageBeep(MB_ICONWARNING)
        ctypes.windll.user32.MessageBoxW(0, message, "LexMind-Omni 系統警報", MB_ICONWARNING)
    except Exception as e:
        print(f"Error triggering alert: {e}")

def test_api_key(key):
    """測試單一金鑰是否可用 (使用最省額度的 countTokens)"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:countTokens?key={key}"
    payload = {
        "contents": [{
            "parts": [{"text": "Hello"}]
        }]
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        return False

def verify_and_recover_keys():
    """測試所有金鑰，若有可用的則清除耗盡狀態，若全死則發出警報。"""
    try:
        from workflow_helper import load_config
        config = load_config()
        if config.get("settings", {}).get("stt_engine") == "vertexai":
            log_workflow("🚀 [Key Verification] 系統目前使用 Vertex AI 企業通道，無需測試金鑰，自動放行。")
            return True

        qm = QuotaManager()
        keys = qm.keys
    except Exception as e:
        log_workflow(f"⚠️ [Key Verification] 無法載入金鑰或配置: {e}")
        return False

    if not keys:
        log_workflow("⚠️ [Key Verification] 沒有找到任何金鑰。")
        return False
        
    log_workflow(f"🔄 [Key Verification] 系統遭到 Quota 或 Hard Gate 攔截，開始測試 {len(keys)} 把金鑰是否恢復...")
    
    recovered_key = None
    for idx, k in enumerate(keys):
        k_masked = f"{k[:8]}...{k[-4:]}" if len(k) > 12 else "INVALID_KEY"
        if test_api_key(k):
            recovered_key = k
            log_workflow(f"✅ [Key Verification] 找到可用金鑰: {k_masked} (第 {idx+1} 把)")
            break
            
    if recovered_key:
        # 重設 exhausted 狀態
        try:
            quota_state_file = Path("config/quota_state.json")
            if quota_state_file.exists():
                quota_state_file.write_text(json.dumps({"exhausted_keys": []}, ensure_ascii=False), encoding="utf-8-sig")
                
            api_keys_state_file = Path("A:/manifests/api_keys_state.json")
            if api_keys_state_file.exists():
                os.remove(api_keys_state_file)
                
            log_workflow("🚀 [Key Verification] 已重置所有耗盡狀態，系統可繼續運行。")
            return True
        except Exception as e:
            log_workflow(f"⚠️ [Key Verification] 重置狀態失敗: {e}")
            return True 
    else:
        log_workflow(f"🚨 [Key Verification] 測試了 {len(keys)} 把金鑰，全數皆為 429/403 (Quota Exceeded)！")
        # 觸發警報
        alert_msg = f"注意：所有 {len(keys)} 把 Gemini API 金鑰已達配額上限！\n\n系統將進入長時間冷卻，請立即補充新金鑰至 keys.yaml，或等待 Google 恢復配額。"
        
        # 開啟獨立 thread 避免 block 流程
        import threading
        threading.Thread(target=alert_and_beep, args=(alert_msg,), daemon=True).start()
        
        return False

if __name__ == "__main__":
    verify_and_recover_keys()
