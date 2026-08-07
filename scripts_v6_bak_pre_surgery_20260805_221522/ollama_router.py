# -*- coding: utf-8 -*-
import json
import sys
import io
import json
import logging
import requests
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8-sig', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8-sig', errors='replace')

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DEFAULT_MODEL = "deepseek-r1:7b"

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
                response = requests.post(self.base_url, json=payload, stream=True, timeout=None)
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
                response = requests.post(self.base_url, json=payload, timeout=None)
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

