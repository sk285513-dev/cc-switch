import os
import re
import requests
import json
import time
import mimetypes
from pathlib import Path

# Try importing fallback/diagram utilities
try:
    from PIL import Image
    from pdf2image import convert_from_path
except ImportError:
    Image = None
    convert_from_path = None

try:
    from workflow_helper import get_gemini_key, load_config
except ImportError:
    try:
        from scripts.workflow_helper import get_gemini_key, load_config
    except ImportError:
        def get_gemini_key():
            return os.environ.get("GEMINI_API_KEY", "")
        def load_config():
            return {}

# Gemini upload & processing helper functions
def upload_to_gemini_api(file_path, api_key):
    url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        if file_path.lower().endswith('.pdf'):
            mime_type = "application/pdf"
        elif file_path.lower().endswith('.mp3'):
            mime_type = "audio/mp3"
        elif file_path.lower().endswith('.wav'):
            mime_type = "audio/wav"
        elif file_path.lower().endswith('.mp4'):
            mime_type = "video/mp4"
        elif file_path.lower().endswith('.png'):
            mime_type = "image/png"
        elif file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
            mime_type = "image/jpeg"
        else:
            mime_type = "application/octet-stream"
            
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": mime_type,
        "Content-Type": "application/json"
    }
    
    metadata = {"file": {"displayName": file_name}}
    
    response = requests.post(url, headers=headers, json=metadata)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to initiate resumable upload (HTTP {response.status_code}): {response.text}")
        
    upload_url = response.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise RuntimeError("Missing X-Goog-Upload-URL in response headers")
        
    headers_upload = {
        "X-Goog-Upload-Command": "upload, finalize",
        "X-Goog-Upload-Offset": "0",
        "Content-Length": str(file_size)
    }
    
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        
    response_upload = requests.post(upload_url, headers=headers_upload, data=file_bytes)
    if response_upload.status_code != 200:
        raise RuntimeError(f"Failed to upload bytes (HTTP {response_upload.status_code}): {response_upload.text}")
        
    res_data = response_upload.json()
    file_uri = res_data["file"]["uri"]
    file_name_api = res_data["file"]["name"]
    return file_uri, file_name_api, mime_type

def wait_for_gemini_file(file_name_api, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/{file_name_api}?key={api_key}"
    for _ in range(60): # 10 minutes max
        response = requests.get(url)
        if response.status_code == 200:
            state = response.json().get("file", {}).get("state", "PROCESSING")
            if state == "ACTIVE":
                return True
            elif state == "FAILED":
                raise RuntimeError("Gemini file processing failed")
        time.sleep(10)
    raise TimeoutError("Gemini file processing timed out")

def delete_gemini_file(file_name_api, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/{file_name_api}?key={api_key}"
    try:
        requests.delete(url)
    except:
        pass

def generate_content_with_file(file_uri, mime_type, prompt, api_key, model_name="gemini-2.5-flash"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "file_data": {
                            "mime_type": mime_type,
                            "file_uri": file_uri
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Gemini generation failed: {response.text}")
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except KeyError:
        raise RuntimeError(f"Unexpected response format: {response.json()}")


class MultimodalLegalInput:
    def __init__(self, model_size='small', glossary_path=None, gpu_id=0):
        if glossary_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            glossary_path = str(base_dir / "legal_glossary.json")
        self.glossary_path = glossary_path
        self.glossary = self._load_glossary()
        
    def _load_glossary(self):
        if os.path.exists(self.glossary_path):
            try:
                with open(self.glossary_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "common_errors": {
                "假芳": "甲方", "假方": "甲方",
                "倚芳": "乙方", "倚方": "乙方", "以方": "乙方",
                "炳芳": "丙方", "丙芳": "丙方", "炳方": "丙方",
                "丁芳": "丁方", "形法": "刑法", "形訴": "刑訴"
            }
        }

    def apply_glossary_fix(self, text: str) -> str:
        """第一層：硬性精準規則匹配與天干名詞提換"""
        if not text:
            return ""
        fixed_text = text
        for wrong, right in self.glossary.get("common_errors", {}).items():
            fixed_text = re.sub(wrong, right, fixed_text)
        return fixed_text

    def transcribe_audio(self, file_path, status_callback=None):
        """聽覺：利用雲端 Gemini 多模態模型進行高精度轉錄，相容 VTT/時間軸格式"""
        if status_callback:
            status_callback("☁️ 正在上傳音訊檔案至 Gemini 雲端...")
            
        api_key = get_gemini_key()
        if not api_key:
            return "[ERROR] 未設定 GEMINI_API_KEY 環境變數或 config.yaml 中的金鑰"
            
        try:
            # 1. 上傳檔案至 Gemini Files API
            file_uri, file_name_api, mime_type = upload_to_gemini_api(file_path, api_key)
            
            if status_callback:
                status_callback("☁️ 檔案已上傳，正在等候 Gemini 處理音軌...")
                
            # 2. 等待檔案處理為 ACTIVE
            wait_for_gemini_file(file_name_api, api_key)
            
            if status_callback:
                status_callback("☁️ Gemini 處理完成，正在生成時間軸逐字稿...")
                
            # 3. 呼叫 Gemini 進行轉錄
            model_name = "gemini-2.5-flash"
            try:
                cfg = load_config()
                model_name = cfg.get("api", {}).get("gemini_model_low_cost", "gemini-2.5-flash")
            except:
                pass
                
            prompt = (
                "你是一個精通臺灣法律與繁體中文的專業聽寫速記員。\n"
                "請將此音訊/視訊檔案轉錄為高品質的繁體中文逐字稿，並嚴格遵守以下聽寫規則：\n\n"
                "【重要：完整性與精確性要求】\n"
                "此檔案為極為關鍵的法律教學教材，是後續所有 AI 專案與智能庫的智慧基礎。請務必做到「一字不漏、完全轉錄」！\n"
                "嚴禁任何摘要、縮寫、省略、或簡化發言的行為。請完整保留講師的所有口語說明、舉例與課堂細節。\n\n"
                "1. 語言規範：一律輸出繁體中文（台灣習慣用語，例如「資訊」而非「信息」、「影片」而非「視頻」、「代理人」等）。\n"
                "2. 法律專業術語：精確記錄所有臺灣法律術語（例如：「被告」、「原告」、「不當得利」、「侵權行為」、「時效抗辯」等）。\n"
                "3. 法規條文格式：精確保留所有法律名稱與條號，條號請以中文大寫數字記錄（例如：「民法第一百八十四條」、「行政程序法第九十二條」等）。\n"
                "4. 司法實務字號：精確記錄釋字與裁判/判決字號格式（例如：「釋字第588號」、「最高法院108年度台上字第20號民事判決」等）。\n"
                "5. 時間戳對齊：請在每隔約 30 秒至 1 分鐘或在段落轉換時，於行首插入時間戳記，格式為 `[HH:MM:SS]` 或 `[MM:SS]`。\n"
                "6. 結構化排版：自動在適當位置插入 Markdown 二級或三級標題（例如：## 案例分析：甲對乙提起訴訟）。\n\n"
                "現在，請開始進行語音轉錄，只輸出轉錄後的 Markdown 文本，不要有任何多餘的引言或解釋。"
            )
            
            transcript = generate_content_with_file(file_uri, mime_type, prompt, api_key, model_name)
            
            # 清除雲端檔案
            delete_gemini_file(file_name_api, api_key)
            
            # 套用字詞修正
            transcript_fixed = self.apply_glossary_fix(transcript)
            
            if status_callback:
                status_callback("☁️ 逐字稿生成成功！")
                
            return transcript_fixed
            
        except Exception as e:
            return f"[ERROR] 雲端 Gemini ASR 轉錄失敗: {e}"

    def ocr_document(self, file_path, status_callback=None, page_callback=None):
        """視覺：書狀、照片 PDF 之圖形辨識 (利用 Gemini 雲端多模態模型)"""
        if status_callback:
            status_callback("☁️ 正在上傳文件至 Gemini 雲端進行高精度 OCR...")
            
        api_key = get_gemini_key()
        if not api_key:
            err_msg = "[ERROR] 未設定 GEMINI_API_KEY"
            return [{"page": 1, "text": err_msg}]
            
        try:
            # 1. 上傳檔案至 Gemini Files API
            file_uri, file_name_api, mime_type = upload_to_gemini_api(file_path, api_key)
            
            if status_callback:
                status_callback("☁️ 文件已上傳，正在等候 Gemini 處理...")
                
            # 2. 等待檔案處理為 ACTIVE
            wait_for_gemini_file(file_name_api, api_key)
            
            if status_callback:
                status_callback("☁️ Gemini 處理完成，正在進行高精度 OCR 識別...")
                
            # 3. 呼叫 Gemini 進行 OCR
            model_name = "gemini-2.5-flash"
            try:
                cfg = load_config()
                model_name = cfg.get("api", {}).get("gemini_model_low_cost", "gemini-2.5-flash")
            except:
                pass
                
            prompt = (
                "你是一個高精度的法律文卷 OCR 系統。\n"
                "請對此文件進行 OCR 辨識，提取出每一頁的完整文字內容。\n"
                "請務必遵守以下規範：\n"
                "1. 繁體中文：一律輸出台灣繁體中文法律用語。\n"
                "2. 保持完整：保留原汁原味的段落與文字結構。\n"
                "3. 輸出格式：必須使用 JSON 陣列格式輸出，其中每一個元素包含 \"page\" (整數，頁碼，從 1 開始) 與 \"text\" (該頁辨識出的所有文字內容)。\n"
                "例如：\n"
                "[\n"
                "  {\"page\": 1, \"text\": \"第一頁文字...\"},\n"
                "  {\"page\": 2, \"text\": \"第二頁文字...\"}\n"
                "]\n"
                "只輸出 JSON 陣列內容，不要有任何 Markdown 標記（如 ```json）或引言。"
            )
            
            ocr_result = generate_content_with_file(file_uri, mime_type, prompt, api_key, model_name)
            
            # 清除雲端檔案
            delete_gemini_file(file_name_api, api_key)
            
            # 解析 JSON 內容
            ocr_result_clean = ocr_result.strip()
            if ocr_result_clean.startswith("```"):
                ocr_result_clean = re.sub(r"^```(?:json)?\n", "", ocr_result_clean)
                ocr_result_clean = re.sub(r"\n```$", "", ocr_result_clean)
                ocr_result_clean = ocr_result_clean.strip()
                
            pages = json.loads(ocr_result_clean)
            
            # Apply字詞修正
            for p in pages:
                p["text"] = self.apply_glossary_fix(p["text"])
                
            # Convert PDF/Image to PIL Images if page_callback is requested
            if page_callback and convert_from_path and Image:
                if status_callback:
                    status_callback("🎬 正在載入頁面影像以提取圖表與板書...")
                try:
                    if file_path.lower().endswith('.pdf'):
                        images = convert_from_path(file_path)
                    else:
                        images = [Image.open(file_path)]
                        
                    for p in pages:
                        p_num = p["page"]
                        p_idx = p_num - 1
                        if 0 <= p_idx < len(images):
                            try:
                                page_callback(images[p_idx], p_num)
                            except Exception as cb_err:
                                print(f"[OCR] Page callback error on page {p_num}: {cb_err}")
                except Exception as img_err:
                    print(f"[OCR] Image loading failed: {img_err}")
                    
            if status_callback:
                status_callback("☁️ OCR 辨識與視覺筆記提取完成！")
                
            return pages
            
        except Exception as e:
            err_msg = f"[ERROR] 雲端 Gemini OCR 辨識失敗: {e}"
            print(err_msg)
            return [{"page": 1, "text": err_msg}]

    def post_refine_using_llm(self, text: str) -> str:
        """第二層：法語脈絡重構（利用 Gemini 雲端模型進行校對）"""
        if not text:
            return ""
            
        if text.startswith("[ERROR]") or text.startswith("[WARNING]"):
            return text
            
        api_key = get_gemini_key()
        if not api_key:
            return text
            
        print("[LLM PROOF] Forwarding text to Gemini cloud for proofreading...")
        try:
            model_name = "gemini-2.5-flash"
            try:
                cfg = load_config()
                model_name = cfg.get("api", {}).get("gemini_model_low_cost", "gemini-2.5-flash")
            except:
                pass
                
            prompt = (
                "你是一位在台灣法律實務界見習的高材生，精通繁體中文與台灣司法常用代稱與法條格式。\n"
                "以下是一段由語音識別（ASR）或圖片辨識（OCR）生成的法律教學文本草稿。\n"
                "此文本是極為重要的法律基礎教材，必須保證其「絕對完整與一字不漏」！\n"
                "請在【不改變原話意圖、不進行任何縮減、不刪減任何講師的口語解釋、細節與範例】的絕對前提下，"
                "將其校對為符合台灣實務用語的精準文字。\n"
                "請專注於修正錯別字（例如「假芳」修正為「甲方」）與調整法學排版，嚴禁重寫或概括原文內容！\n"
                "並維持任何已有的時間軸。[時間軸格式必須保留，不要刪除時間戳記]。\n\n"
                f"待校對文本：\n{text}"
            )
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            res = requests.post(url, json=payload, timeout=120)
            if res.status_code == 200:
                content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                if content:
                    return content.strip()
            return text
        except Exception as e:
            print(f"[LLM PROOF] Gemini refinement failed: {e}, returning original text")
            return text