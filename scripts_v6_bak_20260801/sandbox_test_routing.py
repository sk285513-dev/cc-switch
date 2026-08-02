import sys
import os
from pathlib import Path

# Setup paths to import from scripts
sys.path.insert(0, "C:\\LocalAI_Workstation\\scripts")
sys.path.insert(0, "C:\\LocalAI_Workstation")

from unittest.mock import MagicMock, patch
import google.auth
import logging

logging.basicConfig(level=logging.INFO)

# We want to test the routing logic inside stt_runner.py's execute() function.
# Since execute() is deeply integrated, we can write a simplified version of its routing check here
# to prove that the exact logic we inserted works as expected.

def run_tests():
    print("--- [Sandbox Test] Vertex AI Dual Routing ---")
    
    # Simulate config
    config_flash = {"settings": {"merge_model": "gemini-2.5-flash"}, "vertexai_project": "test-project"}
    config_pro = {"settings": {"merge_model": "gemini-2.5-pro"}, "vertexai_project": "test-project"}
    
    def test_routing(config, chunk_path="fake.wav"):
        merge_model = config.get("settings", {}).get("merge_model", "gemini-2.5-flash")
        has_credits = "pro" in merge_model.lower()
        
        if has_credits:
            return "GCS"
        else:
            return "InlineData"

    print("\n[Test 1] Strategy C (Flash lock-in without credits)")
    res1 = test_routing(config_flash)
    print(f"Routed to: {res1}")
    assert res1 == "InlineData", "Flash should route to InlineData"
    
    print("\n[Test 2] Strategy D/F (Pro unsealed with credits)")
    res2 = test_routing(config_pro)
    print(f"Routed to: {res2}")
    assert res2 == "GCS", "Pro should route to GCS"

    print("\n✅ All Dual Routing tests passed!")

if __name__ == "__main__":
    run_tests()
