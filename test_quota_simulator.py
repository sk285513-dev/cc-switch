import sys
import time
sys.path.append('scripts')
from quota_manager import QuotaManager

def simulate_retry_loop():
    print("=== Simulating merge_transcript.py API Retry Loop ===")
    qm = QuotaManager()
    api_key = "MOCK_KEY_123"
    
    # We simulate 3 attempts. First 2 fail with 429, 3rd succeeds.
    attempt = 0
    consecutive_429 = 0
    
    while attempt < 3:
        try:
            # Simulate qm.throttle_key
            print(f"\n[Attempt {attempt+1}] Checking RPM limits...")
            qm.throttle_key(api_key)
            
            # Simulate the request
            print(f"[Attempt {attempt+1}] Sending API Request via requests.post...")
            
            if attempt < 2:
                # Simulate a 429 error from the API
                print(f"[Attempt {attempt+1}] Simulated HTTP 429 received from Google API!")
                raise Exception("429 Too Many Requests: Quota Exceeded")
            else:
                print(f"[Attempt {attempt+1}] Simulated HTTP 200 Success!")
                return "Model returned: Successfully processed transcript"
                
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str:
                consecutive_429 += 1
                print(f"[Attempt {attempt+1}] Caught 429 error. Invoking QuotaManager.handle_error()...")
                res = qm.handle_error(e, api_key, consecutive_429)
                sleep_time = res["sleep_time"]
                
                print(f"-> QuotaManager suggested Jitter backoff. Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
                
                if res["new_key"] and res["new_key"] != api_key:
                    print(f"-> QuotaManager rotated key! Old: {api_key}, New: {res['new_key']}")
                    api_key = res["new_key"]
            else:
                print("Unknown error, sleep 5s")
                time.sleep(5)
                
        attempt += 1

    raise RuntimeError("Failed after 3 attempts")

if __name__ == "__main__":
    result = simulate_retry_loop()
    print("\n✅ Simulation Complete!")
    print(f"Final Result: {result}")
