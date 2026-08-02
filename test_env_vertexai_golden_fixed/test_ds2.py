import urllib.request, json, time

body = json.dumps({
    "model": "deepseek-r1:7b",
    "messages": [
        {"role": "system", "content": "Taiwan law AI. Answer in Traditional Chinese. Be very brief."},
        {"role": "user",   "content": "Civil Code Article 197 limitation period start point?"}
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
        print(f"TIME={time.time()-t:.1f}s done={d.get('done_reason')}")
        print(f"CONTENT={repr(d['message']['content'][:500])}")
        print(f"THINKING={repr(d['message'].get('thinking','')[:200])}")
except Exception as e:
    print(f"ERROR={e} after {time.time()-t:.1f}s")
