# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 5: 前端介面與路由代理 (UI & Router)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 5】。
# 修改儀表板 UI 或顯示邏輯時，絕對必須同步更新 Group 9 (視覺測試機器人) 的截圖 OCR 辨識邏輯。
# 本儀表板讀取的資料來自 Group 1/2，若顯示異常，請勿擅自修改後端資料格式！
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import sys
import json
from google import genai
from quota_manager import QuotaManager
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

