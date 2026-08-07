# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 5: 前端介面與路由代理 (UI & Router)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 5】。
# 修改儀表板 UI 或顯示邏輯時，絕對必須同步更新 Group 9 (視覺測試機器人) 的截圖 OCR 辨識邏輯。
# 本儀表板讀取的資料來自 Group 1/2，若顯示異常，請勿擅自修改後端資料格式！
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
# -*- coding: utf-8 -*-
import sys
import io
import json
import logging
import requests
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "deepseek-r1:32b"

class OllamaRouter:
    """
    Ollama 本地端模型路由代理。
    負責與本地的 Ollama 服務溝通，提供流暢的生成介面。
    """
    def __init__(self, base_url: str = OLLAMA_URL, default_model: str = DEFAULT_MODEL):
        self.base_url = base_url
        self.default_model = default_model

    def generate_chat(self, prompt: str, system_prompt: str = "", model: str = None, stream: bool = False) -> str:
        """
        呼叫 Ollama Chat API
        """
        target_model = model or self.default_model
        
        # 【修復 Issue 15 & 17】加入 Flagging 機制，若問題過長或包含高度複雜的法律詞彙，自動 Fallback 給雲端 Gemini Pro API
        complexity_keywords = ["釋字", "憲判字", "最高法院", "判例", "爭點"]
        is_complex = len(prompt) > 1500 or sum(1 for k in complexity_keywords if k in prompt) >= 2
        
        if is_complex:
            logger.info("[OllamaRouter] 偵測到高複雜度法理問題 (長度或關鍵字達標)，觸發 Fallback 機制交由雲端 API 處理...")
            import subprocess
            import json
            try:
                # 組合 contents (將 system_prompt 與 prompt 合併)
                combined = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                contents_json = json.dumps([combined])
                # 呼叫 gemini_proxy.py
                script_path = os.path.join(os.path.dirname(__file__), "gemini_proxy.py")
                # 預設呼叫 gemini-2.5-pro 處理複雜邏輯，且為非測試流量 (0)
                result = subprocess.run([sys.executable, script_path, "gemini-2.5-pro", contents_json, "0"], capture_output=True, text=True, check=True, encoding="utf-8")
                return result.stdout.strip()
            except Exception as e:
                logger.warning(f"[OllamaRouter] 雲端 Fallback 失敗，退回本地模型: {e}")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": stream
        }
        
        try:
            if stream:
                response = requests.post(self.base_url, json=payload, stream=True, timeout=120)
                response.raise_for_status()
                
                full_response = ""
                print(f"[{target_model}] 思考中...", end="\n", flush=True)
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        if "message" in chunk and "content" in chunk["message"]:
                            content = chunk["message"]["content"]
                            print(content, end="", flush=True)
                            full_response += content
                print("\n")
                return full_response
            else:
                response = requests.post(self.base_url, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[OllamaRouter] 連線失敗: {e}")
            raise RuntimeError(f"Ollama 連線錯誤: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    router = OllamaRouter()
    
    print("=== Ollama Router 連線測試 ===")
    try:
        ans = router.generate_chat("請用繁體中文解釋什麼是『比例原則』，簡短回答即可。", model="deepseek-r1:7b", stream=True)
        print("\n=== 測試成功 ===")
    except Exception as e:
        print(f"\n=== 測試失敗: {e} ===")

