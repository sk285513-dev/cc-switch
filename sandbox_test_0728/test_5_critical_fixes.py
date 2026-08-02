import sys
import unittest
import ast
from unittest.mock import patch, MagicMock

sys.path.append(r'C:\LocalAI_Workstation\scripts')
import chunk_planner
import stt_runner
import markdown_formatter
import merge_transcript

class TestLexMindOmniFixes(unittest.TestCase):
    
    def test_01_chunk_planner_limit(self):
        # 測試目標: 確保切片上限的預設值被設為 360 秒，而不是 720 秒
        with open(r'C:\LocalAI_Workstation\scripts\chunk_planner.py', 'r', encoding='utf-8') as f:
            code = f.read()
            
        self.assertIn('get("chunk_limit_video_sec", 360)', code, "Video chunk limit is not safely bounded to 360s.")
        self.assertIn('get("chunk_limit_audio_sec", 360)', code, "Audio chunk limit is not safely bounded to 360s.")
        self.assertNotIn('720', code, "Danger: The 12-minute trap (720s) is still present in chunk_planner.py!")
                
    def test_02_vertexai_429_backoff(self):
        # 測試目標: 確保 Vertex AI 遇到 429 錯誤時，不會當機而是進入避退邏輯
        # 我們直接解析 stt_runner.py 的源碼來確保 429 catch block 包含 vertexai
        with open(r'C:\LocalAI_Workstation\scripts\stt_runner.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        self.assertIn("stt_engine in [\"gemini\", \"vertexai\"]", code, "Vertex AI is missing from the 429 exception handler.")
        
    def test_03_double_execution_removed(self):
        # 測試目標: stt_runner.py 跑完不准用 Popen 偷跑 merge_transcript.py
        with open(r'C:\LocalAI_Workstation\scripts\stt_runner.py', 'r', encoding='utf-8') as f:
            code = f.read()
            
        tree = ast.parse(code)
        popen_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == 'Popen':
                    popen_calls.append(node)
                    
        has_merge_trigger = False
        for call in popen_calls:
            # 將 AST 節點轉回字串來檢查是否呼叫了 merge_transcript
            if "merge_script" in ast.unparse(call) or "merge_transcript.py" in ast.unparse(call):
                has_merge_trigger = True
                
        self.assertFalse(has_merge_trigger, "Double execution vulnerability found! Popen still triggers merge_transcript.py")
        
    def test_04_markdown_formatter_linear_time(self):
        # 測試目標: 當無時間戳長句時，時間分布應該超過 90 秒，線性展開到 360 秒
        long_text = "這是一句測試。 " * 100  # 假裝很長的無時間戳文本
        
        segments = markdown_formatter.parse_transcript_into_timed_segments(long_text, 0, 360)
        
        self.assertTrue(len(segments) > 1, "Should split into multiple lines")
        last_segment = segments[-1]
        
        # 最後一段的 start_time 應該非常靠近結尾 360，絕對不能全小於 90
        self.assertGreater(last_segment["start"], 300, "Timestamps collapsed! Linear distribution failed.")
        
    def test_05_tiered_fallback_matrix(self):
        # 測試目標: 跨策略降級禁止 (Flash 遇到耗盡不能跨越到 Pro)
        tried_models = []
        def mock_post(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            model = url.split("/models/")[1].split(":")[0] if "/models/" in url else "unknown"
            if model not in tried_models:
                tried_models.append(model)
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.text = "Quota exceeded"
            return mock_resp
            
        # 攔截 HTTP 呼叫
        with patch('merge_transcript.requests.post', side_effect=mock_post):
            # 關閉時間睡眠以加速測試
            with patch('merge_transcript.time.sleep'):
                # 模擬金鑰用盡
                with patch('workflow_helper.get_gemini_key', return_value=None):
                    with patch('workflow_helper.mark_key_exhausted', create=True):
                        try:
                            merge_transcript.call_gemini_api("Test prompt", "gemini-2.5-flash", "fake_key")
                        except Exception:
                            pass
                            
        self.assertNotIn("gemini-pro-latest", tried_models, "Security breach! Flash strategy escalated to Pro model.")
        self.assertIn("gemini-2.5-flash", tried_models)
        self.assertIn("gemini-2.0-flash", tried_models)
        self.assertIn("gemini-3.5-flash", tried_models)

if __name__ == '__main__':
    unittest.main(verbosity=2)
