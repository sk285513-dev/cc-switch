import urllib.request
import json
try:
    req = urllib.request.Request(
        "http://127.0.0.1:3000/api/eval-local",
        data=json.dumps({"question": "甲將A地借名登記..."}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    urllib.request.urlopen(req)
except Exception as e:
    if hasattr(e, 'read'):
        print(e.read().decode())
    else:
        print(e)
