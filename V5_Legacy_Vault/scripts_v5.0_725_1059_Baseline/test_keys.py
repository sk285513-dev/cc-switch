import yaml
import requests
import sys
from datetime import datetime, timezone

def verify_keys():
    try:
        with open("config/keys.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error reading keys.yaml: {e}")
        return

    raw_keys = data.get("keys", [])
    if not raw_keys:
        print("No keys found in keys.yaml.")
        return

    # Ensure SSOT dict structure
    for i, k in enumerate(raw_keys):
        if isinstance(k, str):
            raw_keys[i] = {"value": k, "status": "active"}
        elif isinstance(k, dict) and "status" not in k:
            raw_keys[i]["status"] = "active"

    valid_count = 0
    dead_count = 0
    exhausted_count = 0

    print(f"Testing {len(raw_keys)} keys (SSOT Mode)...")
    for k_obj in raw_keys:
        key = k_obj.get("value")
        if not key: continue

        # Skip testing if it's already marked dead to save time, unless user forces a re-check
        # We will test all active/exhausted keys.
        if k_obj.get("status") == "dead":
            dead_count += 1
            continue

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
        payload = {"contents": [{"parts": [{"text": "hi"}]}]}
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                k_obj["status"] = "active"
                k_obj["notes"] = "OK"
                valid_count += 1
            elif res.status_code == 429:
                k_obj["status"] = "exhausted"
                k_obj["notes"] = "HTTP 429 Quota Exceeded"
                exhausted_count += 1
            elif res.status_code in (401, 403, 400, 404):
                k_obj["status"] = "dead"
                k_obj["notes"] = f"HTTP {res.status_code} Error"
                dead_count += 1
            else:
                # 503 or others, keep as active but note it
                k_obj["status"] = "active"
                k_obj["notes"] = f"HTTP {res.status_code} Transient"
                valid_count += 1
        except Exception as e:
            print(f"Error testing key {key[:8]}: {e}")
            k_obj["status"] = "dead"
            k_obj["notes"] = str(e)
            dead_count += 1
            
        k_obj["last_checked"] = datetime.now(timezone.utc).isoformat()

    print(f"Result: {valid_count} active, {exhausted_count} exhausted, {dead_count} dead.")
    
    # Write back without deleting any keys
    data["keys"] = raw_keys
    with open("config/keys.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    print("SSOT config/keys.yaml updated. No keys were deleted.")

if __name__ == "__main__":
    verify_keys()
