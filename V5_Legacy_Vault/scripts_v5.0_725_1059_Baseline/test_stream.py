import urllib.request, json, time, sys

body = json.dumps({
    "model": "ornith:9b-bf16",
    "messages": [
        {"role": "system", "content": "You are a Taiwan law AI assistant. Answer in Traditional Chinese. Be concise."},
        {"role": "user",   "content": "請問民法第197條侵權行為損害賠償請求權時效，起算點是什麼時候開始計算？"}
    ],
    "stream": True,
    "options": {"temperature": 0.1}
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST"
)

t = time.time()
print("開始串流接收...")
tokens = 0
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            if line:
                d = json.loads(line)
                tokens += 1
                if tokens % 50 == 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                if d.get("done"):
                    print(f"\n完成! 總計耗時: {time.time()-t:.1f}s | 總 token: {tokens}")
                    break
except Exception as e:
    print(f"\nERROR={e} after {time.time()-t:.1f}s")
