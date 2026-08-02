import requests
import time

url = 'http://localhost:8507'
for _ in range(5):
    try:
        response = requests.get(url)
        print("Status code:", response.status_code)
        print(response.text[:500])
        break
    except Exception as e:
        print(e)
        time.sleep(2)
