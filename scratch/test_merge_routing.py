import os
import sys
import threading
import logging
from unittest.mock import MagicMock, patch

# 設定專案根目錄
sys.path.append(r"C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站")
sys.path.append(r"C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\scripts")

from scripts.merge_transcript import call_gemini_api
from google.api_core import exceptions as google_exceptions

logging.basicConfig(level=logging.INFO)

class DummyQuotaManager:
    def report_success(self, key):
        pass
    def handle_error(self, e, key, consecutive_429_count=1):
        # Simulate QuotaManager handling 429 and providing a new key
        return {"sleep_time": 0, "new_key": "new_fake_api_key"}

def test_merge_dual_routing():
    qm = DummyQuotaManager()
    current_key_ref = ["fake_api_key"]
    config = {
        "settings": {
            "vertexai_project": "fake_project",
            "vertexai_location": "us-central1"
        }
    }
    
    try:
        with patch('scripts.merge_transcript.genai.Client') as MockClient, \
             patch('scripts.merge_transcript.google.auth.default') as MockAuthDefault:
             
            # 模擬憑證
            MockAuthDefault.return_value = (MagicMock(), "fake_project")
            
            # 模擬 Vertex Client
            mock_client_inst = MagicMock()
            MockClient.return_value = mock_client_inst
            
            # 設定第一階 Base64 拋出 429 錯誤, 第二階正常
            mock_generate_content = MagicMock()
            mock_response_success = MagicMock()
            mock_response_success.text = "gemini merged output"
            
            mock_generate_content.side_effect = [
                google_exceptions.ResourceExhausted("429 Quota Exceeded"), 
                mock_response_success
            ]
            mock_client_inst.models.generate_content = mock_generate_content
            
            # 測試執行
            result = call_gemini_api(
                prompt="test prompt",
                model_name="gemini-2.5-flash",
                qm=qm,
                current_key_ref=current_key_ref,
                config=config
            )
            
            assert result == "gemini merged output", "call_gemini_api 應該回傳成功的文字"
            
            # 驗證 GenAI Client 有被以 Vertex 模式調用
            MockClient.assert_called_with(vertexai=True, project="fake_project", location="us-central1", credentials=MockAuthDefault.return_value[0])
            
            # 驗證換 key 後是否有更新 current_key_ref
            assert current_key_ref[0] == "new_fake_api_key", "遇到 429 後應該要由 QuotaManager 換 key"
            
            print("========================================")
            print("✅ 沙盒測試成功：Merge Agent 成功使用 Vertex AI 並正確處理 429 輪替！")
            print("========================================")

    finally:
        pass

if __name__ == "__main__":
    test_merge_dual_routing()
