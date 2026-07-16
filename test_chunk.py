import sys, glob, os, yaml, json, time, traceback
sys.path.insert(0, r'C:\LocalAI_Workstation\scripts')

from workflow_helper import load_config
cfg = load_config()

# 找一個 pending chunk
pending_chunk = None
for f in glob.glob('A:/manifests/task_*_chunks.json'):
    try:
        ch = json.load(open(f, encoding='utf-8'))
        if not isinstance(ch, list): continue
        for c in ch:
            if c.get('status') in ('pending','failed') and c.get('retry_count',99) < 3:
                wav = c.get('path','')
                if wav and os.path.exists(wav):
                    pending_chunk = c
                    break
        if pending_chunk: break
    except: pass

if not pending_chunk:
    print('找不到 pending chunk')
    sys.exit()

print('Chunk:', pending_chunk['filename'])
print('WAV  :', pending_chunk['path'])

from quota_manager import QuotaManager
qm = QuotaManager()
try:
    key = qm.acquire_key_exclusive()
    print('Key  :', key[:12], '...')
except RuntimeError as e:
    print('NO KEY:', e)
    sys.exit()

import google.genai as genai
client = genai.Client(api_key=key)

print('Uploading...')
uf = client.files.upload(file=pending_chunk['path'])
print('Uploaded:', uf.name)

try:
    from stt_runner import transcribe_chunk
    print('Calling transcribe_chunk()...')
    result = transcribe_chunk(client, uf, cfg, qm=qm, api_key=key)
    print('OK:', str(result)[:120])
except Exception as e:
    print('FAIL:')
    traceback.print_exc()
finally:
    try: client.files.delete(name=uf.name)
    except: pass
    qm.release_key(key)
