import urllib.request, json, time

body = json.dumps({
    "model": "deepseek-r1:7b",
    "messages": [
        {"role": "system", "content": "You are a Taiwan law AI assistant. Always reply in Traditional Chinese (Mandarin). Be precise and use proper Taiwan legal terminology."},
        {"role": "user",   "content": "請問民法第197條侵權行為損害賠償請求權的時效，起算點是什麼時候開始計算？請依照台灣最高法院實務見解回答。"}
    ],
    "stream": False,
    "options": {"temperature": 0.1}
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST"
)
t = time.time()
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
        elapsed = time.time()-t
        print(f"TIME={elapsed:.1f}s | done={d.get('done_reason')} | tokens={d.get('eval_count')}")
        print(f"\n=== CONTENT ===")
        print(d["message"]["content"])
except Exception as e:
    print(f"ERROR={e} after {time.time()-t:.1f}s")
