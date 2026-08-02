import sys
import os
sys.path.append('scripts')
import time
from unittest.mock import patch
from merge_transcript import call_gemini_api
from workflow_helper import get_gemini_key

def test_workflow_helper_wrapper():
    print("=== Testing workflow_helper Wrapper ===")
    key1 = get_gemini_key()
    print(f"[Wrapper Test] First acquired key: {key1[:8]}..." if key1 else "Failed to get key")
    assert key1 != "", "get_gemini_key returned empty string"
    print("✓ workflow_helper wrapper successfully retrieved a key via QuotaManager.\n")

class MockResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text
    def json(self):
        return self._json

# We will count how many times post is called.
call_count = 0

def mocked_requests_post(*args, **kwargs):
    global call_count
    call_count += 1
    # First 2 calls: return 429 Too Many Requests to simulate rate limit
    if call_count <= 2:
        print(f"  [Mock API] Returning HTTP 429 (Too Many Requests) on attempt {call_count}")
        return MockResponse(429, text='{"error": {"message": "Quota exceeded", "code": 429, "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "2s"}]}}')
    
    # 3rd call: Return success 200
    print(f"  [Mock API] Returning HTTP 200 (Success) on attempt {call_count}")
    return MockResponse(200, json_data={"candidates": [{"content": {"parts": [{"text": "Mock successful response text"}]}}]})

@patch('requests.post', side_effect=mocked_requests_post)
@patch('workflow_helper.load_config')
def test_merge_transcript_retry_logic(mock_load_config, mock_post):
    mock_load_config.return_value = {"settings": {"merge_engine": "aistudio"}, "api": {}}
    print("=== Testing merge_transcript.py Retry Logic with Jitter ===")
    start_time = time.time()
    
    # This should trigger 2x 429s, triggering the QuotaManager handle_error with Jitter, 
    # then succeed on the 3rd try.
    result = call_gemini_api("Test prompt", model_name="gemini-1.5-flash", api_key="test_key_123")
    
    elapsed = time.time() - start_time
    print(f"\n[Result] Final returned text: '{result}'")
    print(f"[Result] Total elapsed time: {elapsed:.2f} seconds (includes QuotaManager Jitter sleeps)")
    
    assert result == "Mock successful response text", "Did not get expected final result"
    assert call_count == 3, "API was not called exactly 3 times"
    print("✓ merge_transcript.py successfully caught 429s, applied QuotaManager backoff, and recovered!")

if __name__ == "__main__":
    test_workflow_helper_wrapper()
    test_merge_transcript_retry_logic()
    print("\n🎉 All sandbox tests passed!")
