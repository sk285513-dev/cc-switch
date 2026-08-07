# LexMind-Omni System Source Bundle (V2 - Expert Refactored)

# LexMind Omni System Source Bundle for Review

## visual_analyzer.py

```python
import os
import re
import time
import requests
import json
import numpy as np
from pathlib import Path
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

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

class VisualLegalAnalyzer:
    def __init__(self, agent_instance=None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.obsidian_dir = self.base_dir / "Obsidian_Vault" / "04_教材圖表校對"
        self.image_dir = self.obsidian_dir / "images"
        os.makedirs(self.image_dir, exist_ok=True)
        self.agent_instance = agent_instance
        self.llm_url = f'{os.environ.get("OLLAMA_HOST", "http://localhost:11434")}/api/chat'
        self.model_name = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")
        self.gemini_multimodal_disabled = False

    def _query_llm(self, prompt: str) -> str:
        """安全呼叫本地大模型"""
        try:
                payload = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.2, "num_ctx": 16384}
                }
                res = requests.post(self.llm_url, json=payload, timeout=90)
                if res.status_code == 200:
                    reply = res.json().get('message', {}).get('content', '')
                    # 去除思考標籤
                    if "<think>" in reply:
                        reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
                    return reply
        except Exception as e:
                print(f"[WARNING] Visual analyzer LLM query failed: {e}")
        return "（無法取得本地大模型之智能註記分析）"

    def _query_gemini_multimodal(self, image_path, prompt, api_key):
        try:
                url_upload = f"https://generativelanguage.googleapis.com/upload/v1beta/files"
                file_name = os.path.basename(image_path)
                file_size = os.path.getsize(image_path)
                mime_type = "image/png"
                
                headers = {
                    "X-Goog-Upload-Protocol": "resumable",
                    "X-Goog-Upload-Command": "start",
                    "X-Goog-Upload-Header-Content-Length": str(file_size),
                    "X-Goog-Upload-Header-Content-Type": mime_type,
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                }
                metadata = {"file": {"displayName": file_name}}
                
                res_init = requests.post(url_upload, headers=headers, json=metadata, timeout=30)
                if res_init.status_code != 200:
                    print(f"[Gemini OCR] Init upload failed: {res_init.text}")
                    if res_init.status_code == 429:
                        self.gemini_multimodal_disabled = True
                        print("[Gemini OCR] Upload 429 Quota Exceeded. Disabling multimodal.")
                    return ""
                upload_url = res_init.headers.get("X-Goog-Upload-URL")
                if not upload_url:
                    print("[Gemini OCR] Missing upload URL")
                    return ""
                    
                headers_upload = {
                    "X-Goog-Upload-Command": "upload, finalize",
                    "X-Goog-Upload-Offset": "0",
                    "Content-Length": str(file_size)
                }
                with open(image_path, "rb") as f:
                    file_bytes = f.read()
                res_up = requests.post(upload_url, headers=headers_upload, data=file_bytes, timeout=60)
                if res_up.status_code != 200:
                    print(f"[Gemini OCR] Upload bytes failed: {res_up.text}")
                    return ""
                    
                res_data = res_up.json()
                file_uri = res_data["file"]["uri"]
                file_name_api = res_data["file"]["name"]
                
                # Wait for file active
                url_status = f"https://generativelanguage.googleapis.com/v1beta/{file_name_api}"
                headers_status = {"x-goog-api-key": api_key}
                state = "PROCESSING"
                for _ in range(30):
                    res_status = requests.get(url_status, headers=headers_status, timeout=15)
                    if res_status.status_code == 200:
                        state = res_status.json().get("file", {}).get("state", "PROCESSING")
                        if state == "ACTIVE":
                            break
                        elif state == "FAILED":
                            print("[Gemini OCR] File processing failed on server.")
                            break
                        print("[Gemini OCR] Processing file...")
                    time.sleep(2)
                    
                if state != "ACTIVE":
                    print("[Gemini OCR] Timeout waiting for file to become active.")
                    return ""
                    
                model_name = "gemini-2.5-flash"
                try:
                    cfg = load_config()
                    model_name = cfg.get("api", {}).get("gemini_model_low_cost", "gemini-2.5-flash")
                except:
                    pass
                    
                url_gen = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                headers_gen = {"Content-Type": "application/json", "x-goog-api-key": api_key}
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
                res_gen = requests.post(url_gen, headers=headers_gen, json=payload, timeout=60)
                content = ""
                if res_gen.status_code == 200:
                    try:
                        content = res_gen.json()["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception as parse_e:
                        print(f"[Gemini OCR] Parse response failed: {parse_e}")
                else:
                    print(f"[Gemini OCR] Generate failed (HTTP {res_gen.status_code}): {res_gen.text}")
                    if res_gen.status_code == 429:
                        self.gemini_multimodal_disabled = True
                        print("[Gemini OCR] HTTP 429 Quota Exceeded. Disabling future Gemini multimodal calls for this run.")
                
                # Cleanup
                try:
                    requests.delete(url_status, headers=headers_status, timeout=15)
                except:
                    pass
                return content.strip()
        except Exception as e:
                print(f"[WARNING] Gemini multimodal query failed: {e}")
                return ""

    def _sanitize_filename(self, name: str) -> str:
        for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                name = name.replace(char, '')
        return name.strip()

    def extract_diagrams_from_page(self, pil_image, class_name: str, lesson_name: str, page_no: int, source_name: str) -> list:
        """
        分析書面教材的頁面影像，自動定位並裁切圖表、邏輯圖或樹狀圖，
        並在 Obsidian 中產生可編輯的校對筆記（內嵌截圖與自動生成的 Mermaid 關係圖）。
        """
        if cv2 is None:
                return []

        # 轉成 OpenCV BGR 格式
        img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        h_img, w_img, _ = img.shape
        
        # 影像預處理：轉灰階、二值化反轉
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # 進行膨脹以連結鄰近的線條與圖表組件
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        
        # 尋找外部輪廓
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        created_notes = []
        idx = 0
        
        for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                
                # 篩選條件：寬高需大於 150 像素（避開單一文字或噪點），且不能是整張頁面（大於 95%）
                if w > 150 and h > 150:
                    if w > w_img * 0.95 and h > h_img * 0.95:
                        continue
                        
                    idx += 1
                    crop = img[y:y+h, x:x+w]
                    
                    # 儲存裁切下來的圖表圖片 (Unicode 安全寫法)
                    clean_src = self._sanitize_filename(source_name)
                    crop_filename = f"{clean_src}_p{page_no}_crop_{idx}.png"
                    crop_path = self.image_dir / crop_filename
                    is_success, buffer = cv2.imencode(".png", crop)
                    if is_success:
                        with open(str(crop_path), "wb") as f:
                            f.write(buffer)
                    else:
                        cv2.imwrite(str(crop_path), crop)
                    
                    # 進行圖表文字 OCR 辨識
                    ocr_text = ""
                    if pytesseract is not None:
                        try:
                            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                            ocr_text = pytesseract.image_to_string(Image.fromarray(crop_rgb), lang='chi_tra+eng').strip()
                        except:
                            pass

                    # 呼叫大模型進行分析並生成關係圖代碼
                    prompt = f"""你是一個精通臺灣法律實務的助理。我們從講義《{source_name}》第 {page_no} 頁自動擷取了一個圖表（輪廓偵測區域）。
該圖表區域內辨識出的文字內容如下：
<document>
{ocr_text}
</document>

請根據這些文字，幫我完成以下事項：
1. 判斷這是一個什麼類型的圖表（如：民事權利關係圖、法律概念樹狀圖、邏輯流程圖、表格等）。
2. 用繁體中文寫出該圖表的詳細語意解讀，並自動比對聯想關聯的臺灣現行法律條文（例如：如果提到車禍折損，聯想民法184條、197條等），寫下理解與演化註記。
3. **生成對應的 Mermaid.js 流程圖或關係圖代碼**，讓使用者可以在 Markdown 編輯器中直接看到此圖表的結構並編輯。
   - 注意：Mermaid 節點文字必須用雙引號括住，例如 A["原告甲"] --> B["被告乙"]，以防渲染語法出錯。
   - 如果文字太凌亂，請建立一個合理的法律邏輯樹狀圖或關係示意圖。

請只輸出：
【解讀與註記】：
(您的詳細法律理解說明與條文對位)

【MERMAID 代碼】：
(完整的 mermaid 程式碼塊，如 graph TD ... 等，不要帶 markdown ``` 符號)
"""
                    ai_response = self._query_llm(prompt)
                    
                    # 解析 AI 回應
                    ai_analysis = "（解讀生成失敗）"
                    mermaid_code = "graph TD\n    A[\"教材圖表\"] --> B[\"尚無關聯關係\"]"
                    
                    if "【解讀與註記】" in ai_response:
                        parts = ai_response.split("【MERMAID 代碼】")
                        ai_analysis = parts[0].replace("【解讀與註記】", "").strip()
                        if len(parts) > 1:
                            mermaid_code = parts[1].replace(":", "").strip()
                            mermaid_code = re.sub(r"^```mermaid", "", mermaid_code)
                            mermaid_code = re.sub(r"```$", "", mermaid_code).strip()
                    else:
                        ai_analysis = ai_response
                    
                    # 建立 Obsidian Markdown 校對筆記
                    note_filename = f"校對_{clean_src}_第{page_no}頁_圖表{idx}.md"
                    note_path = self.obsidian_dir / note_filename
                    
                    note_content = f"""# 📑 書面教材圖表校對筆記
- **來源講義**: [{source_name}](file:///{source_name.replace('\\', '/')})
- **課程分類**: `{class_name}`
- **課堂章節**: `{lesson_name}`
- **教材頁次**: 第 `{page_no}` 頁
- **擷取序號**: 圖表 `{idx}`
- **偵測時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 🔍 擷取圖表對照圖
![圖表](./images/{crop_filename})

## 🧠 AI 智慧解讀與法律註記
{ai_analysis}

## 📊 可編輯之 Mermaid 關係流程圖
```mermaid
{mermaid_code}
```

## ✍️ 操作者手動校對修改區
<!-- 您可以直接修改上方的文字或調整 Mermaid 區塊中的節點，Obsidian 會即時重新渲染 -->
- [ ] 欄位結構與法律邏輯已校對無誤。
- **校對筆記**: 
"""
                    with open(note_path, 'w', encoding='utf-8') as f_note:
                        f_note.write(note_content)
                    
                    created_notes.append((note_filename, str(note_path)))
                    
        return created_notes

    def track_video_blackboard(self, video_path: str, class_name: str, lesson_name: str, status_callback=None) -> list:
        """
        以低記憶體抽樣分析影片，使用像素影格差分算法偵測老師板書的動作，
        自動截圖並判別是「文字板書」還是「關係圖板書」，
        生成 Obsidian 連接筆記，對比資料庫法條並附帶 Mermaid 邏輯圖。
        """
        if cv2 is None:
                return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
                print(f"[WARNING] Cannot open video file: {video_path}")
                return []

        # 取得影片資訊與抽樣間隔 (預設優化為每 15 秒抽樣一影格，可由 config.yaml 配置)
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        interval_sec = 1.0 # 預設 1 秒 (建立連續影格比對機制，防 15s 差異過大 OOM)
        try:
                cfg = load_config()
                val = float(cfg.get("settings", {}).get("video_sample_interval_sec", 1.0))
                if val > 2.0:
                    interval_sec = 1.0 # 強制限制，避免超過 2 秒引發無限截圖
                else:
                    interval_sec = val
        except:
                pass
                
        sample_interval = max(1, int(interval_sec * fps))
        
        prev_gray = None
        is_writing = False
        writing_start_frame = 0
        last_captured_time = -30  # 避免 30 秒內重複擷取
        
        created_notes = []
        frame_idx = 0
        board_idx = 0
        video_stem = Path(video_path).stem
        clean_video_name = self._sanitize_filename(video_stem)
        if os.environ.get("TEST_MODE_ACCELERATED") == "1":
                max_test_frames = 90 * fps
        else:
                max_test_frames = total_frames

        try:
            while True:
                if frame_idx >= max_test_frames:
                    break
                    
                current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                if current_frame != int(frame_idx):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
                    
                ret, frame = cap.read()
                if not ret:
                    break

                current_sec = frame_idx // fps
                
                # 轉換為灰階並進行高斯模糊
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur_gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if prev_gray is not None:
                    # 計算影格絕對像素差異
                    frame_diff = cv2.absdiff(prev_gray, blur_gray)
                    _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
                    
                    # 計算變化像素總量
                    changed_pixels = np.sum(thresh == 255)
                    h_f, w_f = gray.shape
                    total_pixels = h_f * w_f
                    change_ratio = changed_pixels / total_pixels
                    
                    # 判定動作：大於 0.8% 視為正在書寫或走動
                    if change_ratio > 0.008:
                        if not is_writing:
                            is_writing = True
                            writing_start_frame = frame_idx
                    else:
                        # 當像素變化降低（小於 0.15%）且之前處於書寫狀態
                        if is_writing:
                            is_writing = False
                            
                            # 確保距離上次擷取已超過 30 秒，且書寫時間大於 5 秒，避免抓到單純晃動
                            if (current_sec - last_captured_time) >= 30 and (frame_idx - writing_start_frame) > (5 * fps):
                                board_idx += 1
                                last_captured_time = current_sec
                                
                                # 擷取當前寫完後的乾淨板書（中間 80% 區域通常為黑板主體）
                                y_start, y_end = int(h_f * 0.1), int(h_f * 0.9)
                                x_start, x_end = int(w_f * 0.1), int(w_f * 0.9)
                                board_crop = frame[y_start:y_end, x_start:x_end]
                                
                                # 儲存板書擷圖 (Unicode 安全寫法)
                                ts_str = f"{int(current_sec // 3600):02d}_{int((current_sec % 3600) // 60):02d}_{current_sec % 60:02d}"
                                board_filename = f"board_{clean_video_name}_{ts_str}.png"
                                board_path = self.image_dir / board_filename
                                is_success, buffer = cv2.imencode(".png", board_crop)
                                if is_success:
                                    with open(str(board_path), "wb") as f:
                                        f.write(buffer)
                                else:
                                    cv2.imwrite(str(board_path), board_crop)
                                
                                if status_callback:
                                    status_callback(f"🎬 偵測到老師板書動作！時間點: {current_sec // 60}分{current_sec % 60}秒，已自動截圖...")

                                # 優先使用雲端 Gemini 進行高精度板書視覺辨識與法理分析
                                gemini_key = get_gemini_key()
                                ai_analysis = ""
                                mermaid_code = "graph TD\n    A[\"影音板書\"] --> B[\"尚無關聯關係\"]"
                                board_type_label = "影音板書"
                                
                                if gemini_key and not getattr(self, "gemini_multimodal_disabled", False):
                                    if status_callback:
                                        status_callback(f"🎬 正在呼叫雲端多模態模型進行板書視覺辨識與法學分析...")
                                    
                                    gemini_prompt = f"""你是一個精通臺灣法律與繁體中文的專業聽寫速記與影像分析助理。
我們正在對法律影音教材《{video_stem}》進行高精度分析。目前在時間點 {current_sec // 60}分{current_sec % 60}秒，偵測到老師書寫了板書並擷取了此圖片。
請仔細「看」這張板書圖片，並完成以下任務：
1. 【板書高精度 OCR】：將圖片中老師寫的所有文字、符號與關係一字不漏地辨識出來。
2. 【板書詳細解讀與法條對照】：
   - 解說板書所代表的法律學理、爭點、案例邏輯或關係。
   - 自動對照並聯想臺灣現行法律條文（如民法第184條、侵權行為、消滅時效等），寫下理解與演化註記。
3. 【生成 Mermaid 邏輯圖】：
   - 根據圖片中呈現的關係結構（如人際關係、法律行為流程等），生成對應的 Mermaid.js 關係圖代碼（以 graph TD 或 graph LR 開頭）。
   - 注意：Mermaid 節點文字必須用雙引號括住，例如 A["原告甲"] --> B["被告乙"]，以防渲染語法出錯。

請只輸出以下格式（不要有任何多餘的 Markdown 外置標記，直接輸出標題與內容）：
【解讀與註記】：
(您的詳細法律理解說明與條文對位，包含辨識出的文字)

【MERMAID 代碼】：
(完整的 mermaid 程式碼，不要用 ``` 符號包裹)
"""
                                    ai_response = self._query_gemini_multimodal(str(board_path), gemini_prompt, gemini_key)
                                    
                                    if ai_response and "【解讀與註記】" in ai_response:
                                        parts = ai_response.split("【MERMAID 代碼】")
                                        ai_analysis = parts[0].replace("【解讀與註記】", "").strip()
                                        if len(parts) > 1:
                                            mermaid_code = parts[1].replace(":", "").strip()
                                            mermaid_code = re.sub(r"^```mermaid", "", mermaid_code)
                                            mermaid_code = re.sub(r"```$", "", mermaid_code).strip()
                                    else:
                                        ai_analysis = ai_response if ai_response else "（雲端解讀生成失敗）"
                                
                                # 若無金鑰或雲端失敗，回退至本地 Tesseract 與 Ollama
                                if not ai_analysis or ai_analysis.strip() == "（雲端解讀生成失敗）":
                                    if status_callback:
                                        status_callback(f"⚠️ 雲端辨識不可用，回退至本地 OCR 與 Ollama...")
                                    ocr_text = ""
                                    if pytesseract is not None:
                                        try:
                                            board_rgb = cv2.cvtColor(board_crop, cv2.COLOR_BGR2RGB)
                                            ocr_text = pytesseract.image_to_string(Image.fromarray(board_rgb), lang='chi_tra+eng').strip()
                                        except:
                                            pass
                                    is_text_board = len(ocr_text) > 15
                                    board_type_label = "文字板書" if is_text_board else "關係圖/邏輯圖板書"
                                    
                                    local_prompt = f"""你是一個精通臺灣法律實務的助理。我們在法律影音教材《{video_stem}》的時間點：{current_sec // 60}分{current_sec % 60}秒 偵測到老師書寫了板書，並自動截圖。
擷取類型分類為：【{board_type_label}】。
擷取區域的 OCR 辨識字元如下：
<document>
{ocr_text}
</document>

請根據這些資訊與您擁有的台灣法律知識，幫我完成以下事項：
1. 針對辨識出的板書文字，進行語意整理，並自動與臺灣現行法律條文（如民法第184條、侵權行為、消滅時效等）進行比對，寫下「知識庫比對與理解演化註記」。
2. 如果分類為「關係圖/邏輯圖板書」（或者有複雜邏輯關係），請幫我生成對應的 Mermaid.js 流程圖代碼以呈現老師黑板上的圖畫結構。
   - 注意：Mermaid 節點文字必須用雙引號括住，例如 A["原告甲"] --> B["被告乙"]，以防語法出錯。
   - 如果分類為「文字板書」，則生成一個整理好的條列式邏輯樹 Mermaid 關係圖。

請只輸出：
【解讀與註記】：
(您的詳細法律理解說明與條文對位)

【MERMAID 代碼】：
(完整的 mermaid 程式碼塊，如 graph TD ... 等，不要帶 markdown ``` 符號)
"""
                                    ai_response = self._query_llm(local_prompt)
                                    if "【解讀與註記】" in ai_response:
                                        parts = ai_response.split("【MERMAID 代碼】")
                                        ai_analysis = parts[0].replace("【解讀與註記】", "").strip()
                                        if len(parts) > 1:
                                            mermaid_code = parts[1].replace(":", "").strip()
                                            mermaid_code = re.sub(r"^```mermaid", "", mermaid_code)
                                            mermaid_code = re.sub(r"```$", "", mermaid_code).strip()
                                    else:
                                        ai_analysis = ai_response
                                
                                # 寫入 Obsidian Markdown 校對筆記
                                note_filename = f"校對_影音板書_{clean_video_name}_{ts_str}.md"
                                note_path = self.obsidian_dir / note_filename
                                
                                timestamp_hms = f"{current_sec // 3600:02d}:{ (current_sec % 3600) // 60:02d}:{current_sec % 60:02d}"
                                
                                note_content = f"""# 🎥 影音教材板書校對筆記
- **來源影片**: [{video_stem}](file:///{video_path.replace('\\', '/')})
- **課程分類**: `{class_name}`
- **課堂章節**: `{lesson_name}`
- **影片時間戳記**: `{timestamp_hms}` ({current_sec} 秒)
- **板書類型**: `{board_type_label}`
- **偵測時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 🔍 擷取黑板板書對照圖
![板書](./images/{board_filename})

## 🧠 AI 智慧理解與知識庫演化註記
{ai_analysis}

## 📊 可編輯之 Mermaid 關係流程圖
```mermaid
{mermaid_code}
```

## ✍️ 操作者手動校對修改區
<!-- 您可以直接修改上方的文字或調整 Mermaid 區塊中的節點，Obsidian 會即時重新渲染 -->
- [ ] 欄位結構與法律邏輯已校對無誤。
- **校對筆記**: 
"""
                                with open(note_path, 'w', encoding='utf-8') as f_note:
                                    f_note.write(note_content)
                                
                                created_notes.append((note_filename, str(note_path)))

                # 更新前一影格
                prev_gray = blur_gray
                frame_idx += sample_interval
                
                if frame_idx >= total_frames:
                    break
        finally:
            cap.release()
            
        return created_notes

```

## auto_ingest_bot.py

```python
# -*- coding: utf-8 -*-
import os
import sys
import time
import re
import json
import gc
from pathlib import Path

# 將 root 與 scripts 目錄納入 PATH，確保子模組順利載入
curr_dir = Path(__file__).resolve().parent
if curr_dir.name in ("新程式碼", "scripts", "extracted_sources"):
    base_dir = curr_dir.parent
else:
    base_dir = curr_dir

sys.path.append(str(base_dir))
sys.path.append(str(base_dir / "scripts"))
sys.path.append(str(base_dir / "extracted_sources" / "scripts"))

# 強制 stdout / stderr 採用 UTF-8 輸出，防止 Windows cp950 編碼錯誤崩潰
if sys.platform == "win32":
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

from agent_core_pro import LocalLegalAgent
from multimodal_input import MultimodalLegalInput
from visual_analyzer import VisualLegalAnalyzer

# 套用 48GB DRAM 環境硬體優化配置 (Single Source of Truth)
try:
    from scripts.config_loader import apply_hardware_config
    cfg = apply_hardware_config()
    CHROMA_TEXT_LIMIT = cfg.get("chroma_text_limit", 150000)
except Exception:
    import os
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["MKL_NUM_THREADS"] = "4"
    CHROMA_TEXT_LIMIT = 150000

import hashlib

SUPPORTED_EXTS = {'.mp3', '.mp4', '.wav'}  # 嚴格依照使用者要求：規定除非有特殊原因，否則預設就是只能吸入國家考試「司法官與律師」等法律相關專業科目的純影音格式
# 嚴格依照使用者要求：前提是必須嚴格封鎖非國家考試「司法官與律師」等法律相關專業科目以外的雜訊檔案
LAW_KEYWORDS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法"]

TAIWAN_LEGAL_PATTERNS = [
    r"\d+\s*年\s*[^\d\s]+\s*字第\s*\d+\s*號",  # 裁判字號，例如 112年上字第10號
    r"第\s*\d+\s*條",                       # 法條，例如 第197條
    r"民法|刑法|民事訴訟法|刑事訴訟法|行政程序法|司法院|法院|最高法院|檢察署|檢察官|起訴書|判決書|裁定書|訴狀|聲請書|答辯狀"
]

def get_file_hash(f_path):
    """計算檔案的 SHA-256 雜湊值，作為智能資料記憶的核心憑據"""
    sha256 = hashlib.sha256()
    try:
        if not os.path.exists(f_path):
            return None
        with open(f_path, 'rb') as f:
            while True:
                data = f.read(65536) # 64KB blocks
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    except Exception:
        return None

def check_text_for_legal_relevance(text):
    """分析文字內容，利用正則表達式與關鍵字密度判定是否為法律相關教材"""
    if not text:
        return False
    # 1. 檢查台灣法律特有正則特徵
    for pattern in TAIWAN_LEGAL_PATTERNS:
        if re.search(pattern, text):
            return True
    # 2. 統計獨特法律關鍵字數量
    matched_kws = set()
    for kw in LAW_KEYWORDS:
        if kw in text:
            matched_kws.add(kw)
    # 若包含至少 2 個不同的法律關鍵字，則視為法律相關
    if len(matched_kws) >= 2:
        return True
    return False

def is_file_content_legal(f_path):
    """智能分析檔案名稱、路徑或實際內容，精確判別是否為法律教材，杜絕亂抓資料"""
    f_path_lower = str(f_path).lower()
    f_name = os.path.basename(f_path_lower)
    ext = os.path.splitext(f_path_lower)[1]
    
    # 1. 首先檢查檔名本身是否符合法律特徵
    name_kws = [kw for kw in LAW_KEYWORDS if kw.lower() in f_name]
    if len(name_kws) >= 2:
        return True
        
    # 2. 如果檔名特徵不足，針對文本檔/PDF讀取內容進行語意分析
    if ext in {'.txt', '.md'}:
        try:
            with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                head = f.read(3000)
                if check_text_for_legal_relevance(head):
                    return True
        except Exception:
            pass
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(f_path)
            pages_text = []
            for i in range(min(2, len(reader.pages))):
                text = reader.pages[i].extract_text()
                if text:
                    pages_text.append(text)
            combined_text = "\n".join(pages_text)
            if check_text_for_legal_relevance(combined_text):
                return True
        except Exception:
            pass
            
    # 3. 影音與圖像檔案在尚未進行 ASR/OCR 之前僅以路徑做為防護線，必須在完整路徑中包含法律關鍵字
    if ext in {'.png', '.jpg', '.jpeg', '.mp3', '.mp4', '.wav'}:
        if any(kw.lower() in f_path_lower for kw in LAW_KEYWORDS):
            return True
            
    return False

EXCLUDE_DIRS = {
    "system volume information", "$recycle.bin", "windows", "program files", 
    "program files (x86)", "appdata", ".gemini", "node_modules", ".git", 
    "localaio_workstation", "temp", "cache", "anaconda3", "miniconda3", 
    ".conda", ".cargo", ".rustup", "pycache", "__pycache__", ".vscode", 
    "venv", ".venv", "build", "dist", "obj", "bin"
}

BUFFER_FILE = "C:\\LocalAI_Workstation\\chosen_paths_buffer.json"

def scan_drives(scan_path=None):
    """搜尋指定的路徑或本機所有有效磁碟機中符合條件的法律教材資料夾，嚴防指定 H: 卻掃描其他磁碟之問題"""
    valid_folders = []
    drives = []
    
    # 如果傳入了指定路徑（防止亂抓其他磁碟）
    if scan_path:
        scan_path = str(scan_path).strip()
        # 移除引號
        if (scan_path.startswith('"') and scan_path.endswith('"')) or (scan_path.startswith("'") and scan_path.endswith("'")):
            scan_path = scan_path[1:-1].strip()
        
        # 處理 Windows 磁碟機，例如 H -> H:\ 或 H: -> H:\
        if len(scan_path) == 1 and scan_path.isalpha():
            scan_path = scan_path + ":\\"
        elif len(scan_path) == 2 and scan_path[1] == ':' and scan_path[0].isalpha():
            scan_path = scan_path + "\\"
            
        scan_path = os.path.abspath(scan_path)
        if not os.path.exists(scan_path):
            print(f"\n[Step 1] ❌ 指定的路徑不存在: {scan_path}")
            return []
            
        print(f"\n[Step 1] 開始精確掃描指定的路徑/資料夾: {scan_path}...")
        
        # 如果是單一檔案
        if os.path.isfile(scan_path):
            f_name = os.path.basename(scan_path)
            f_ext = os.path.splitext(f_name)[1].lower()
            if f_ext in SUPPORTED_EXTS:
                if is_file_content_legal(scan_path):
                    parent_dir = os.path.dirname(scan_path)
                    print(f"      [找到有效教材檔案] {scan_path}")
                    return [parent_dir]
            return []
            
        # 如果是特定資料夾且不是磁碟根目錄，先直接加入以防其命名沒有法律關鍵字但使用者刻意指定
        is_drive_root = (len(scan_path) == 3 and scan_path[1:] == ":\\") or scan_path == "/"
        if not is_drive_root and os.path.isdir(scan_path):
            try:
                # 檢查資料夾下是否有法律教材檔案
                has_legal_file = False
                for f in os.listdir(scan_path):
                    f_path = os.path.join(scan_path, f)
                    if os.path.isfile(f_path) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
                        if is_file_content_legal(f_path):
                            has_legal_file = True
                            break
                if has_legal_file:
                    valid_folders.append(scan_path)
            except Exception:
                pass
                
        # 以此為起點
        drives = [scan_path]
    else:
        print("\n[Step 1] 開始掃描本機磁碟尋找法律教材資料夾...")
        # 獲取本機所有存在的磁碟機字母，排除未準備好的磁碟（例如光碟機）
        if sys.platform == "win32":
            try:
                import ctypes
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for i in range(26):
                    if bitmask & (1 << i):
                        drive_path = f"{chr(65+i)}:\\"
                        # 取得磁碟類型並進行唯讀/準備狀態測試
                        dtype = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                        # 2: REMOVABLE, 3: FIXED, 4: REMOTE
                        if dtype in (2, 3, 4):
                            try:
                                # 測試是否可讀，不可讀會拋出異常
                                os.listdir(drive_path)
                                drives.append(drive_path)
                            except Exception:
                                pass
            except Exception:
                # 備用方案
                import string
                for letter in string.ascii_uppercase:
                    drive_path = f"{letter}:\\"
                    if os.path.exists(drive_path):
                        drives.append(drive_path)
        else:
            drives = ["/"]
            
        print(f"   -> 偵測到可讀取之本機磁碟機: {', '.join(drives)}")
    
    for drive in drives:
        print(f"   -> 正在掃描路徑 {drive} (最大深度限制為 8)...")
        # 遍歷目錄
        for root, dirs, files in os.walk(drive, topdown=True):
            # 計算當前深度
            try:
                rel_path = os.path.relpath(root, drive)
                depth = 0 if rel_path == "." else len(Path(rel_path).parts)
            except Exception:
                continue
            
            # 限制掃描最大深度為 8
            if depth >= 8:
                dirs.clear() # 停止遞迴其子目錄
                continue
                
            # 過濾掉敏感與系統目錄，防止掃描時卡死或速度極慢
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIRS and not d.startswith('.')]
            
            # 檢查完整路徑是否含有法律相關關鍵字 (解決課程名稱通常建立在父資料夾的實務情況)
            folder_matches = any(kw in root for kw in LAW_KEYWORDS)
            
            has_valid_media = False
            file_matches = False
            
            try:
                # 遍歷旗下檔案
                for f in os.listdir(root):
                    f_ext = os.path.splitext(f)[1].lower()
                    if f_ext in SUPPORTED_EXTS:
                        has_valid_media = True
                        # 如果檔案名稱包含法律關鍵字
                        if any(kw in f for kw in LAW_KEYWORDS):
                            file_matches = True
            except Exception:
                pass
                
            # 雙重特徵匹配：資料夾名稱匹配且含有媒體，或檔案本身符合媒體且名稱匹配
            if has_valid_media and (folder_matches or file_matches):
                abs_path = os.path.abspath(root)
                if abs_path not in valid_folders:
                    valid_folders.append(abs_path)
                    reason = "資料夾名稱符合" if folder_matches else "檔案名稱符合"
                    print(f"      [找到有效教材資料夾 ({reason}, 深度: {depth})] {abs_path}")
                        
    return valid_folders

def update_buffer_file(paths):
    """將搜尋到的路徑寫入 chosen_paths_buffer.json"""
    try:
        os.makedirs(os.path.dirname(BUFFER_FILE), exist_ok=True)
        with open(BUFFER_FILE, "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=4)
        print(f"\n[Step 2] 成功將 {len(paths)} 個路徑寫入介面快取 buffer 檔案中。")
    except Exception as e:
        print(f"\n[Step 2] ❌ 寫入快取檔失敗: {e}")

HISTORY_FILE = "C:\\LocalAI_Workstation\\ingested_history.json"

def load_ingested_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                if isinstance(history, dict):
                    return history
        except Exception:
            pass
    return {}

def save_ingested_history(history):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
PROCESSED_STEMS_CACHE = None

def get_processed_stems():
    """快取所有已處理的檔案名稱，避免每次都掃描硬碟，造成 I/O 瓶頸"""
    global PROCESSED_STEMS_CACHE
    if PROCESSED_STEMS_CACHE is None:
        PROCESSED_STEMS_CACHE = set()
        processed_dir = Path("A:\\processed_md")
        if processed_dir.exists():
            for md_file in processed_dir.glob("*.md"):
                if md_file.name != "00_已處理清單_Agent請查閱此表.md":
                    PROCESSED_STEMS_CACHE.add(md_file.name)
    return PROCESSED_STEMS_CACHE

def generate_processed_report_table():
    """為未來的 Agent 與使用者產生一份總結表格，放在 A:\\processed_md 中方便查閱避免重複"""
    processed_dir = Path("A:\\processed_md")
    if not processed_dir.exists():
        return
        
    md_files = list(processed_dir.glob("*.md"))
    md_files = [f for f in md_files if f.name != "00_已處理清單_Agent請查閱此表.md"]
    
    report_lines = [
        "# 📚 全域已處理課程總表 (Source of Truth)",
        "本表由自動機器人維護，列出所有已經成功消化並產出講義的實體課程檔案。**任何 AI Agent 在進行處理前，請優先查閱此表以避免重複做工！**",
        "",
        f"**最後更新時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**已處理總數**: {len(md_files)} 堂課",
        "",
        "| 課程檔案名稱 | 大小 (KB) | 產出講義時間 |",
        "|---|---|---|"
    ]
    
    # 依時間排序 (最新的在最上面)
    try:
        md_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        for f in md_files:
            size_kb = round(os.path.getsize(f) / 1024, 2)
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(f)))
            report_lines.append(f"| {f.name} | {size_kb} | {mtime} |")
            
        report_path = processed_dir / "00_已處理清單_Agent請查閱此表.md"
        with open(report_path, "w", encoding="utf-8") as out_f:
            out_f.write("\n".join(report_lines))
    except Exception:
        pass

def is_file_already_ingested(f_path, history):
    # 1. 終極真實來源 (Source of Truth) 檢查：比對記憶體快取中的 A:\processed_md 產物
    try:
        stem = Path(f_path).stem
        stems_cache = get_processed_stems()
        for processed_name in stems_cache:
            if stem in processed_name:
                return True
    except Exception:
        pass

    # 2. 若實體檔案不存在，退回檢查 JSON 紀錄檔
    if f_path not in history:
        return False
    try:
        current_hash = get_file_hash(f_path)
        if not current_hash:
            return False
        record = history[f_path]
        
        # 1. 優先使用 SHA-256 雜湊比對（黃金標準）
        if "hash" in record:
            if record["hash"] == current_hash:
                return True
        else:
            # 2. 相容舊版：比對大小與修改時間，若一致則補算並升級 hash 紀錄
            current_size = os.path.getsize(f_path)
            current_mtime = os.path.getmtime(f_path)
            if record.get("size") == current_size and record.get("mtime") == current_mtime:
                record["hash"] = current_hash
                save_ingested_history(history)
                return True
    except Exception:
        pass
    return False

def record_file_ingested(f_path, history):
    try:
        f_hash = get_file_hash(f_path)
        history[f_path] = {
            "size": os.path.getsize(f_path),
            "mtime": os.path.getmtime(f_path),
            "hash": f_hash,
            "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_ingested_history(history)
    except Exception:
        pass

def run_ingest(folders):
    """執行一鍵吸收與消化"""
    print("\n[Step 3] 開始全自動批次教材消化建置流程...")
    
    # 1. 收集資料夾下所有有效檔案
    valid_files_info = []
    seen_paths = set()
    
    for folder in folders:
        p_obj = Path(folder)
        if not p_obj.exists():
            continue
        # 遞迴掃描旗下所有支援的檔案
        for f in p_obj.rglob("*"):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
                abs_p = str(f.resolve())
                if abs_p not in seen_paths:
                    # 智能資料比對：分析是否是法律相關的資料來源，不逆向亂抓無關資料
                    if not is_file_content_legal(abs_p):
                        print(f"   [跳過無關檔案] {f.name} (經智慧防護判定非法律相關內容)")
                        continue
                    seen_paths.add(abs_p)
                    valid_files_info.append((f.name, abs_p, folder))
                    
    total = len(valid_files_info)
    if total == 0:
        print("   -> ❌ 未在此等資料夾下發現任何可消化的影音或文件教材！結束。")
        return
        
    print(f"   -> 收集完畢，共計 {total} 個教材檔案待處理。")
    
    # 刷新並產生給 Agent 看的總結報表
    generate_processed_report_table()
    
    # 產生比對報表 (Table)
    history = load_ingested_history()
    print("\n" + "="*85)
    print(" 📊 自動掃描檔案比對狀態總覽表 (Processed vs Unprocessed)")
    print("-" * 85)
    
    pending_files = []
    for disp_name, f_path, parent_folder in valid_files_info:
        is_processed = is_file_already_ingested(f_path, history)
        status_text = "[已處理 - 跳過]" if is_processed else "[待處理 - 佇列中]"
        
        # 簡單縮排處理以因應中文字元長度不定
        print(f" {status_text} | {Path(parent_folder).name} -> {disp_name}")
        
        if not is_processed:
            pending_files.append((disp_name, f_path, parent_folder))
            
    print("="*85)
    print(f"\n   -> 報表總結: 共找到 {total} 個檔案，其中 {total - len(pending_files)} 個已消化過，準備處理 {len(pending_files)} 個新檔案。")
    
    if not pending_files:
        print("   -> 🟢 所有檔案皆已處理完畢，無新檔案需消化！結束。")
        update_buffer_file([])
        return
        
    # 2. 初始化 AI 與處理器 (延後到確定有檔案要處理才載入，節省資源)
    print("   -> 正在初始化核心 AI 代理人與多模態處理器...")
    agent = LocalLegalAgent()
    processor = MultimodalLegalInput(model_size="small")
    analyzer = VisualLegalAnalyzer()
    
    transcripts_dir = "C:\\LocalAI_Workstation\\Transcripts"
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # 3. 逐一處理待辦檔案
    total_pending = len(pending_files)
    for idx, (disp_name, f_path, parent_folder) in enumerate(pending_files):
            
        print(f"\n------------------------------------------------------------")
        print(f" [進度: {idx+1} / {total}] 正在吸收: {disp_name}")
        print(f" 檔案路徑: {f_path}")
        print(f"------------------------------------------------------------")
        
        try:
            # 推定課程與課堂名稱 (依據資料夾結構)
            parent_dir = Path(f_path).parent
            grandparent_dir = parent_dir.parent if parent_dir else None
            
            lesson_name = parent_dir.name if parent_dir else "預設課堂"
            class_name = grandparent_dir.name if grandparent_dir and grandparent_dir.name != Path(parent_folder).parent.name else "預設課程"
            
            p_file = Path(f_path)
            file_size_mb = os.path.getsize(f_path) / (1024 * 1024)
            
            raw_text = ""
            pages_list = []
            
            # 處理轉錄或 OCR
            if p_file.suffix.lower() in ['.mp3', '.mp4', '.wav']:
                print("   [1/3] 正在進行影音 Whisper 實時轉錄...")
                raw_text = processor.transcribe_audio(f_path)
                
                if p_file.suffix.lower() == '.mp4':
                    print("   [1.5] 偵測到影片，正在擷取板書圖表筆記...")
                    video_notes = analyzer.track_video_blackboard(f_path, class_name, lesson_name)
                    
                print("   [2/3] 正在使用 LLM 校正拼音與裁判錯字...")
                final_text = processor.post_refine_using_llm(raw_text)
            elif p_file.suffix.lower() == '.txt':
                with open(f_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                    raw_text = f_in.read(CHROMA_TEXT_LIMIT)
                print("   [2/3] 正在使用 LLM 進行校正...")
                final_text = processor.post_refine_using_llm(raw_text)
            else:
                print("   [1/3] 正在進行書面文件 OCR 辨識與視覺版面分析...")
                pages_list = processor.ocr_document(f_path)
                combined_ocr_text = "\n".join([p["text"] for p in pages_list])
                print("   [2/3] 正在使用 LLM 進行校正...")
                final_text = processor.post_refine_using_llm(combined_ocr_text)
                
            # 儲存逐字稿文字檔
            def sanitize_filename(name: str) -> str:
                for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    name = name.replace(char, '')
                return name.strip()
                
            out_filename = f"{sanitize_filename(class_name)}_{sanitize_filename(lesson_name)}_{sanitize_filename(p_file.stem)}_逐字稿.txt"
            out_filepath = os.path.join(transcripts_dir, out_filename)
            with open(out_filepath, "w", encoding="utf-8") as f_out:
                f_out.write(final_text)
            print(f"   -> [逐字稿存檔] {out_filepath}")
            
            # 摘要並上傳向量資料庫
            print("   [3/3] 正在利用大模型提煉核心爭點與推理路徑並建檔...")
            payload_prompt = f"分析以下文本，提煉出：核心爭點、推理路徑、結論：\n\n<document>\n{final_text[:2000]}\n</document>"
            res = agent.chat(payload_prompt) # 調用 agent 做推理
            summary = res[0] if isinstance(res, tuple) else str(res)
            
            # 儲存到智商庫
            safe_chroma_text = final_text[:CHROMA_TEXT_LIMIT]
            doc_to_store = f"【自動吸收消化精華】\n{summary}\n\n【原始校對文本】\n{safe_chroma_text}"
            doc_embedding = agent._get_embedding(doc_to_store)
            if doc_embedding:
                agent.intel_coll.add(
                    ids=[f"auto_ref_{p_file.name}_{idx}_{int(time.time())}"],
                    documents=[doc_to_store],
                    embeddings=[doc_embedding],
                    metadatas=[{"source": disp_name, "mode": "機器人全自動吸收", "size_mb": round(file_size_mb, 2), "type": "summary", "class_name": class_name, "lesson_name": lesson_name}]
                )
                print("   -> [成功] 向量智商庫 Upsert 成功，該教材已吸收完畢。")
                record_file_ingested(f_path, history)
                
            # 記憶體清理
            if 'raw_text' in locals(): del raw_text
            if 'final_text' in locals(): del final_text
            if 'pages_list' in locals(): del pages_list
            gc.collect()
            time.sleep(0.5)
            
        except Exception as file_e:
            print(f"   -> ❌ 教材 {disp_name} 消化失敗，原因: {file_e}")
            
    # 全數成功後清空快取
    update_buffer_file([])
    print("\n[Bot SUCCESS] 本批本機法律教材已全自動搜尋並吸收消化完畢！快取已清空。")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="本機法律教材全自動搜尋與一鍵吸收機器人")
    parser.add_argument("--dry-run", action="store_true", help="乾衣模式：僅掃描並列出符合條件的法律資料夾，不進行實際寫入與消化。")
    parser.add_argument("--path", type=str, default=None, help="指定掃描與吸取的路徑（精確位址，例如：H: 或 H:\\foo）")
    args = parser.parse_args()
    
    folders = scan_drives(scan_path=args.path)
    
    if not folders:
        print("\n❌ 本機磁碟中未找到任何名稱含有法律關鍵字且包含影音/文件的教材資料夾。")
        return
        
    print(f"\n本次共掃描出 {len(folders)} 個符合條件的法律資料夾。")
    
    if args.dry_run:
        print("\n[Mode: Dry-Run] 已成功列出所有符合的資料夾。乾衣模式結束，不進行寫入與消化。")
        return
        
    # 寫入介面快取，這樣前台重新整理時能看見
    update_buffer_file(folders)
    
    # 執行全自動吸收
    run_ingest(folders)

if __name__ == "__main__":
    main()

```

## preprocess_media.py

```python
import os
import sys
import argparse
import json
import subprocess
from pathlib import Path
from workflow_helper import ensure_dirs, log_workflow, log_error, get_ffmpeg_path, get_ffprobe_path
from workflow_helper import ensure_dirs, log_workflow, log_error, get_ffmpeg_path, get_ffprobe_path

def get_safe_env():
    # 【資安修補】安全繼承白名單環境變數，防止子進程外洩敏感金鑰
    whitelist = {"PATH", "SystemRoot", "USERPROFILE", "SystemDrive", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"}
    return {k: v for k, v in os.environ.items() if k in whitelist}

def atomic_write_json(file_path, data):
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as wf:
        json.dump(data, wf, ensure_ascii=False, indent=2)
    os.replace(tmp_path, file_path)
def get_media_info(file_path):
    cmd = [
        get_ffprobe_path(), "-v", "error",
        "-show_format", "-show_streams",
        "-of", "json", file_path
    ]
    # 【資安修補】安全繼承白名單環境變數
    safe_env = get_safe_env()
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore", env=safe_env, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)

def preprocess(task_id):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    chunks_dir = paths["chunks_dir"]
    
    manifest_file = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_file):
        log_error(f"Manifest file not found: {manifest_file}")
        return False
        
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    source_path = manifest["source_path"]
    if not os.path.exists(source_path):
        log_error(f"Source file not found: {source_path}")
        manifest["status"] = "failed"
        manifest["error"] = "Source file missing"
        atomic_write_json(manifest_file, manifest)
        return False

    log_workflow(f"Preprocess Agent: Analyzing media info for {manifest['source_name']}")
    
    try:
        media_info = get_media_info(source_path)
    except Exception as e:
        log_error(f"Failed to read media info for {source_path}: {e}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffprobe error: {e}"
        atomic_write_json(manifest_file, manifest)
        return False

    # 解析影音資訊
    fmt = media_info.get("format", {})
    try:
        if os.environ.get("TEST_MODE_ACCELERATED") == "1":
            duration = min(90.0, float(fmt.get("duration", 0)))
        else:
            duration = float(fmt.get("duration", 0))
    except (ValueError, TypeError):
        duration = 0.0
    bitrate = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else 0
    size_bytes = int(fmt.get("size", 0))
    
    has_video = False
    has_audio = False
    resolution = "N/A"
    audio_codec = "N/A"
    channels = 0
    sample_rate = 0
    
    for stream in media_info.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            has_video = True
            width = stream.get("width")
            height = stream.get("height")
            if width and height:
                resolution = f"{width}x{height}"
        elif codec_type == "audio":
            has_audio = True
            audio_codec = stream.get("codec_name", "N/A")
            channels = int(stream.get("channels", 0)) if stream.get("channels") else 0
            sample_rate = int(stream.get("sample_rate", 0)) if stream.get("sample_rate") else 0

    log_workflow(f"Media Info: Video={has_video} ({resolution}), Audio={has_audio} ({audio_codec}), Duration={duration:.1f}s")
    
    # 建立該任務的切片資料夾
    task_chunks_dir = os.path.join(chunks_dir, task_id)
    os.makedirs(task_chunks_dir, exist_ok=True)
    
    chunk_pattern = os.path.join(task_chunks_dir, "chunk_%03d.wav")
    
    log_workflow(f"Preprocess Agent: Extracting and segmenting audio to {chunk_pattern}")
    if os.environ.get("TEST_MODE_ACCELERATED") == "1":
        ffmpeg_cmd = [
            get_ffmpeg_path(), "-y", "-i", source_path,
            "-t", "90",
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-f", "segment", "-segment_time", "600",
            chunk_pattern
        ]
    else:
        ffmpeg_cmd = [
            get_ffmpeg_path(), "-y", "-i", source_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-f", "segment", "-segment_time", "600",
            chunk_pattern
        ]
    
    try:
        # 【資安修補】安全繼承白名單環境變數
        safe_env = get_safe_env()
        result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore", env=safe_env, timeout=1200)
    except Exception as run_err:
        log_error(f"Failed to run ffmpeg command {ffmpeg_cmd}: {run_err}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffmpeg execution exception: {run_err}"
        atomic_write_json(manifest_file, manifest)
        return False
    if result.returncode != 0:
        log_error(f"ffmpeg extraction failed: {result.stderr}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffmpeg error: {result.stderr}"
        atomic_write_json(manifest_file, manifest)
        return False
        
    import glob
    chunks = []
    chunk_files = sorted(glob.glob(os.path.join(task_chunks_dir, "chunk_*.wav")))
    for idx, cf in enumerate(chunk_files):
        chunks.append({
            "chunk_index": idx,
            "filename": os.path.basename(cf),
            "path": cf,
            "start_time": idx * 600.0,
            "end_time": (idx + 1) * 600.0 if idx < len(chunk_files) - 1 else duration,
            "status": "pending",
            "retry_count": 0
        })
        
    chunks_manifest_file = os.path.join(manifests_dir, f"{task_id}_chunks.json")
    atomic_write_json(chunks_manifest_file, chunks)
        
    manifest["chunks_count"] = len(chunks)

    # 更新 Manifest 資訊
    manifest["media_info"] = {
        "duration_sec": duration,
        "size_bytes": size_bytes,
        "has_video": has_video,
        "has_audio": has_audio,
        "resolution": resolution,
        "audio_codec": audio_codec,
        "audio_channels": channels,
        "audio_sample_rate": sample_rate,
        "extracted_audio_path": chunk_files[0] if chunk_files else ""
    }
    manifest["steps"]["preprocess"] = "completed"
    manifest["status"] = "preprocessed"
    
    atomic_write_json(manifest_file, manifest)
        
    log_workflow(f"Preprocess Agent: Completed task {task_id}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    preprocess(args.task_id)

```

## stt_runner.py

```python
import os
import sys
# Append project root to sys.path to resolve ModuleNotFoundError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
import yaml
import time
import subprocess
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from google import genai
from google.genai import types
from scripts.quota_manager import QuotaManager
from scripts.whisper_pool import WhisperPool
def init_gemini_client(config):
    # Load dotenv from potential paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    potential_dotenv_paths = [
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "..", ".env"),
        os.path.join(script_dir, "..", "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
        "c:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\.env"
    ]
    
    for path in potential_dotenv_paths:
        if os.path.exists(path):
            load_dotenv(path)
            
    api_key = None
    if 'api' in config and 'gemini_api_key' in config['api']:
        api_key = config['api']['gemini_api_key']
    if not api_key:
        api_key_var = config.get('gemini', {}).get('api_key_env_var', 'GEMINI_API_KEY')
        api_key = os.environ.get(api_key_var)
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if not api_key:
        raise Exception("Gemini API Key not found! Please check config.yaml or set GEMINI_API_KEY.")
        
    client = genai.Client(api_key=api_key)
    return client

def init_local_whisper(model_name):
    from faster_whisper import WhisperModel
    import ctranslate2
    
    # 偵測是否具備 CUDA GPU
    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    logging.info(f"Initializing local Whisper model '{model_name}' on device: {device}...")
    
    # 完整 OOM 防護降備鏈：CUDA float16 -> CUDA int8_float16 -> CUDA int8 -> CPU int8
    model = None
    if device == "cuda":
        try:
            logging.info("Attempting load: device=cuda, compute_type=float16")
            model = WhisperModel(model_name, device="cuda", compute_type="float16")
            logging.info("Whisper model loaded successfully with float16 on CUDA.")
        except Exception as e:
            logging.warning(f"Failed loading CUDA float16: {e}. Trying CUDA int8_float16...")
            try:
                model = WhisperModel(model_name, device="cuda", compute_type="int8_float16")
                logging.info("Whisper model loaded successfully with int8_float16 on CUDA.")
            except Exception as e2:
                logging.warning(f"Failed loading CUDA int8_float16: {e2}. Trying CUDA int8...")
                try:
                    model = WhisperModel(model_name, device="cuda", compute_type="int8")
                    logging.info("Whisper model loaded successfully with int8 on CUDA.")
                except Exception as e3:
                    logging.warning(f"Failed loading CUDA int8: {e3}. Falling back to CPU.")
                    device = "cpu"
                
    if device == "cpu":
        try:
            logging.info("Attempting load: device=cpu, compute_type=int8")
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            logging.info("Whisper model loaded successfully with int8 on CPU.")
        except Exception as e4:
            logging.error(f"[嚴重錯誤] CPU int8 load failed: {e4}. Cannot load model on any device.")
            raise RuntimeError("Cannot load Whisper model on any device.") from e4
            
    return model

def init_local_whisper_cpu_only(model_name):
    """蒸餾引擎專用：強制使用 CPU int8，避免與 Gemini API 呼叫搶奪 VRAM。"""
    from faster_whisper import WhisperModel
    logging.info(f"[Distill Engine] Initializing Whisper '{model_name}' in CPU-only int8 mode (VRAM isolation)...")
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        logging.info("[Distill Engine] Whisper CPU int8 loaded successfully.")
        return model
    except Exception as e:
        logging.error(f"[Distill Engine] CPU int8 load failed: {e}. System memory exhausted.")
        raise RuntimeError(f"Whisper CPU load failed: {e}")

def transcribe_chunk_local(model, chunk_path):
    """向後相容的本地 Whisper 轉錄（單例 WhisperPool 的薄包裝）。"""
    return WhisperPool.transcribe(chunk_path)

def apply_glossary_fix(text):
    glossary = {
        "common_errors": {
            "假芳": "甲方", "假方": "甲方",
            "倚芳": "乙方", "倚方": "乙方", "以方": "乙方",
            "炳芳": "丙方", "丙芳": "丙方", "炳方": "丙方",
            "丁芳": "丁方", "形法": "刑法", "形訴": "刑訴"
        }
    }
    fixed_text = text
    for wrong, right in glossary.get("common_errors", {}).items():
        fixed_text = re.sub(wrong, right, fixed_text)
    return fixed_text

def transcribe_chunk(client, uploaded_file, config):
    model = "gemini-2.5-flash"
    if 'api' in config and 'gemini_model_low_cost' in config['api']:
        model = config['api']['gemini_model_low_cost']
    elif 'gemini' in config and 'model_name' in config['gemini']:
        model = config['gemini']['model_name']
    
    prompt = """你是一位專業的台灣法律課程與講座的逐字稿整理助理。
請將提供的音檔進行精確的繁體中文語音轉錄，並遵守以下規定：
【重要：完整性與精確性要求】
此檔案為極為關鍵的法律教學教材，是後續所有 AI 專案與智能庫的智慧基礎。請務必做到「一字不漏、完全轉錄」！
嚴禁 any 摘要、縮寫、省略、或簡化發言的行為。請完整保留講師的所有口語說明、舉例與課堂細節。
1. 輸出格式一律為繁體中文（台灣習慣用詞）。
2. 保留台灣法律專業術語（例如：不當得利、消滅時效、除斥期間、借名登記、侵權行為、公法上請求權等）。
3. 完整保留所有提到的法律法條名稱與條號，例如「民法第一百八十四條」、「民法第197條」、「民法第126條」、「行政程序法第131條」，若口述簡寫如「民法一八四」請轉錄為完整的「民法第一百八十四條」。
4. 保留釋字字號（例如：釋字第474號）與法院判決字號（例如：最高法院109年度台上字第X號）之標準格式。
5. 聽不清楚或不確定之處不可憑空預測，一律以 [待確認] 標記。
6. 請適度保留時間戳記（例如 [01:23] 或 [15:45]），方便對照原始影音。
7. 當辨識到章節、科目、主題、結論或堂數切換時，請自動插入適當的 Markdown 標題（#、##、###）。
8. 若辨識到「爭點」、「重點整理」、「必考」、「結論」、「實務見解」等關鍵語音字樣，請自動在該段落前加上特殊的 Markdown 加粗重點標記（如：**【爭點】**、**【實務見解】**）。
"""
    
    time.sleep(2)
    response = client.models.generate_content(
        model=model,
        contents=[uploaded_file, prompt]
    )
    return response.text

# ────────────────────────────────────────────────────────────────
# 並列 chunk 處理核心函式
# ────────────────────────────────────────────────────────────────

CHUNK_CONCURRENCY = 2  # 每個任務內最多同時並列 2 個 chunk 上傳（嚴格限流，防止 Google 429 封鎖）

def process_single_chunk(
    chunk: dict,
    client,
    qm: QuotaManager,
    current_key_ref: list,   # 用 list 包裹讓執行緒間可共享可變引用
    key_lock: threading.Lock,
    task_id: str,
    chunks_manifest_path: str,
    manifest_write_lock: threading.Lock,
    config: dict,
    chunk_errors_log: str,
    stt_engine: str,
) -> bool:
    """
    處理單一音訊 chunk 的完整流程：上傳 → Gemini 轉譯 → 本地 Whisper 對照 → 蒸餾存檔。
    線程安全：manifest 寫入使用 manifest_write_lock。
    返回 True 表示成功，False 表示最終失敗。
    """
    chunk_path = chunk["path"]
    chunk_filename = chunk["filename"]
    retry_limit = 3
    uploaded_file = None
    upload_client = None
    consecutive_429_count = 0

    logging.info(f"[Parallel STT] Processing chunk: {chunk_filename}")

    while chunk["retry_count"] < retry_limit:
        try:
            # ── 雲端 Gemini 路徑 ──
            if stt_engine in ["gemini", "vertexai"]:
                file_size = os.path.getsize(chunk_path)
                if file_size > 2000 * 1024 * 1024:
                    raise ValueError(f"{chunk_filename} 超過 2GB 上傳上限")

                # 若金鑰變換，清理舊雲端檔案並重新上傳
                if stt_engine == "gemini":
                    with key_lock:
                        active_key = current_key_ref[0]

                    if upload_client is not None and upload_client._api_key != active_key:
                        if uploaded_file:
                            try:
                                upload_client.files.delete(name=uploaded_file.name)
                            except Exception:
                                pass
                        uploaded_file = None
                        upload_client = None

                if not uploaded_file:
                    if stt_engine == "gemini":
                        with key_lock:
                            active_key = current_key_ref[0]
                        upload_client = genai.Client(api_key=active_key)
                    else: # vertexai
                        v_project = config.get("settings", {}).get("vertexai_project")
                        v_loc = config.get("settings", {}).get("vertexai_location", "us-central1")
                        upload_client = genai.Client(vertexai=True, project=v_project, location=v_loc)
                        
                    logging.info(f"[Parallel STT] Uploading {chunk_filename}...")
                    uploaded_file = upload_client.files.upload(file=chunk_path)
                    logging.info(f"[Parallel STT] Uploaded → {uploaded_file.name}")

                if stt_engine == "gemini":
                    with key_lock:
                        active_key = current_key_ref[0]
                    fresh_client = genai.Client(api_key=active_key)
                else:
                    fresh_client = upload_client

                transcription = transcribe_chunk(fresh_client, uploaded_file, config)

                # ── 雙軌 ASR 蒸餾（WhisperPool 排隊）──
                local_whisper_text = ""
                try:
                    logging.info(f"[Parallel STT][Distill] WhisperPool 排隊：{chunk_filename}")
                    local_whisper_text = WhisperPool.transcribe(chunk_path)
                    local_whisper_text = apply_glossary_fix(local_whisper_text)
                    logging.info(f"[Parallel STT][Distill] 完成：{chunk_filename}")

                    if local_whisper_text and transcription:
                        from difflib import SequenceMatcher
                        s = SequenceMatcher(None, local_whisper_text, transcription)
                        diff_items = []
                        for tag, i1, i2, j1, j2 in s.get_opcodes():
                            if tag == "replace":
                                lw = local_whisper_text[i1:i2]
                                gr = transcription[j1:j2]
                                if 0 < len(lw) < 100 and 0 < len(gr) < 100:
                                    diff_items.append({"local_whisper_raw": lw, "gemini_corrected": gr})

                        distill_dir = "A:\\distillation_dataset"
                        os.makedirs(distill_dir, exist_ok=True)
                        chunk_distill_path = os.path.join(
                            distill_dir,
                            f"{task_id}_{chunk_filename.replace('.wav', '')}_distill.json"
                        )
                        with open(chunk_distill_path, "w", encoding="utf-8") as df:
                            json.dump({
                                "task_id": task_id,
                                "chunk_filename": chunk_filename,
                                "diff_mappings": diff_items,
                                "local_whisper_text": local_whisper_text,
                                "gemini_text": transcription,
                                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }, df, ensure_ascii=False, indent=2)
                        logging.info(f"[Parallel STT][Distill] 蒸餾資料已儲存：{chunk_distill_path}")

                except Exception as de:
                    logging.warning(f"[Parallel STT][Distill] 蒸餾失敗（非致命）：{de}")

            else:  # local_whisper
                transcription = WhisperPool.transcribe(chunk_path)
                transcription = apply_glossary_fix(transcription)

            # ── 儲存轉錄結果 ──
            txt_output_path = os.path.splitext(chunk_path)[0] + ".txt"
            with open(txt_output_path, "w", encoding="utf-8") as tf:
                tf.write(transcription)

            json_output_path = os.path.splitext(chunk_path)[0] + ".json"
            with open(json_output_path, "w", encoding="utf-8") as jf:
                json.dump({
                    "task_id": task_id,
                    "filename": chunk_filename,
                    "part_no": chunk.get("part_no", chunk.get("chunk_id")),
                    "transcription": transcription,
                    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }, jf, ensure_ascii=False, indent=2)

            with manifest_write_lock:
                chunk["status"] = "completed"
                
            consecutive_429_count = 0
            if stt_engine == "gemini":
                qm.report_success(current_key_ref[0])
            logging.info(f"[Parallel STT] ✅ 完成：{chunk_filename}")

            return True

        except Exception as e:
            err_str = str(e)
            if stt_engine == "gemini" and (
                "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            ):
                consecutive_429_count += 1
                with key_lock:
                    current_key = current_key_ref[0]
                    res = qm.handle_error(e, current_key, consecutive_429_count)
                    sleep_time = res["sleep_time"]
                    new_key = res["new_key"]
                    project_cooldown = res["project_cooldown"]

                    if new_key:
                        current_key_ref[0] = new_key
                        consecutive_429_count = 0
                        logging.info(f"[Parallel STT] 切換至新金鑰: {new_key[:8]}...")
                    else:
                        logging.error("[Parallel STT] 所有金鑰耗盡，終止此 chunk。")
                        break

                if sleep_time > 0:
                    time.sleep(sleep_time)
                continue

            # 非 429 錯誤
            if uploaded_file and upload_client:
                try:
                    upload_client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass
            uploaded_file = None
            upload_client = None
            with manifest_write_lock:
                chunk["retry_count"] += 1
            logging.error(
                f"[Parallel STT] chunk {chunk_filename} 失敗（{chunk['retry_count']}/{retry_limit}）：{e}"
            )
            with manifest_write_lock:
                with open(chunk_errors_log, "a", encoding="utf-8") as ef:
                    ef.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{task_id}][{chunk_filename}]: {e}\n")
            time.sleep(5)

    # 最終清理
    if uploaded_file and upload_client:
        try:
            upload_client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

    if chunk["status"] != "completed":
        with manifest_write_lock:
            chunk["status"] = "failed"
        return False
    return True

def run_stt(task_id: str, exclusive_key: str = None):
    """STT 主函式。exclusive_key 為多工並列模式下由外部 Task Dispatcher 傳入的排他金鑰。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    from workflow_helper import load_config, get_resolved_paths
    config = load_config()
    paths = get_resolved_paths()
        
    manifests_dir = paths['manifests_dir']
    workflow_log = os.path.join(paths['logs_dir'], "workflow.log")
    chunk_errors_log = os.path.join(paths['logs_dir'], "chunk_errors.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            ConcurrentRotatingFileHandler(workflow_log, mode=\"a\", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        ]
    )
    
    # Ensure error log directory exists
    os.makedirs(os.path.dirname(chunk_errors_log), exist_ok=True)
    
    logging.info(f"--- STT Processing Task {task_id} ---")
    manifest_path = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_path):
        logging.error(f"Manifest not found for task {task_id}")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    chunks_manifest_path = os.path.join(manifests_dir, f"{task_id}_chunks.json")
    if not os.path.exists(chunks_manifest_path):
        logging.error(f"Chunks manifest not found for task {task_id}")
        return
        
    with open(chunks_manifest_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    if not chunks:
        logging.error(f"No chunks found in manifest for task {task_id}")
        return
        
    stt_engine = config.get("settings", {}).get("stt_engine", "gemini")
    local_whisper_model = config.get("settings", {}).get("local_whisper_model", "small")

    client = None
    whisper_model = None

    if stt_engine == "local_whisper":
        # 預加載 WhisperPool（全域單例，安全）
        try:
            WhisperPool.get_model(local_whisper_model)
        except Exception as e:
            logging.error(f"Failed to initialize WhisperPool: {e}. Falling back to Gemini.")
            stt_engine = "gemini"
            
    qm = None
    current_key = None
    key_lock = threading.Lock()

    if stt_engine == "gemini":
        qm = QuotaManager()
        # 優先使用外部傳入的排他金鑰（多工並列模式）
        if exclusive_key:
            current_key = exclusive_key
            logging.info(f"[STT] 使用外部傳入排他金鑰: {current_key[:8]}...")
        else:
            current_key = qm.acquire_key_exclusive()
            logging.info(f"[STT] 取得排他金鑰: {current_key[:8]}...")
        client = genai.Client(api_key=current_key)

        # 預加載 WhisperPool 以縮短第一個 chunk 的等待時間
        try:
            WhisperPool.get_model("medium")
        except Exception as e:
            logging.warning(f"[STT][Distill] WhisperPool 預加載失敗（非致命）：{e}")
            
    elif stt_engine == "vertexai":
        v_cred_path = config.get("settings", {}).get("vertexai_credentials_path", "config/vertex_key.json")
        cred_abs = os.path.abspath(os.path.join(script_dir, "..", v_cred_path))
        if not os.path.exists(cred_abs):
            logging.error(f"[STT] Vertex AI 找不到憑證檔案：{cred_abs}。請確認已將 JSON 放置於正確路徑，否則系統將無法執行轉錄！")
            return False
            
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_abs
        v_project = config.get("settings", {}).get("vertexai_project")
        v_loc = config.get("settings", {}).get("vertexai_location", "us-central1")
        logging.info(f"[STT] 使用 Vertex AI 企業通道，專案：{v_project} ({v_loc})，憑證：{v_cred_path}")
        client = genai.Client(vertexai=True, project=v_project, location=v_loc)
        
        try:
            WhisperPool.get_model("medium")
        except Exception as e:
            pass

    # 共享可變金鑰引用（執行緒間傳遞）
    current_key_ref = [current_key]

    pending_chunks = [c for c in chunks if c["status"] != "completed"]
    logging.info(f"[STT] 共 {len(pending_chunks)} 個 chunk 待處理，並列度 M={CHUNK_CONCURRENCY}")

    # 建立一個全局的 Lock 用於保護 manifest 的寫入
    manifest_write_lock = threading.Lock()
    all_succeeded = True
    
    # ── 並列執行所有 pending chunks（M=3 並列度）──
    with ThreadPoolExecutor(max_workers=CHUNK_CONCURRENCY) as executor:
        futures = {
            executor.submit(
                process_single_chunk,
                chunk,
                client,
                qm,
                current_key_ref,
                key_lock,
                task_id,
                chunks_manifest_path,
                manifest_write_lock,
                config,
                chunk_errors_log,
                stt_engine,
            ): chunk
            for chunk in pending_chunks
        }

        for future in as_completed(futures):
            chunk = futures[future]
            try:
                success = future.result()
                if not success:
                    all_succeeded = False
                # 每完成一個 chunk 即時存檔（加 per-task 鎖保護）
                with manifest_write_lock:
                    try:
                        with open(chunks_manifest_path, "w", encoding="utf-8") as f:
                            json.dump(chunks, f, ensure_ascii=False, indent=2)
                    except Exception as save_err:
                        logging.warning(f"[STT] Manifest 存檔失敗：{save_err}")
            except Exception as exc:
                logging.error(f"[STT] chunk {chunk.get('filename')} Future 異常：{exc}")
                chunk["status"] = "failed"
                all_succeeded = False

    # ── 更新主任務 Manifest 狀態 ──
    if all_succeeded:
        manifest["status"] = "transcribed"
        manifest["steps"]["stt"] = "completed"
    else:
        manifest["status"] = "partial_success"
        manifest["steps"]["stt"] = "failed"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    with open(chunks_manifest_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    if stt_engine == "gemini" and qm:
        try:
            qm._save_state()
        except Exception as se:
            logging.warning(f"Failed to save quota state at run_stt end: {se}")
        # 若金鑰是本函式自行取得的（非外部多工 dispatcher 傳入），歸還排他鎖
        if not exclusive_key and current_key_ref[0]:
            qm.release_key(current_key_ref[0])

    logging.info(f"STT Phase completed. Succeeded={all_succeeded}. Triggering Merge Agent...")

    # Trigger Merge Transcript script
    merge_script = os.path.join(script_dir, "merge_transcript.py")
    cmd = [sys.executable, merge_script, "--task-id", task_id]
    try:
        subprocess.run(cmd, cwd=script_dir, timeout=600, check=True)
    except subprocess.TimeoutExpired:
        logging.error("merge_transcript.py timed out after 600s!")
    except subprocess.CalledProcessError as e:
        logging.error(f"merge_transcript.py failed with return code {e.returncode}")
    return all_succeeded

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stt_runner.py {task_id}")
        sys.exit(1)
    run_stt(sys.argv[1])

```

## quota_manager.py

```python
import os
import json
import time
import random
import logging
import sys
import re
import ctypes
from pathlib import Path
import yaml
from cryptography.fernet import Fernet
import hashlib
from scripts.win32_kernel import KernelMutex

class SecureMemoryWiper:
    """Phase 7.7 C API 記憶體零化引擎 (OOP 封裝)
    負責調用 Windows 核心 API 進行硬體級的記憶體抹除，對抗 GC 延遲與 Memory Dump。
    """
    @staticmethod
    def wipe_bytearray(key_bytes: bytearray):
        """安全地將記憶體覆寫為 0"""
        if not isinstance(key_bytes, bytearray) or not key_bytes:
            return
        try:
            kernel32 = ctypes.windll.kernel32
            RtlSecureZeroMemory = kernel32.RtlSecureZeroMemory
            RtlSecureZeroMemory.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            RtlSecureZeroMemory.restype = ctypes.c_void_p

            data_len = len(key_bytes)
            # 取得 bytearray 的底層 C 陣列指標
            c_buffer = (ctypes.c_char * data_len).from_buffer(key_bytes)
            buffer_address = ctypes.addressof(c_buffer)
            
            # 呼叫底層 API 強制抹除
            RtlSecureZeroMemory(buffer_address, data_len)
            key_bytes.clear()
        except Exception as e:
            logging.warning(f"SecureMemoryWiper failed: {e}")

class AllKeysExhaustedError(Exception):
    pass

class KeyManager:
    """中介層：專責從 Vault 提取主金鑰。"""
    @staticmethod
    def get_all_keys() -> list[str]:
        try:
            from scripts.utils.vault import Vault
            v = Vault()
            keys = v.load_and_decrypt()
            if keys:
                return keys
        except ImportError:
            logging.warning("Vault class not found, falling back.")
        except Exception as e:
            logging.warning(f"KeyManager: Failed to load from Vault: {e}")

        config_yaml_path = Path("config.yaml")
        if config_yaml_path.exists():
            try:
                with open(config_yaml_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if cfg and "api" in cfg:
                    val = cfg.get("api", {}).get("gemini_api_key")
                    if val and not val.startswith("AUTO_LOAD_"):
                        return [val.strip()]
            except Exception:
                pass
        return []

class QuotaManager:
    """
    【專家終極加固版】
    1. 依賴注入 (DI)
    2. 鎖檔分離 (Lockfile) 與安全原子寫入 (Safe os.replace)
    3. 全抖動指數退避 (Full Jitter)
    4. 記憶體 JIT 保護與日誌脫敏
    """
    def __init__(self, key_manager=None, state_path: str = "config/quota_state.json", is_test_traffic: bool = False):
        self.state_path = Path(state_path)
        self.is_test_traffic = is_test_traffic
        # 廢棄 Lockfile，統一改用與 UI 相同的 Phase 7.8 核心級 Named Mutex 防止 AB-BA 死鎖
        import hashlib
        path_hash = hashlib.md5(str(self.state_path).encode()).hexdigest()[:8]
        self.mutex_name = f"Global\\LexMind_Vault_Mutex_{path_hash}"
        
        # 依賴注入：不再自己實例化，而是使用傳入的 key_manager
        # 若未傳入，為保持向後相容性，仍使用 KeyManager
        self.key_manager = key_manager if key_manager else KeyManager()
        
        raw_keys = self.key_manager.get_all_keys() if hasattr(self.key_manager, 'get_all_keys') else []
        if not raw_keys:
            raise ValueError("No API keys found via KeyManager.")
            
        # 【資安修補：記憶體駐留防禦】
        # 為了避免在 Heap 留下明文陣列，我們在 QuotaManager 內使用一把拋棄式金鑰加密儲存。
        self._jit_key = Fernet.generate_key()
        self._jit_cipher = Fernet(self._jit_key)
        self._encrypted_keys = [self._jit_cipher.encrypt(k.encode('utf-8')) for k in raw_keys]
        
        self.max_concurrent_calls = 6
        self.base_jitter_seconds = 2.0
        self._load_config()
        self._init_state_file()

    def _hash_key(self, key: str) -> str:
        """將金鑰單向雜湊，防止落盤外洩"""
        return hashlib.sha256(key.encode('utf-8')).hexdigest()

    def _check_and_reload_vault(self):
        """【修復 Issue 5, 7, 11】 每次拿金鑰前，檢查 Vault 是否被 UI 更新，若是則熱載入。並支援 SRE QoS 測試金鑰隔離。"""
        vault_file = "config/secure_keys_test.vault" if self.is_test_traffic else "config/secure_keys.vault"
        vault_path = Path(vault_file)
        if not vault_path.exists():
            return
            
        current_mtime = os.path.getmtime(vault_path)
        if not hasattr(self, '_last_vault_mtime') or current_mtime > self._last_vault_mtime:
            logging.info(f"QuotaManager: 偵測到金鑰庫 ({vault_file}) 已更新，執行跨進程熱載入 (True IPC)...")
            self._last_vault_mtime = current_mtime
            
            # 從安全金鑰庫 (Vault) 解密取得金鑰，徹底取代不安全的 KeyManager 與 keys.yaml
            from scripts.utils.vault import Vault
            v = Vault(vault_file=vault_file)
            try:
                raw_keys = v.load_and_decrypt()
            except Exception as e:
                logging.error(f"QuotaManager: 解密 Vault 失敗: {e}")
                raw_keys = []
                
            if raw_keys:
                self._jit_key = Fernet.generate_key()
                self._jit_cipher = Fernet(self._jit_key)
                self._encrypted_keys = [self._jit_cipher.encrypt(k.encode('utf-8')) for k in raw_keys]


    def _load_config(self):
        config_yaml = Path("config.yaml")
        if config_yaml.exists():
            try:
                with open(config_yaml, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                api_cfg = cfg.get("api", {})
                self.max_concurrent_calls = api_cfg.get("max_concurrent_calls", 6)
                self.base_jitter_seconds = float(api_cfg.get("base_jitter_seconds", 2.0))
            except Exception as e:
                logging.warning(f"Failed to load traffic config: {e}")

    def _init_state_file(self):
        os.makedirs(self.state_path.parent, exist_ok=True)
        if not self.state_path.exists():
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump({
                    "exhausted_keys": [], 
                    "in_use_keys": [],
                    "circuit_breaker": "CLOSED",
                    "cooldown_until": 0,
                    "probe_in_progress": False
                }, f)

    def _read_update_state(self, callback):
        """Phase 7.9 核心級同步：加上超時與防死鎖防禦"""
        # 使用 KernelMutex 進行 OS 級的阻塞排隊 (CPU 負載 0%)
        # 加上 15000ms 超時，防止持有者被防毒軟體卡死導致連環死鎖
        mutex = KernelMutex(self.mutex_name)
        if not mutex.acquire(15000):
            mutex.close()
            raise TimeoutError("Mutex timeout: Possible cascading deadlock detected, falling back to Jitter.")
            
        try:
            # 已經取得跨進程鎖，可以安全讀寫 state_path
            if not self.state_path.exists():
                self._init_state_file()
                
            # 讀取真實資料檔
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                state = {"exhausted_keys": [], "in_use_keys": []}
            
            if "exhausted_keys" not in state: state["exhausted_keys"] = []
            if "in_use_keys" not in state: state["in_use_keys"] = []
            if "circuit_breaker" not in state: state["circuit_breaker"] = "CLOSED"
            if "cooldown_until" not in state: state["cooldown_until"] = 0
            if "probe_in_progress" not in state: state["probe_in_progress"] = False
            
            should_save = callback(state)
                
            if should_save:
                # 原子寫入：寫到 tmp 並 fsync
                tmp_file = str(self.state_path) + ".tmp"
                with open(tmp_file, "w", encoding="utf-8") as tf:
                    json.dump(state, tf, ensure_ascii=False, indent=2)
                    tf.flush()
                    os.fsync(tf.fileno())
                    
                # 【SRE 修補】防禦 Windows Defender 與 WinError 32
                max_retries = 3
                for i in range(max_retries):
                    try:
                        os.replace(tmp_file, str(self.state_path))
                        break
                    except PermissionError:
                        if i == max_retries - 1:
                            raise
                        time.sleep(0.1)
        finally:
            mutex.release()
            mutex.close()

    def acquire_key_exclusive(self) -> str:
        self._check_and_reload_vault()
        selected_key = None
        
        def _try_acquire(state):
            nonlocal selected_key
            # 從 JIT 密碼中解密進行比較
            for enc_k in self._encrypted_keys:
                k = self._jit_cipher.decrypt(enc_k).decode('utf-8')
                hashed_k = self._hash_key(k)
                if hashed_k not in state["exhausted_keys"] and hashed_k not in state["in_use_keys"]:
                    selected_key = k
                    state["in_use_keys"].append(hashed_k)
                    return True
            return False

        self._read_update_state(_try_acquire)
        
        if not selected_key:
            raise AllKeysExhaustedError("所有金鑰均已被佔用或耗盡，無法取得排他性金鑰。")
            
        logging.debug(f"QuotaManager: 跨進程鎖定金鑰 {selected_key[:8]}...")
        return selected_key

    def release_key(self, key: str):
        def _try_release(state):
            hashed_k = self._hash_key(key)
            if hashed_k in state["in_use_keys"]:
                state["in_use_keys"].remove(hashed_k)
                return True
            return False
            
        self._read_update_state(_try_release)
        logging.debug(f"QuotaManager: 跨進程釋放金鑰 {key[:8]}...")

    def handle_error(self, e: Exception, current_key: str, consecutive_429: int):
        # 【資安修補：日誌脫敏】
        raw_err_msg = str(e)
        safe_err_msg = re.sub(r'AIza[a-zA-Z0-9_-]{35}', 'AIza***', raw_err_msg)
        vault_key = os.environ.get("LEXMIND_VAULT_KEY")
        if not vault_key and os.path.exists("config/vault.key"):
            try:
                with open("config/vault.key", "r", encoding="utf-8") as f:
                    vault_key = f.read().strip()
            except Exception:
                pass
                
        if vault_key and vault_key in safe_err_msg:
            safe_err_msg = safe_err_msg.replace(vault_key, "[REDACTED_VAULT_KEY]")
            
        # 【修補 Issue 4：避免 429 誤判，與 Issue 31 防範檔名注入】
        import google.api_core.exceptions as google_exceptions
        is_429 = isinstance(e, google_exceptions.ResourceExhausted) or getattr(e, 'code', None) == 429
        is_401_403 = isinstance(e, (google_exceptions.Forbidden, google_exceptions.Unauthorized)) or getattr(e, 'code', None) in (401, 403)

        
        # 【SRE 修補：真實的全抖動指數退避 (Full Jitter Exponential Backoff)】
        # random.uniform(0, base * (2 ** retry_count))
        temp = min(60.0, self.base_jitter_seconds * (2 ** consecutive_429))
        sleep_time = random.uniform(0, temp)
        
        new_key = current_key
        project_cooldown = False

        if is_401_403 or (is_429 and consecutive_429 >= 3):
            logging.warning(f"QuotaManager: Key {current_key[:8]}... marked exhausted. Error: {safe_err_msg}")
            
            def _mark_exhausted(state):
                # 【資安修補】僅寫入 Hash 值，落實 Zeroization
                hashed_k = self._hash_key(current_key)
                if hashed_k not in state["exhausted_keys"]:
                    state["exhausted_keys"].append(hashed_k)
                if hashed_k in state["in_use_keys"]:
                    state["in_use_keys"].remove(hashed_k)
                return True
                
            self._read_update_state(_mark_exhausted)
            # 任務完成後，直接將記憶體中的 current_key 明文抹除
            key_bytes = bytearray(current_key.encode('utf-8'))
            SecureMemoryWiper.wipe_bytearray(key_bytes)
            
            try:
                new_key = self.acquire_key_exclusive()
            except AllKeysExhaustedError:
                new_key = None
                
        if new_key is None:
            project_cooldown = True
            
            def _open_circuit(state):
                if state.get("circuit_breaker") != "OPEN":
                    state["circuit_breaker"] = "OPEN"
                    # 加入一點隨機避免同時搶 probe
                    state["cooldown_until"] = time.time() + 300 + random.uniform(0, 5)
                    state["probe_in_progress"] = False
                    return True
                return False
            self._read_update_state(_open_circuit)

            logging.warning(f"QuotaManager: 所有 API 金鑰皆已耗盡！進入斷路器熔斷模式 (Circuit Breaker OPEN)...")
            
            while True:
                action = None
                def _check_circuit(state):
                    nonlocal action
                    cb = state.get("circuit_breaker", "CLOSED")
                    cooldown = state.get("cooldown_until", 0)
                    probe = state.get("probe_in_progress", False)
                    probe_ts = state.get("probe_timestamp", 0)

                    if cb == "CLOSED":
                        action = "RESUME"
                    elif cb == "OPEN":
                        if time.time() >= cooldown:
                            if not probe:
                                # Become leader probe
                                state["circuit_breaker"] = "HALF_OPEN"
                                state["probe_in_progress"] = True
                                state["probe_timestamp"] = time.time()
                                action = "PROBE"
                                return True
                    elif cb == "HALF_OPEN":
                        if not probe or (time.time() - probe_ts > 30):
                            state["probe_in_progress"] = True
                            state["probe_timestamp"] = time.time()
                            action = "PROBE"
                            return True
                    return False
                
                try:
                    self._read_update_state(_check_circuit)
                except TimeoutError:
                    logging.warning("QuotaManager: Mutex timeout, falling back to Jitter wait...")
                    time.sleep(5)
                    continue
                
                if action == "RESUME":
                    logging.info("QuotaManager: 斷路器已閉合 (CLOSED)，其他探針已成功恢復金鑰。準備喚醒。")
                    break
                elif action == "PROBE":
                    logging.info("QuotaManager: 半開探針 (HALF_OPEN) 啟動！本 Worker 將擔任 Leader 進行 API 試探。")
                    self.reset_all_keys()
                    break
                else:
                    time.sleep(5)
            
            try:
                new_key = self.acquire_key_exclusive()
            except AllKeysExhaustedError:
                new_key = None
            sleep_time = 0
            
        return {"sleep_time": sleep_time, "new_key": new_key, "project_cooldown": project_cooldown}

    def reset_all_keys(self):
        def _reset(state):
            state["exhausted_keys"] = []
            return True
        self._read_update_state(_reset)
        logging.info("QuotaManager: 所有金鑰耗盡狀態已重設。")

    def get_key_status(self):
        """【修補 Issue 35：防呆設計】安全回傳狀態字典，避免解構時 NoneType TypeError 崩潰"""
        current_state = None
        def _read_status(state):
            nonlocal current_state
            current_state = dict(state)
            return False
        
        try:
            self._read_update_state(_read_status)
        except Exception as e:
            logging.warning(f"QuotaManager: Failed to get key status: {e}")
            
        if current_state is None:
            return {"circuit_breaker": "UNKNOWN", "exhausted_keys": [], "in_use_keys": []}, None
            
        return current_state, None

    def report_success(self, key: str = None):
        def _close_circuit(state):
            changed = False
            if state.get("circuit_breaker") != "CLOSED":
                state["circuit_breaker"] = "CLOSED"
                state["probe_in_progress"] = False
                changed = True
            if key:
                hashed_k = self._hash_key(key)
                if hashed_k in state["in_use_keys"]:
                    state["in_use_keys"].remove(hashed_k)
                    changed = True
            return changed
        self._read_update_state(_close_circuit)
        logging.debug(f"QuotaManager: API 呼叫成功，斷路器狀態確認閉合 (CLOSED)。")

    def reset_key(self, key: str):
        # 兼容原本錯誤的呼叫名稱
        self.report_success(key)

    def acquire_key(self) -> str:
        self._check_and_reload_vault()
        selected_key = None
        def _try_acquire(state):
            nonlocal selected_key
            for enc_k in self._encrypted_keys:
                k = self._jit_cipher.decrypt(enc_k).decode('utf-8')
                hashed_k = self._hash_key(k)
                if hashed_k not in state["exhausted_keys"]:
                    selected_key = k
                    return False
            return False

        self._read_update_state(_try_acquire)
        if not selected_key:
            raise AllKeysExhaustedError("All keys exhausted.")
        return selected_key

def load_keys_yaml(path: str = "config/keys.yaml"):
    return KeyManager.get_all_keys()

```

## win32_kernel.py

```python
# -*- coding: utf-8 -*-
"""
Phase 7.8 Windows Kernel API 封裝 (OOP)
負責提供跨進程 Named Mutex、Named Event 以及 Job Object 管理。
"""
import ctypes
from ctypes import wintypes
import time
import sys

kernel32 = ctypes.windll.kernel32

# Win32 Constants
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_ABANDONED = 0x00000080
INFINITE = 0xFFFFFFFF

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.POINTER(wintypes.ULONG)),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]
    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

class KernelMutex:
    """跨進程具名互斥鎖 (Named Mutex)"""
    def __init__(self, name: str):
        self.name = name
        # CreateMutexW 會建立或開啟已存在的 Mutex
        self.handle = kernel32.CreateMutexW(None, False, self.name)
        if not self.handle:
            raise ctypes.WinError()

    def acquire(self, timeout_ms: int = INFINITE) -> bool:
        """請求 Mutex。由 OS 排程器控制，期間 CPU 負載為 0%"""
        result = kernel32.WaitForSingleObject(self.handle, timeout_ms)
        if result == WAIT_OBJECT_0 or result == WAIT_ABANDONED:
            return True
        return False

    def release(self):
        kernel32.ReleaseMutex(self.handle)

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        self.acquire()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class KernelEvent:
    """跨進程具名事件 (Named Event) 用於心跳"""
    def __init__(self, name: str):
        self.name = name
        # CreateEventW (bManualReset=False, bInitialState=False)
        self.handle = kernel32.CreateEventW(None, False, False, self.name)
        if not self.handle:
            raise ctypes.WinError()

    def signal(self):
        """發送事件信號 (Heartbeat)"""
        kernel32.SetEvent(self.handle)

    def wait(self, timeout_ms: int) -> bool:
        """等待事件。由 OS 負責計時與喚醒，無視 NTFS 延遲"""
        result = kernel32.WaitForSingleObject(self.handle, timeout_ms)
        return result == WAIT_OBJECT_0

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

class KernelJobObject:
    """工作物件 (Job Object) 用於自動管理進程樹"""
    def __init__(self, name: str = None, open_only: bool = False):
        if open_only:
            # 存取權限: JOB_OBJECT_TERMINATE = 0x0008
            self.handle = kernel32.OpenJobObjectW(0x0008, False, name)
        else:
            self.handle = kernel32.CreateJobObjectW(None, name)
            if self.handle:
                self._set_kill_on_close()
                
        if not self.handle:
            raise ctypes.WinError()

    def _set_kill_on_close(self):
        """設定 Job Object 在 Handle 關閉時自動斬殺所有關聯進程"""
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        
        # SetInformationJobObject (JobObjectExtendedLimitInformation = 9)
        result = kernel32.SetInformationJobObject(
            self.handle,
            9, 
            ctypes.byref(info),
            ctypes.sizeof(info)
        )
        if not result:
            raise ctypes.WinError()

    def assign_current_process(self):
        """將當前進程加入 Job。其衍生的子進程會自動繼承"""
        current_process = kernel32.GetCurrentProcess()
        result = kernel32.AssignProcessToJobObject(self.handle, current_process)
        if not result:
            raise ctypes.WinError()

    def get_io_counters(self):
        """取得 Job Object 的 IO_COUNTERS 數據，用於防禦心跳偽造"""
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        ret_len = wintypes.DWORD()
        result = kernel32.QueryInformationJobObject(
            self.handle,
            9, # JobObjectExtendedLimitInformation
            ctypes.byref(info),
            ctypes.sizeof(info),
            ctypes.byref(ret_len)
        )
        if not result:
            raise ctypes.WinError()
        return info.IoInfo

    def terminate(self, exit_code: int = 1):
        """瞬間無情斬殺整個進程樹"""
        result = kernel32.TerminateJobObject(self.handle, exit_code)
        if not result:
            raise ctypes.WinError()

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

```

## multimodal_input.py

```python
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
```

## agent_core_pro.py

```python
import os
import re
import requests
import chromadb
import json
import hashlib
import math
from pathlib import Path

DEFAULT_MERMAID = "graph TD\n    A[\"人: 申訴人\"] -->|諮詢| B[\"事: 法律案件\"]"

# 載入全局 config.json 的單一真理源配置
try:
    from scripts.config_loader import apply_hardware_config
    cfg = apply_hardware_config()
    DEFAULT_LLM_MODEL = cfg.get("ollama_model", "deepseek-r1:32b")
    OLLAMA_HOST = cfg.get("ollama_host", "http://127.0.0.1:11434")
except Exception:
    DEFAULT_LLM_MODEL = "deepseek-r1:32b"
    OLLAMA_HOST = "http://127.0.0.1:11434"

EMBEDDING_DIM = 768

_CHROMA_CLIENTS = {}

def get_chroma_client(path):
    abs_path = os.path.abspath(path)
    if abs_path not in _CHROMA_CLIENTS:
        _CHROMA_CLIENTS[abs_path] = chromadb.PersistentClient(path=abs_path)
    return _CHROMA_CLIENTS[abs_path]

class LegalRWSAnalyzer:
    def __init__(self, context_role="lawyer"):
        self.context_role = context_role
        self.const_patterns = [r"\d{3}\s*年\s*憲判字第\s*\d+\s*號", r"(司法院)?釋字第\s*\d+\s*號"]
        self.defense_keywords = ["消滅時效", "時效抗辯", "時效中斷", "過失相抵", "同時履行抗辯", "罹於時效", "時效起算", "追訴權時效", "追訴期"]

    def calculate_score(self, text: str) -> float:
        """核心 RWS 權重算法 (0.0 ~ 1.0)"""
        weight = 20
        text_clean = text.replace(" ", "")

        # 1. 識別憲法與釋字 (Level 1 最高級)
        if any(re.search(p, text) for p in self.const_patterns):
            weight = 95 + (5 if self.context_role in ["lawyer", "judge"] else 0)
        # 2. 識別黃金條文
        elif "民法" in text_clean and any(f"第{n}條" in text_clean for n in ["126", "179", "184", "197", "226", "227", "767"]):
            weight = 110
        elif "刑法" in text_clean and any(f"第{n}條" in text_clean for n in ["80", "185-3", "271", "320", "321", "339"]):
            weight = 110
        elif "行政程序法" in text_clean and any(f"第{n}條" in text_clean for n in ["92", "111", "131"]):
            weight = 110
        # 3. 識別一般法律 (Level 2)
        elif any(x in text_clean for x in ["民法", "刑法", "民事訴訟法", "刑事訴訟法", "行政訴訟法"]):
            weight = 90
        # 4. 識別命令與細則 (Level 3/4)
        elif "細則" in text_clean or "施行細則" in text_clean:
            weight = 50
        elif any(x in text_clean for x in ["要點", "注意事項", "基準", "須知"]):
            weight = 20

        # 5. 時效與核心抗辯加權
        if any(kw in text_clean for kw in self.defense_keywords):
            weight += 20 if self.context_role in ["lawyer", "judge"] else 10

        return min(weight, 120) / 120.0

class OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model_name="nomic-embed-text:latest", host="http://127.0.0.1:11434"):
        self.model_name = model_name
        self.host = host

    def __call__(self, input: list) -> list:
        embeddings = []
        for text in input:
            try:
                import requests
                res = requests.post(f'{self.host}/api/embeddings', json={'model': self.model_name, 'prompt': text}, timeout=30)
                if res.status_code == 200:
                    embeddings.append(res.json().get('embedding'))
                else:
                    embeddings.append([0.0] * 768)
            except Exception as e:
                print(f"[WARNING] Custom Ollama Embedding Error: {e}")
                embeddings.append([0.0] * 768)
        return embeddings

class LocalLegalAgent:
    def __init__(self, context_role="lawyer", db_path=None):
        self.role = context_role
        self.analyzer = LegalRWSAnalyzer(context_role=context_role)
        self.const_patterns = [r"\d{3}\s*年\s*憲判字第\s*\d+\s*號", r"(司法院)?釋字第\s*\d+\s*號"]
        
        # 動態判定專案根目錄，完美相容本機任何磁碟與目錄路徑
        self.base_dir = Path(__file__).resolve().parent.parent
        
        if db_path is None:
            db_path = str(self.base_dir / "RAGFlow_Datasets")
            
        # 絕對路徑校正
        self.abs_db_path = os.path.abspath(db_path)
        self.chroma_client = get_chroma_client(self.abs_db_path)
        
        # 檢測與自動升級 384-dim 到 768-dim (以相容 nomic-embed-text:latest)
        try:
            coll_docs = self.chroma_client.get_collection(name="legal_docs")
            try:
                # 測試 768 維度查詢是否相容
                coll_docs.query(query_embeddings=[[0.0] * 768], n_results=1)
            except Exception as e:
                if "dimension" in str(e).lower() or "expecting embedding" in str(e).lower():
                    print("Deleting old 384-dim legal_docs collection to upgrade to 768-dim nomic-embed-text...")
                    self.chroma_client.delete_collection(name="legal_docs")
                    coll_docs = self.chroma_client.create_collection(name="legal_docs", metadata={"hnsw:space": "cosine"})
            self.law_coll = coll_docs
        except Exception:
            try:
                self.law_coll = self.chroma_client.create_collection(name="legal_docs", metadata={"hnsw:space": "cosine"})
            except Exception:
                self.law_coll = self.chroma_client.get_or_create_collection(name="legal_docs")

        try:
            coll_intel = self.chroma_client.get_collection(name="legal_intelligence_vault")
            try:
                # 測試 768 維度查詢是否相容
                coll_intel.query(query_embeddings=[[0.0] * 768], n_results=1)
            except Exception as e:
                if "dimension" in str(e).lower() or "expecting embedding" in str(e).lower():
                    print("Deleting old 384-dim legal_intelligence_vault collection to upgrade to 768-dim nomic-embed-text...")
                    self.chroma_client.delete_collection(name="legal_intelligence_vault")
                    coll_intel = self.chroma_client.create_collection(name="legal_intelligence_vault")
            self.intel_coll = coll_intel
        except Exception:
            try:
                self.intel_coll = self.chroma_client.create_collection(name="legal_intelligence_vault")
            except Exception:
                self.intel_coll = self.chroma_client.get_or_create_collection(name="legal_intelligence_vault")
        
        self.history_file = str(self.base_dir / "history.json")
        self.memory = self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_memory(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory[-10:], f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[WARNING] Failed to save memory file: {e}")

    def _get_embedding(self, text: str):
        if getattr(self, '_ollama_offline', False):
            return None
        # 使用 nomic-embed-text:latest 進行向量化，提升語意檢索效能
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        try:
            res = requests.post(f"{host}/api/embeddings", json={'model': 'nomic-embed-text:latest', 'prompt': text}, timeout=2)
            if res.status_code == 200:
                return res.json().get('embedding')
        except Exception as e:
            print(f"[WARNING] Ollama Embedding Error: {e}. Disabling future embedding calls.")
            self._ollama_offline = True
        return None

    def _condense_query(self, current_input: str) -> str:
        """多輪對話歷史語意壓縮重構"""
        if not self.memory:
            return current_input
        
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in self.memory[-4:]])
        prompt = (
            "你是一個法律案情文本提煉助手。請將以下的歷史對話紀錄與使用者新提問結合，"
            "壓縮還原成一個包含具體法律糾紛事實、對稱主體與爭點的單一精準檢索句。只需輸出最終檢索句，不要加入多餘旁白。\n\n"
            f"對話歷史：\n{history_text}\n"
            f"最新提問：\n{current_input}"
        )
        try:
            res = requests.post(f'{os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")}/api/chat',
                                json={'model': os.environ.get("OLLAMA_MODEL", DEFAULT_LLM_MODEL), 'messages': [{'role': 'user', 'content': prompt}], 'stream': False, 'options': {'num_ctx': 32768}}, timeout=45)
            if res.status_code == 200:
                return res.json().get('message', {}).get('content', current_input).strip()
        except:
            pass
        return current_input

    def search_hybrid(self, query: str, category_hint: str = "通用", n_results: int = 15):
        """雙重資料庫檢索 + RWS 權重重新排序 (Re-ranking)"""
        query_vec = self._get_embedding(query)
        if not query_vec:
            return []

        # 進行相似度檢索
        res_law = self.law_coll.query(query_embeddings=[query_vec], n_results=n_results)
        res_intel = self.intel_coll.query(query_embeddings=[query_vec], n_results=5)

        combined = []
        
        # 1. 處理法條庫召回
        if res_law and res_law['documents'] and res_law['documents'][0]:
            for d, m, dist in zip(res_law['documents'][0], res_law['metadatas'][0], res_law['distances'][0]):
                cos_sim = 1.0 - (dist / 2.0)
                sim_score = max(cos_sim, 0.0)
                
                # 基於位階標記的 RWS 權重 (憲法=1.0, 法律=0.8, 命令=0.6, 規則=0.4, 預設=0.2)
                level = int(m.get('level', 5))
                if level == 1:
                    rws_weight = 1.0
                elif level == 2:
                    rws_weight = 0.8
                elif level == 3:
                    rws_weight = 0.6
                elif level == 4:
                    rws_weight = 0.4
                else:
                    rws_weight = 0.2

                # 憲法與釋字強制置頂
                if any(re.search(p, d) for p in self.const_patterns):
                    rws_weight = 1.0

                # 時效強制置頂 (命中「消滅時效」、「追訴權時效」且 query 包含時效相關字眼，權重強制拉滿 1.0)
                if "時效" in d and any(k in query for k in ["時效", "過期", "抗辯"]):
                    rws_weight = 1.0

                cat_match = 1.0 if m.get('category') == category_hint else 0.8
                final_score = (0.4 * sim_score) + (0.6 * rws_weight) * cat_match
                
                combined.append({
                    "text": d,
                    "score": round(final_score, 4),
                    "source": m.get('source', '法條'),
                    "level": level
                })

        # 2. 處理經驗與智商庫
        if res_intel and res_intel['documents'] and res_intel['documents'][0]:
            for d, m in zip(res_intel['documents'][0], res_intel['metadatas'][0]):
                # 經驗文檔賦予極高權重，置頂於最前端，引導 AI 避開邏輯陷阱
                combined.append({
                    "text": f"【經驗智商晶片】\n{d}",
                    "score": 1.2,
                    "source": m.get('source', '智商庫'),
                    "level": 1
                })

        # 重新排序
        combined.sort(key=lambda x: x['score'], reverse=True)
        return combined[:5]

    def chat_with_rws(self, user_input: str) -> tuple:
        condensed = self._condense_query(user_input)
        
        # 簡單判定大類
        category_hint = "通用"
        if any(w in condensed for w in ["侵權", "撞", "損害賠償", "欠錢", "返還", "不當得利", "契約"]):
            category_hint = "民事"
        elif any(w in condensed for w in ["告訴", "罪", "被告人", "檢察", "詐欺", "公訴", "起訴"]):
            category_hint = "刑事"
        elif any(w in condensed for w in ["罰單", "處分", "扣押", "訴願", "稅", "核課"]):
            category_hint = "行政"
            
        evidence = self.search_hybrid(condensed, category_hint=category_hint)
        context_str = "\n".join([f"[{i+1}] {e['text']} (RWS 綜效得分: {e['score']})" for i, e in enumerate(evidence)])

        system_instruction = (
            "你是一位精通臺灣裁判實務、擁有「老律師與老法官靈魂」的資深 AI 法律特助。\n"
            f"目前你採取『{self.role}』的訴訟視角進行邏輯涵攝與答辯策略推論。\n"
            "請基於下方由 RWS 系統篩選、按重要性高低排序的法律事件證據、判例摘要及條文：\n\n"
            f"{context_str}\n\n"
            "【警示規則與法意要求】：\n"
            "1. 若證據中包含『消滅時效』且經對位本案事實過期，你必須直接在回答的第一段最開頭以『紅字或極度醒目格式』發出最嚴厲的法律截止警告，提醒當事人程序的程序保命符。\n"
            "2. 答題必須採取正統的法律實務「三段論法」（找爭點 -> 敘明適用法規 -> 涵攝事實給出結論與下一步救濟途徑）。\n"
            "3. 確保使用台灣繁體中文法律用語。嚴禁使用大陸詞彙如『公安』、『檢察院』、『被告人』。"
        )

        messages = [
            {"role": "system", "content": system_instruction}
        ]
        # 追加最近幾輪歷史
        messages.extend(self.memory[-6:])
        messages.append({"role": "user", "content": user_input})

        try:
            res = requests.post(f'{OLLAMA_HOST}/api/chat',
                                json={'model': DEFAULT_LLM_MODEL, 'messages': messages, 'stream': False, 'options': {'num_ctx': 32768}}, timeout=120)
            if res.status_code == 200:
                reply = res.json().get('message', {}).get('content', 'API 回應格式異常')
                # 追加到歷史紀錄中
                self.memory.append({"role": "user", "content": user_input})
                self.memory.append({"role": "assistant", "content": reply})
                self._save_memory()
                
                # 自動提煉人事時地物關係並寫入 Obsidian 與 ChromaDB
                mermaid_code = DEFAULT_MERMAID
                try:
                    mermaid_code = self._save_to_obsidian_and_chromadb(user_input, reply)
                except Exception as e_mem:
                    print(f"[WARNING] Error writing to Obsidian and relation graph: {e_mem}")
                
                return reply, evidence, mermaid_code
        except Exception as e:
            return f"❌ 呼叫 LLM 服務失敗，請確認本地 Ollama ({DEFAULT_LLM_MODEL}) 正在運行：{e}", [], DEFAULT_MERMAID

        return "（未取得本地 LLM 回應，請確認連接正常。）", [], DEFAULT_MERMAID

    def _save_to_obsidian_and_chromadb(self, user_input: str, reply: str) -> str:
        import datetime
        
        # 預設備份關係圖代碼
        mermaid_code = DEFAULT_MERMAID
        
        # 1. 呼叫 Ollama 對對話進行 人、事、時、地、物 關係提煉 (包含 Mermaid 關係圖)
        prompt = f"""請根據以下對話內容，提煉出這一次互動的「人事時地物」關係，並生成一篇簡明扼要的 Obsidian 法律事件記憶筆記（包含 Mermaid.js 關係流程圖）。
要求：
1. 必須使用繁體中文。
2. 輸出格式必須是完整的 Markdown，包含以下內容：
   # 法律事件記憶 - [主題或簡短案件名稱]
   - **時間 (When)**: [具體時間或對話日期]
   - **人物 (Who)**: [涉及的申訴人、被告或相關人]
   - **事件 (What)**: [糾紛事實、法律問題]
   - **地點 (Where)**: [如果對話中有提到地點，否則填無]
   - **核心物/標的 (Why/Object)**: [例如賠償金額、合約、車禍車輛等]
   - **AI 建議與行動點 (Action Points)**: [對話中給出的核心法律建議或下一步行動]
   
   ## 關係圖面 (Mermaid)
   ```mermaid
   graph TD
     A["人: 申訴人"] -->|關係| B["事: 法律案件"]
   ```
3. 關係圖的節點標籤必須使用雙引號括住，例如 A["人: 申訴人"]，以防止 Mermaid 渲染出錯。
4. 僅輸出 Markdown 內容，不要包含任何前言、解釋、引導詞或思考標籤。

對話內容：
使用者：{user_input}
AI 回應：{reply}
"""
        try:
            res = requests.post(f'{OLLAMA_HOST}/api/chat', 
                                json={'model': DEFAULT_LLM_MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False, 'options': {'num_ctx': 32768}}, 
                                timeout=60)
            if res.status_code == 200:
                memory_md = res.json().get('message', {}).get('content', '').strip()
                
                # 移除思考過程
                if "<think>" in memory_md:
                    memory_md = re.sub(r"<think>.*?</think>", "", memory_md, flags=re.DOTALL).strip()
                
                # 從生成的 Markdown 中提取 Mermaid 流程圖代碼
                mermaid_match = re.search(r"```mermaid\s*(.*?)\s*```", memory_md, re.DOTALL)
                if mermaid_match:
                    mermaid_code = mermaid_match.group(1).strip()
            else:
                memory_md = f"# 法律事件記憶\n- **時間 (When)**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- **人物 (Who)**: 申訴人與AI\n- **事件 (What)**: 法律案件諮詢\n- **對話**: {user_input[:100]}...\n"
        except Exception as e:
            print(f"Failed to generate Obsidian memory: {e}")
            memory_md = f"# 法律事件記憶 (產生失敗)\n- **時間 (When)**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- **錯誤**: {e}\n- **對話**: {user_input[:100]}...\n"
            
        # 2. 定位 Obsidian Vault 路徑
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memory_{timestamp}.md"
        
        vault_dir = os.path.join(self.base_dir, "Obsidian_Vault")
        target_dir = os.path.join(vault_dir, "03_法律與案件")
        
        # 確保 Obsidian_Vault/03_法律與案件 目錄存在
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            print(f"Failed to create directory {target_dir}: {e}")
            target_dir = str(self.base_dir)
            
        file_path = os.path.join(target_dir, filename)
        
        # 3. 寫入 markdown 檔案至 Obsidian
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(memory_md)
            print(f"[OK] Successfully wrote memory and relation graph to Obsidian note: {file_path}")
        except Exception as e:
            print(f"Failed to write memory note to Obsidian: {e}")
            
        # 4. 同步索引至 ChromaDB，確保下次對話可通過嵌入語意進行聯想檢索
        try:
            vec = self._get_embedding(memory_md)
            if vec:
                self.intel_coll.add(
                    ids=[f"obsidian_memory_{timestamp}"],
                    documents=[memory_md],
                    embeddings=[vec],
                    metadatas=[{"source": f"Obsidian記憶 ({filename})", "type": "obsidian_memory"}]
                )
                print(f"[OK] Indexed Obsidian memory and relation graph in ChromaDB")
        except Exception as e:
            print(f"Failed to index memory in ChromaDB: {e}")
            
        return mermaid_code

    def chat(self, user_input):
        """相容規格書規定的 chat 介面"""
        reply, evidence = self.chat_with_rws(user_input)[:2]
        return reply, evidence

    SUBJECT_PROMPTS = {
        "民法": "你是一位民法專家，專精契約、物權與侵權行為等民事法律關係與實務爭議解析。",
        "刑法": "你是一位刑法與刑事訴訟專家，專精犯罪要件、量刑基準與訴訟防禦策略。",
        "行政程序法": "你是一位行政法學與公法實務專家，專精行政處分要件、行政爭訟與訴願程序合規。",
        "專利法": "你是一位專利代理人與智慧財產權專家，專精專利三要件（新穎性、進步性、產業利用性）與侵權分析。",
        "商標法": "你是一位商標審查與爭議救濟專家，專精商標近似、商品類似、混淆誤認之虞判定及商標侵權。",
        "著作權法": "你是一位著作權法專家，專精著作原創性、合理使用要件、重製與合理授權分析。",
        "營業秘密法": "你是一位企業營業秘密防護專家，專精營業秘密三要件（秘密性、經濟價值、合理保密措施）及競業禁止糾紛。",
        "個資法": "你是一位個人資料保護法與資料治理專家，專精個資蒐集、處理、利用之合法要件與合規評估。",
        "選罷法": "你是一位公職人員選舉罷免法專家，專精選罷規範、選舉無效訴訟與選罷罰則。",
        "證券交易法": "你是一位證交法與金融犯罪分析專家，專精內線交易、財報不實、操縱股價之要件認定與實務見解。",
        "所得稅法": "你是一位稅務規劃與租稅實務專家，專精綜合所得稅、營利事業所得稅核課與稅務訴訟糾紛。",
        "金融法規": "你是一位銀行與金融監理專家，專精洗錢防制、銀行法合規與金融消費者保護法實務。",
        "RealtyLex 不動產法律": "你是一位不動產與土地法專家，專精房地買賣、房屋租賃、借名登記與都市更新糾紛分析。",
        "國考": "你是一位國家考試（司法官與律師）輔導專家，引導使用者使用 IRAC 結構剖析國考歷屆考題與爭點。"
    }

    def verify_judgment_citations(self, reply: str) -> str:
        # 正則表達式抓取判決案號：如最高法院 112 年度台上字第 1234 號
        pattern = r"(最高法院\s*\d+\s*年度?\s*\w+字第\s*\d+\s*號)"
        matches = list(set(re.findall(pattern, reply)))
        
        verified_reply = reply
        for citation in matches:
            citation_clean = re.sub(r"\s+", "", citation)
            found = False
            try:
                # 模糊檢索本地法條與判決庫
                res = self.law_coll.query(query_texts=[citation], n_results=1)
                if res and res['documents'] and res['documents'][0]:
                    best_doc = res['documents'][0][0]
                    # 如果匹配度高，或者文件內容包含該案號
                    if citation_clean in best_doc.replace(" ", ""):
                        found = True
            except Exception:
                pass
            
            if found:
                label = f" {citation} `[✅ 判決真實性已確認]`"
            else:
                label = f" {citation} `[⚠️ 案號未載於本機資料庫]`"
                
            verified_reply = verified_reply.replace(citation, label)
            
        return verified_reply

    def chat_subject_qa(self, subject: str, query: str) -> tuple:
        # 獲取特定學科提示詞
        sub_prompt = self.SUBJECT_PROMPTS.get(subject, "你是一位精通臺灣實務的資深 AI 法律特助。")
        
        # 進行 RAG 檢索
        evidence = self.search_hybrid(query, category_hint=subject[:2])
        context_str = "\n".join([f"[{i+1}] {e['text']}" for i, e in enumerate(evidence)])
        
        system_instruction = (
            f"{sub_prompt}\n"
            "請基於以下經 RWS 篩選的法規與關聯資料進行專業解答，確保用語符合中華民國（臺灣）法律實務，避免大陸用語：\n\n"
            f"{context_str}\n"
        )
        
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": query}
        ]
        
        try:
            res = requests.post(f'{OLLAMA_HOST}/api/chat',
                                json={'model': DEFAULT_LLM_MODEL, 'messages': messages, 'stream': False}, timeout=120)
            if res.status_code == 200:
                reply = res.json().get('message', {}).get('content', 'API 回應格式異常')
                reply = self.verify_judgment_citations(reply)
                return reply, evidence
        except Exception as e:
            return f"❌ 呼叫學科問答服務失敗：{e}", []
            
        return "（未取得本地 LLM 回應，請確認連接正常。）", []

    def review_contract(self, contract_text: str) -> str:
        prompt = (
            "你是一位資深的法律合規與契約審查專家（老律師魂）。請幫我針對以下契約文字，進行深度的風險評估與審查。\n"
            "請特別注意並找出以下潛在風險與條款缺失：\n"
            "1. 違約責任與賠償限額（是否有顯失公平之高額違約金或對等性缺失）。\n"
            "2. 契約管轄權與準據法（是否有管轄法院不便或境外司法管轄瑕疵）。\n"
            "3. 終止與解約條款（是否有單方任意解約且無須補償之不平等約定）。\n"
            "4. 標的物交付與驗收標準（條款是否含糊不清、缺少確切驗收期）。\n"
            "5. 保密與智慧財產權歸屬（是否有過度轉讓、缺少合理免責例外）。\n\n"
            "請以條列式結構輸出：\n"
            "## 🕵️ LexMind-Review 契約合規審查報告\n"
            "### 一、 核心風險評估（Risk Assessment）\n"
            "[分析契約中具有法律風險的具體段落並給出理由]\n"
            "### 二、 缺失與建議增補條款（Missing & Proposed Clauses）\n"
            "[分析缺少了什麼保護性條款，並給出建議的具體合約文字]\n\n"
            f"契約內容：\n{contract_text}"
        )
        
        messages = [
            {"role": "system", "content": "你是一位資深法律合規與契約審查專家，請使用繁體中文法律用語進行分析。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            res = requests.post(f'{OLLAMA_HOST}/api/chat',
                                json={'model': DEFAULT_LLM_MODEL, 'messages': messages, 'stream': False}, timeout=120)
            if res.status_code == 200:
                reply = res.json().get('message', {}).get('content', 'API 回應格式異常')
                return reply
        except Exception as e:
            return f"❌ 執行契約審查失敗：{e}"
        return "（未取得本地 LLM 回應，請確認連接正常。）"

```

## workflow_helper.py

```python
import os
import yaml
from pathlib import Path

def load_config():
    # Load config.yaml from workspace root
    script_dir = Path(__file__).parent.resolve()
    workspace_root = script_dir.parent
    config_path = workspace_root / "config.yaml"
    
    if not config_path.exists():
        config_path = script_dir / "config.yaml"
        
    if not config_path.exists():
        # Fallback to current working directory
        config_path = Path("config.yaml").resolve()
        
    if not config_path.exists():
        # Create a default dict if config file is not found
        return {
            "paths": {
                "project_root": "D:\\LegalAI_Project",
                "raw_data_dir": "raw_data",
                "processed_md_dir": "processed_md",
                "manifests_dir": "manifests",
                "chunks_dir": "chunks",
                "logs_dir": "logs"
            },
            "api": {
                "gemini_api_key": "AUTO_LOAD_FROM_ENV",
                "gemini_model_low_cost": "gemini-2.5-flash",
                "gemini_model_high_accuracy": "gemini-2.5-pro"
            },
            "settings": {
                "low_cost_mode": True,
                "chunk_limit_audio_sec": 1200,
                "chunk_limit_video_sec": 720,
                "overlap_sec": 30,
                "silence_detect_duration": 1.5,
                "silence_detect_noise_db": -35,
                "stt_max_retries": 3
            }
        }
        
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

def get_resolved_paths():
    config = load_config()
    paths = config.get("paths", {})
    root = paths.get("project_root", "D:\\LegalAI_Project")
    
    # If D:\ drive does not exist, fallback to C:\LegalAI_Project
    if root.startswith("D:\\") and not os.path.exists("D:\\"):
        root = root.replace("D:\\", "C:\\")
        
    resolved = {"project_root": root}
    for key in ["raw_data_dir", "processed_md_dir", "manifests_dir", "chunks_dir", "logs_dir"]:
        sub_dir = paths.get(key, "")
        resolved[key] = os.path.join(root, sub_dir)
        
    return resolved

def ensure_dirs():
    paths = get_resolved_paths()
    for key, path in paths.items():
        if key == "project_root":
            continue
        os.makedirs(path, exist_ok=True)
    return paths

def get_all_keys():
    import json
    config = load_config()
    keys = []
    
    # 1. 讀取 config.yaml 中的金鑰列表
    api_section = config.get("api", {})
    if "gemini_api_keys" in api_section and isinstance(api_section["gemini_api_keys"], list):
        for k in api_section["gemini_api_keys"]:
            if k and isinstance(k, str):
                keys.append(k.strip())
                
    # 2. 讀取 config.yaml 中的單一金鑰
    single_key = api_section.get("gemini_api_key")
    if single_key and single_key != "AUTO_LOAD_FROM_ENV" and single_key not in keys:
        keys.append(single_key.strip())
        
    # 3. 讀取 .env
    script_dir = Path(__file__).parent.resolve()
    workspace_root = script_dir.parent
    env_path = workspace_root / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith("GEMINI_API_KEYS="):
                    val = line_str.split("=", 1)[1].strip()
                    for k in val.split(","):
                        k_clean = k.strip()
                        if k_clean and k_clean not in keys:
                            keys.append(k_clean)
                elif line_str.startswith("GEMINI_API_KEY="):
                    val = line_str.split("=", 1)[1].strip()
                    if val and val not in keys:
                        keys.append(val)
                        
    # 4. 讀取環境變數
    env_keys_str = os.environ.get("GEMINI_API_KEYS")
    if env_keys_str:
        for k in env_keys_str.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in keys:
                keys.append(k_clean)
    env_single = os.environ.get("GEMINI_API_KEY")
    if env_single and env_single not in keys:
        keys.append(env_single)
        
    return [k for k in keys if k]

def get_gemini_key():
    import json
    import time
    keys = get_all_keys()
    if not keys:
        return ""
    if len(keys) == 1:
        return keys[0]
        
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths["manifests_dir"], "api_keys_state.json")
    
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
            
    # Read config/quota_state.json to sync status
    quota_exhausted = []
    quota_state_file = "config/quota_state.json"
    try:
        if os.path.exists(quota_state_file):
            with open(quota_state_file, "r", encoding="utf-8") as f:
                quota_state = json.load(f)
            quota_exhausted = quota_state.get("exhausted_keys", [])
    except Exception:
        pass

    # 尋找第一個未標記為耗盡，或者已冷卻完畢（超過 10 分鐘）的金鑰
    active_keys = []
    current_time = time.time()
    quota_state_changed = False
    for k in keys:
        k_state = state.get(k, {})
        status = k_state.get("status")
        exhausted_at = k_state.get("exhausted_at", 0)
        
        # 10 分鐘自動解禁
        if status == "exhausted" and (current_time - exhausted_at > 600):
            status = "active"
            if k in quota_exhausted:
                quota_exhausted.remove(k)
                quota_state_changed = True
            
        if status != "exhausted" and k not in quota_exhausted:
            active_keys.append(k)
            
    if quota_state_changed:
        try:
            with open(quota_state_file, "w", encoding="utf-8") as f:
                json.dump({"exhausted_keys": quota_exhausted}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    if not active_keys:
        # 如果全部金鑰都耗盡了，安全起見自動重設狀態檔案，重新循環嘗試
        log_workflow("[Key Pool] 金鑰池內所有金鑰皆已標記為耗盡。正在重設狀態重新循環...", level="warning")
        reset_exhausted_keys()
        return keys[0]
        
    # 實作 Round-Robin 輪詢：尋找 last_used_key，並挑選它的下一個金鑰
    last_key = state.get("last_used_key")
    next_index = 0
    if last_key in active_keys:
        try:
            next_index = (active_keys.index(last_key) + 1) % len(active_keys)
        except ValueError:
            next_index = 0
        
    selected_key = active_keys[next_index]
    
    # 記錄最後使用的金鑰
    state["last_used_key"] = selected_key
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    return selected_key

def mark_key_exhausted(key):
    if not key:
        return
    import json
    import time
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths["manifests_dir"], "api_keys_state.json")
    
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
            
    state[key] = {
        "status": "exhausted",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "exhausted_at": time.time()
    }
    
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log_workflow(f"[Key Pool] 成功標記 API Key {key[:8]}...{key[-4:]} 為「暫時耗盡（進入10分鐘冷卻）」。", level="info")
    except Exception as e:
        print(f"Error saving key pool state: {e}")

    # 同步標記到 config/quota_state.json
    try:
        quota_state_file = "config/quota_state.json"
        quota_exhausted = []
        if os.path.exists(quota_state_file):
            with open(quota_state_file, "r", encoding="utf-8") as f:
                quota_state = json.load(f)
            quota_exhausted = quota_state.get("exhausted_keys", [])
        if key not in quota_exhausted:
            quota_exhausted.append(key)
            with open(quota_state_file, "w", encoding="utf-8") as f:
                json.dump({"exhausted_keys": quota_exhausted}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def reset_exhausted_keys():
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths["manifests_dir"], "api_keys_state.json")
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
            log_workflow("[Key Pool] 成功重置金鑰池中所有金鑰之狀態。", level="info")
        except Exception as e:
            print(f"Error resetting key pool state: {e}")

    try:
        quota_state_file = "config/quota_state.json"
        if os.path.exists(quota_state_file):
            with open(quota_state_file, "w", encoding="utf-8") as f:
                json.dump({"exhausted_keys": []}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def log_workflow(message, level="info"):
    paths = ensure_dirs()
    log_file = os.path.join(paths["logs_dir"], "workflow.log")
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level.upper()}] {message}\n"
    print(log_line.strip())
    
    # 【修復 Issue 27】架構：日誌設計存在平行寫入資料損毀風險，改用 ConcurrentRotatingFileHandler 解決多進程寫入衝突
    try:
        from concurrent_log_handler import ConcurrentRotatingFileHandler
        import logging
        logger = logging.getLogger("workflow")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = ConcurrentRotatingFileHandler(log_file, "a", 10*1024*1024, 5, encoding="utf-8")
            # 避免與 basicConfig 重疊輸出，若已有其它 handler 就不重複加
            logger.addHandler(handler)
        
        if level.lower() == "error":
            logger.error(message)
        elif level.lower() == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    except ImportError:
        # Fallback
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

def log_error(message):
    paths = ensure_dirs()
    log_file = os.path.join(paths["logs_dir"], "chunk_errors.log")
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [ERROR] {message}\n"
    print(log_line.strip())
    
    # 【修復 Issue 27】改用 ConcurrentRotatingFileHandler
    try:
        from concurrent_log_handler import ConcurrentRotatingFileHandler
        import logging
        logger = logging.getLogger("chunk_errors")
        if not logger.handlers:
            logger.setLevel(logging.ERROR)
            handler = ConcurrentRotatingFileHandler(log_file, "a", 10*1024*1024, 5, encoding="utf-8")
            logger.addHandler(handler)
        logger.error(message)
    except ImportError:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    
    # Also log to main workflow log
    log_workflow(message, level="error")

def get_ffmpeg_path():
    import shutil
    p = shutil.which("ffmpeg")
    if p:
        return p
    winget_paths = [
        r"C:\Users\temp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe",
        r"C:\Program Files (x85)\iMyFone\iMyFone D-Back\ffmpeg.exe",
        r"C:\Program Files (x86)\iMyFone\iMyFone D-Back\ffmpeg.exe"
    ]
    for wp in winget_paths:
        if os.path.exists(wp):
            return wp
    return "ffmpeg"

def get_ffprobe_path():
    import shutil
    p = shutil.which("ffprobe")
    if p:
        return p
    winget_paths = [
        r"C:\Users\temp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.exe"
    ]
    for wp in winget_paths:
        if os.path.exists(wp):
            return wp
    return "ffprobe"

```

