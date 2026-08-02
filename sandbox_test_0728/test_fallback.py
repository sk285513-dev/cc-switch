import sys
import requests
from unittest.mock import patch, MagicMock

# 將路徑指向正式上線環境的 scripts (因為剛才已經覆蓋過去了)
sys.path.append(r'C:\LocalAI_Workstation\scripts')
import merge_transcript

def test_fallback(model_name):
    print(f"\n=======================================================")
    print(f"[Test] 測試開始，使用者策略選擇的首選模型: {model_name}")
    tried_models = []
    
    # 建立 mock requests.post 來模擬 429 Quota Exhausted
    def mock_post(*args, **kwargs):
        url = args[0] if args else kwargs.get('url', '')
        model = url.split("/models/")[1].split(":")[0] if "/models/" in url else "unknown"
        
        if model not in tried_models:
            tried_models.append(model)
            print(f"  -> 攔截到底層 API 呼叫: 正在嘗試使用模型 【{model}】")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Quota exceeded"
        return mock_resp

    # 替換掉真實的 HTTP 請求
    with patch('merge_transcript.requests.post', side_effect=mock_post):
        # 替換掉時間睡眠，加速測試
        with patch('merge_transcript.time.sleep'):
            # 覆蓋金鑰輪替邏輯，假裝金鑰池已經用盡 (立刻觸發換模型)
            with patch('merge_transcript.get_gemini_key', return_value=None):
                with patch('merge_transcript.mark_key_exhausted', create=True):
                    try:
                        # 呼叫我們剛剛改寫好的函式
                        merge_transcript.call_gemini_api("Test prompt", model_name, "fake_key_123")
                    except Exception as e:
                        print(f"  -> 最終狀態: 任務安全中止，拋出系統錯誤: {e}")
                        
    print(f"  -> 總結：本策略實際嘗試過的模型軌跡: {tried_models}")

# 測試 1：非 Pro 的策略
test_fallback("gemini-2.5-flash")

# 測試 2：Pro 的策略
test_fallback("gemini-2.5-pro")
