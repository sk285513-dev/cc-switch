import google.genai as genai
from google.genai import types
import threading
import sys
import traceback

def test():
    try:
        data = b'0' * (2000 * 1024)  # 2MB
        part = types.Part.from_bytes(data=data, mime_type="audio/wav")
        client = genai.Client(api_key="fake")
        client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[part, "hello"]
        )
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()

def run_in_thread():
    t = threading.Thread(target=test)
    t.start()
    t.join()

run_in_thread()
