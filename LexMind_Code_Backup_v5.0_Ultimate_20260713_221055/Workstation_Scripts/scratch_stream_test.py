import urllib.request
import json
import sys

url = 'http://127.0.0.1:11434/api/chat'
payload = {
    "model": "ornith:9b-bf16",
    "messages": [
        {"role": "system", "content": "你是一位專業的台灣律師。"},
        {"role": "user", "content": "甲將其所有之A地借名登記於乙名下，乙未經甲同意，擅自將A地以買賣為由移轉登記並交付予知情之丙。請問甲可否向丙請求返還A地？請附上實務見解。"}
    ],
    "stream": True
}

req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
try:
    with urllib.request.urlopen(req, timeout=300) as response:
        print("=== Streaming Response from ornith:9b-bf16 ===")
        for line in response:
            if line:
                data = json.loads(line.decode('utf-8'))
                msg = data.get("message", {})
                content = msg.get("content", "")
                if content:
                    print(content, end="", flush=True)
                
                # Check for any error
                if "error" in data:
                    print(f"\nError: {data['error']}")
                    break
        print("\n=== Done ===")
except Exception as e:
    print(f"Error: {e}")
