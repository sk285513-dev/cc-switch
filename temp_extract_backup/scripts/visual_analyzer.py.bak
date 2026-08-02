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

class VisualLegalAnalyzer:
    def __init__(self, agent_instance=None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.obsidian_dir = self.base_dir / "Obsidian_Vault" / "04_教材圖表校對"
        self.image_dir = self.obsidian_dir / "images"
        os.makedirs(self.image_dir, exist_ok=True)
        self.agent_instance = agent_instance
        self.llm_url = f'{os.environ.get("OLLAMA_HOST", "http://localhost:11434")}/api/chat'
        self.model_name = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")

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
                
                # 儲存裁切下來的圖表圖片
                clean_src = self._sanitize_filename(source_name)
                crop_filename = f"{clean_src}_p{page_no}_crop_{idx}.png"
                crop_path = self.image_dir / crop_filename
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
{ocr_text}

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

        # 取得影片資訊與抽樣間隔（每 5 秒抽樣一影格）
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_interval = 5 * fps  # 5 秒
        
        prev_gray = None
        is_writing = False
        writing_start_frame = 0
        last_captured_time = -30  # 避免 30 秒內重複擷取
        
        created_notes = []
        frame_idx = 0
        board_idx = 0
        video_stem = Path(video_path).stem
        clean_video_name = self._sanitize_filename(video_stem)

        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
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
                            
                            # 儲存板書擷圖
                            ts_str = f"{int(current_sec // 3600):02d}_{int((current_sec % 3600) // 60):02d}_{current_sec % 60:02d}"
                            board_filename = f"board_{clean_video_name}_{ts_str}.png"
                            board_path = self.image_dir / board_filename
                            cv2.imwrite(str(board_path), board_crop)
                            
                            if status_callback:
                                status_callback(f"🎬 偵測到老師板書動作！時間點: {current_sec // 60}分{current_sec % 60}秒，已自動截圖...")

                            # 進行輕量 OCR 辨識
                            ocr_text = ""
                            if pytesseract is not None:
                                try:
                                    board_rgb = cv2.cvtColor(board_crop, cv2.COLOR_BGR2RGB)
                                    ocr_text = pytesseract.image_to_string(Image.fromarray(board_rgb), lang='chi_tra+eng').strip()
                                except:
                                    pass

                            # 判斷板書屬性 (文字板書 vs 關係圖板書)
                            is_text_board = len(ocr_text) > 15
                            board_type_label = "文字板書" if is_text_board else "關係圖/邏輯圖板書"
                            
                            # 呼叫大模型比對知識庫法規並生成筆記內容
                            prompt = f"""你是一個精通臺灣法律實務的助理。我們在法律影音教材《{video_stem}》的時間點：{current_sec // 60}分{current_sec % 60}秒 偵測到老師書寫了板書，並自動截圖。
擷取類型分類為：【{board_type_label}】。
擷取區域的 OCR 辨識字元如下：
{ocr_text}

請根據這些資訊與您擁有的台灣法律知識，幫我完成以下事項：
1. 針對辨識出的板書文字，進行語意整理，並自動與臺灣現行法律條文（如民法第184條、侵權行為、消滅時效等）進行比對，寫下「知識庫比對與理解演化註記」。
2. 如果分類為「關係圖/邏輯圖板書」（或者有複雜邏輯關係），請幫我**生成對應的 Mermaid.js 流程圖代碼**以呈現老師黑板上的圖畫結構。
   - 注意：Mermaid 節點文字必須用雙引號括住，例如 A["原告甲"] --> B["被告乙"]，以防語法出錯。
   - 如果分類為「文字板書」，則生成一個整理好的條列式邏輯樹 Mermaid 關係圖。

請只輸出：
【解讀與註記】：
(您的詳細法律理解說明與條文對位)

【MERMAID 代碼】：
(完整的 mermaid 程式碼塊，如 graph TD ... 等，不要帶 markdown ``` 符號)
"""
                            ai_response = self._query_llm(prompt)
                            
                            ai_analysis = "（解讀生成失敗）"
                            mermaid_code = "graph TD\n    A[\"影音板書\"] --> B[\"尚無關聯關係\"]"
                            
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
                
        cap.release()
        return created_notes
