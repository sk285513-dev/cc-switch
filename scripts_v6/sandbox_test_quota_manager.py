import sys
import os
from pathlib import Path

# Setup paths to import from scripts
sys.path.insert(0, "C:\\LocalAI_Workstation\\scripts")
sys.path.insert(0, "C:\\LocalAI_Workstation")

from quota_manager import QuotaManager
import google.api_core.exceptions as google_exceptions
from unittest.mock import MagicMock
import logging

logging.basicConfig(level=logging.INFO)

def run_tests():
    print("--- [Sandbox Test] QuotaManager Error Handling ---")
    
    # Mock load_keys to avoid FileNotFoundError / ValueError in test environment
    QuotaManager._load_keys = MagicMock()
    QuotaManager._load_state = MagicMock()
    
    qm = QuotaManager(
        keys_path="config/keys.yaml",
        policy_path="config/quota_policy.yaml",
        state_path="config/quota_state.json"
    )
    
    current_key = "AQ.test_key_123"
    
    print("\n[Test 1] Real ResourceExhausted (429) Exception")
    e_429 = google_exceptions.ResourceExhausted("Real 429 Quota Exceeded")
    res1 = qm.handle_error(e_429, current_key, consecutive_429=1)
    print(f"Result (sleep_time): {res1.get('sleep_time')}")
    assert res1.get('sleep_time') > 0, "429 should cause sleep time > 0"
    
    print("\n[Test 2] Real ServiceUnavailable (503) Exception")
    e_503 = google_exceptions.ServiceUnavailable("Service overloaded")
    res2 = qm.handle_error(e_503, current_key, consecutive_429=0)
    print(f"Result (sleep_time): {res2.get('sleep_time')}")
    assert res2.get('sleep_time') >= 30, "503 should cause mandatory 30+ seconds sleep"

    print("\n[Test 3] Fake 429 String Injection (e.g. filename is 429_quota.wav)")
    # This is a normal ValueError with "429" in the string.
    # Previously, this would trigger a 429 block. Now, it should NOT trigger a 429 sleep.
    e_fake_429 = ValueError("Cannot process file 429_quota.wav")
    res3 = qm.handle_error(e_fake_429, current_key, consecutive_429=0)
    print(f"Result (sleep_time): {res3.get('sleep_time')}")
    assert res3.get('sleep_time') == 0, "String injection should not cause 429 sleep"

    print("\n[Test 4] Real Unauthorized (401) Exception")
    e_401 = google_exceptions.Unauthorized("API key invalid")
    qm.mark_exhausted = MagicMock()
    qm.release_key = MagicMock()
    qm.acquire_key_exclusive = MagicMock(return_value="AQ.new_key_456")
    res4 = qm.handle_error(e_401, current_key, consecutive_429=0)
    print(f"Result (new_key): {res4.get('new_key')}")
    assert qm.mark_exhausted.called, "401 should trigger mark_exhausted"
    
    print("\n✅ All QuotaManager tests passed!")
    
if __name__ == "__main__":
    run_tests()
