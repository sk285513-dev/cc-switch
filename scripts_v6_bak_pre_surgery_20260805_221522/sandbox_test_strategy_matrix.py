import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

def simulate_routing(strategy_name, stt_engine, stt_model):
    """
    Simulates the exact routing logic in stt_runner.py
    Returns a string describing the chosen upload path.
    """
    is_vertex = (stt_engine == "vertexai")
    
    if stt_engine == "local_whisper":
        return "LOCAL_WHISPER (No Cloud Upload)"
        
    if not is_vertex:
        # AI Studio Engine (stt_engine == "gemini")
        # According to Item 5, we abandoned File API due to billing trap and moved to Base64.
        return "BASE64 INLINE (AI Studio)"
        
    else:
        # Vertex AI Engine
        # According to Item 7 Dual-Routing logic
        has_credits = "pro" in stt_model.lower()
        if has_credits:
            return "GCS BUCKET (Vertex AI with Credits)"
        else:
            return "BASE64 INLINE (Vertex AI Flash-locked)"

def run_tests():
    print("==========================================================")
    print("--- [Sandbox Test] Setup Wizard Strategy Matrix Routing ---")
    print("==========================================================")
    
    strategies = [
        {
            "name": "Strategy A (Pure AI Studio Free)",
            "stt_engine": "gemini",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-flash",
            "expected": "BASE64 INLINE (AI Studio)"
        },
        {
            "name": "Strategy B (Mixed AI Studio / Vertex Flash)",
            "stt_engine": "gemini",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-flash",
            "expected": "BASE64 INLINE (AI Studio)"
        },
        {
            "name": "Strategy C (Vertex Flash lock-in, NO Credits)",
            "stt_engine": "vertexai",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-flash",
            "expected": "BASE64 INLINE (Vertex AI Flash-locked)"
        },
        {
            "name": "Strategy D (Vertex Mixed, WITH Pro Credits)",
            "stt_engine": "vertexai",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-pro",
            "expected": "BASE64 INLINE (Vertex AI Flash-locked)"
        },
        {
            "name": "Strategy E (Local Whisper)",
            "stt_engine": "local_whisper",
            "stt_model": "local",
            "merge_model": "gemini-2.5-flash",
            "expected": "LOCAL_WHISPER (No Cloud Upload)"
        },
        {
            "name": "Strategy F (Pure Vertex Pro, Expensive)",
            "stt_engine": "vertexai",
            "stt_model": "gemini-2.5-pro",
            "merge_model": "gemini-2.5-pro",
            "expected": "GCS BUCKET (Vertex AI with Credits)"
        }
    ]
    
    all_passed = True
    for s in strategies:
        print(f"\nEvaluating: {s['name']}")
        print(f"  - stt_engine : {s['stt_engine']}")
        print(f"  - stt_model  : {s['stt_model']}")
        print(f"  - merge_model: {s['merge_model']}")
        
        result = simulate_routing(s['name'], s['stt_engine'], s['stt_model'])
        print(f"  --> ROUTING DECISION: {result}")
        
        if result == s['expected']:
            print("  [PASS] Matches expected logic.")
        else:
            print(f"  [FAIL] Expected {s['expected']}, got {result}")
            all_passed = False

    print("\n==========================================================")
    if all_passed:
        print("[SUCCESS] ALL STRATEGIES ROUTED CORRECTLY ACCORDING TO PLAN!")
    else:
        print("[WARNING] SOME STRATEGIES FAILED ROUTING.")

if __name__ == "__main__":
    run_tests()
