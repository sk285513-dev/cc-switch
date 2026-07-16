import urllib.request
import json

url = 'http://127.0.0.1:11434/api/chat'
payload = {
    "model": "ornith:9b-bf16",
    "messages": [
        {"role": "system", "content": "你是一位專業的台灣律師。請根據台灣現行法規與最高法院實務見解回答問題。"},
        {"role": "user", "content": "甲將其所有之A地借名登記於乙名下，乙未經甲同意，擅自將A地以買賣為由移轉登記並交付予知情之丙。請問甲可否向丙請求返還A地？請附上實務見解。"}
    ],
    "stream": False
}

req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
try:
    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        # 提取 thinking (如果有)
        thinking = data.get("message", {}).get("thinking", "")
        content = data.get("message", {}).get("content", "")
        
        print("=== Local Model (ornith:9b-bf16) Thinking ===")
        print(thinking)
        print("\n=== Local Model (ornith:9b-bf16) Answer ===")
        print(content)
except Exception as e:
    print(f"Error: {e}")
