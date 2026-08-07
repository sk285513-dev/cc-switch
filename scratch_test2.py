import google.genai as genai
from google.genai import types
import threading
import sys
import traceback

# 這是重現 Pydantic / SDK 在 Windows Thread 小堆疊的 RecursionError 測試
def test_recursion():
    sys.setrecursionlimit(500) # 模擬小堆疊
    try:
        data = b'0' * (20 * 1024 * 1024)
        part = types.Part.from_bytes(data=data, mime_type="audio/wav")
        client = genai.Client(api_key="fake")
        client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[part, "hello"]
        )
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

t = threading.Thread(target=test_recursion)
t.start()
t.join()
