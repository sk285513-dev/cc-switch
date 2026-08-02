import urllib.request, json, sys, time

body = json.dumps({
    "model": "ornith:9b-bf16",
    "messages": [
        {"role": "system", "content": "You are a Taiwan law AI. Answer in Traditional Chinese. Be concise."},
        {"role": "user",   "content": "民法第197條的侵權行為損害賠償請求權時效起算點為何？"}
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

start = time.time()
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
        elapsed = time.time() - start
        data = json.loads(raw)
        content  = data.get("message", {}).get("content", "")
        thinking = data.get("message", {}).get("thinking", "")
        done_reason = data.get("done_reason", "")
        print(f"[TIME] {elapsed:.1f}s | done_reason={done_reason}")
        print(f"[CONTENT] {repr(content[:300])}")
        print(f"[THINKING first 300] {repr(thinking[:300])}")
except Exception as e:
    print(f"[ERROR] {e}")
