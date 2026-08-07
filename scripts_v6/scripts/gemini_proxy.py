import sys
import json
from google import genai
from scripts.quota_manager import QuotaManager
from google.genai import types

def main():
    if len(sys.argv) < 4:
        print("Usage: python gemini_proxy.py <model> <contents_json> <is_test_traffic_flag>")
        sys.exit(1)
        
    model = sys.argv[1]
    contents = json.loads(sys.argv[2])
    is_test_traffic = sys.argv[3] == '1'
    
    # 透過 QuotaManager 取得金鑰，落實 QoS 與 429 退避
    qm = QuotaManager(is_test_traffic=is_test_traffic)
    api_key = qm.acquire_key_exclusive()
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Format contents properly for the new SDK
        formatted_contents = []
        for content in contents:
            if isinstance(content, str):
                formatted_contents.append(content)
            elif isinstance(content, dict) and "parts" in content:
                # Basic parsing for typical gemini input structure
                formatted_contents.append(content["parts"][0]["text"])
                
        # Call model
        response = client.models.generate_content(
            model=model,
            contents=formatted_contents
        )
        print(response.text)
    finally:
        qm.release_key_exclusive(api_key)

if __name__ == "__main__":
    main()
