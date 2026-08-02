import urllib.request, json, time
body = b'''{"model":"deepseek-r1:7b","messages":[{"role":"system","content":"Taiwan law AI, Traditional Chinese, concise"},{"role":"user","content":"民法第197條時效起算點？"}],"stream":false,"options":{"temperature":0.1}}'''
req = urllib.request.Request("http://127.0.0.1:11434/api/chat",data=body,headers={"Content-Type":"application/json"},method="POST")
t=time.time()
with urllib.request.urlopen(req,timeout=60) as r:
    d=json.loads(r.read())
    print(f"TIME={time.time()-t:.1f}s done={d.get('done_reason')}")
    print(f"CONTENT={repr(d['message']['content'][:400])}")
    print(f"THINKING={repr(d['message'].get('thinking','')[:200])}")
