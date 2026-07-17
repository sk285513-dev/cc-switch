import os
import re
import requests
import json
from pathlib import Path
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
except ImportError:
    pytesseract = None

class MultimodalLegalInput:
    def __init__(self, model_size='small', glossary_path=None, gpu_id=0):
        if glossary_path is None:
            # 動態判定專案根目錄中的詞庫檔案，適應任何本機磁碟路徑
            base_dir = Path(__file__).resolve().parent.parent
            glossary_path = str(base_dir / "legal_glossary.json")
        self.glossary_path = glossary_path
        self.glossary = self._load_glossary()
        self.llm_url = 'http://localhost:11434/api/chat'
        
        # 延遲加載 WhisperModel 防止顯示卡過載
        self.whisper_model = None
        self.model_size = model_size
        self.gpu_id = gpu_id

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

    def wait_for_gpu_cooldown(self, gpu_id=0):
        """檢查 GPU 溫度與使用率，如果過高則暫停以進行降溫"""
        import time
        import subprocess

        # 在 Windows 環境嘗試執行 nvidia-smi
        while True:
            try:
                cmd = ["nvidia-smi", "--query-gpu=index,temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if res.returncode == 0:
                    lines = res.stdout.strip().split("\n")
                    gpu_data = {}
                    for line in lines:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 3:
                            idx = int(parts[0])
                            temp = int(parts[1])
                            util = int(parts[2])
                            gpu_data[idx] = (temp, util)

                    if gpu_id in gpu_data:
                        temp, util = gpu_data[gpu_id]
                        if temp >= 85 and util >= 95:
                            print(f"[GPU WARNING] [降溫保護] GPU {gpu_id} 溫度已達 {temp}C (臨界點 85C)，負載為 {util}%！已暫停當前工作，等待降溫中...")
                            time.sleep(10)
                            continue
                        elif temp >= 80:
                            # 溫度偏高，稍微放慢速度以防過熱
                            print(f"[GPU INFO] [降溫保護] GPU {gpu_id} 溫度偏高 ({temp}C)，為避免過熱，等待 3 秒再繼續...")
                            time.sleep(3)
                break
            except Exception as e:
                # 若無 nvidia-smi 則跳出
                print(f"[GPU WARNING] 無法讀取 GPU {gpu_id} 的實時狀態 ({e})，跳過降溫檢查。")
                break

    def transcribe_audio(self, file_path):
        """聽覺：影音轉錄，相容 VTT 格式時間軸"""
        if WhisperModel is None:
            return "❌ [錯誤] 未安裝 faster-whisper 套件，請執行 pip install faster-whisper"
        
        # 執行過熱/過載降溫保護
        self.wait_for_gpu_cooldown(self.gpu_id)
        
        if not self.whisper_model:
            # 優先離線載入 (local_files_only=True) 避免聯網逾時卡死
            try:
                self.whisper_model = WhisperModel(self.model_size, device='cuda', device_index=self.gpu_id, compute_type='float16', local_files_only=True)
            except Exception as e1:
                print(f"⚠️ 離線 CUDA 載入失敗 ({e1})，嘗試聯網 CUDA...")
                try:
                    self.whisper_model = WhisperModel(self.model_size, device='cuda', device_index=self.gpu_id, compute_type='float16', local_files_only=False)
                except Exception as e2:
                    print(f"⚠️ CUDA 聯網載入也失敗 ({e2})，嘗試離線 CPU...")
                    try:
                        self.whisper_model = WhisperModel(self.model_size, device='cpu', compute_type='int8', local_files_only=True)
                    except Exception as e3:
                        print(f"⚠️ 離線 CPU 載入失敗 ({e3})，嘗試聯網 CPU...")
                        try:
                            self.whisper_model = WhisperModel(self.model_size, device='cpu', compute_type='int8', local_files_only=False)
                        except Exception as e4:
                            return f"❌ [錯誤] 無法初始化 Whisper 模型 (CUDA & CPU 皆失敗): {e4}"

        print(f"🎤 正在轉錄影音學術教材: {file_path}...")
        segments, _ = self.whisper_model.transcribe(str(file_path), beam_size=5)
        
        raw_results = []
        for s in segments:
            # 校正語音
            clean_text = self.apply_glossary_fix(s.text)
            timestamp = f"[{int(s.start // 3600):02d}:{int((s.start % 3600) // 60):02d}:{s.start % 60:05.2f} -> {int(s.end // 3600):02d}:{int((s.end % 3600) // 60):02d}:{s.end % 60:05.2f}]"
            raw_results.append(f"{timestamp} {clean_text}")
            
        return "\n".join(raw_results)

    def ocr_document(self, file_path):
        """視覺：書狀、照片 PDF 之圖形辨識"""
        # 1. 針對 PDF 優先嘗試使用 pypdf 提取數位文字
        if str(file_path).lower().endswith('.pdf'):
            try:
                import pypdf
                print(f"📄 優先嘗試數位文字提取 (pypdf): {file_path}...")
                reader = pypdf.PdfReader(str(file_path))
                text_list = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_list.append(page_text)
                full_text = "\n".join(text_list).strip()
                if len(full_text) > 100:
                    print(f"✅ 成功直接提取 {len(reader.pages)} 頁數位文字，字數: {len(full_text)}")
                    return self.apply_glossary_fix(full_text)
                else:
                    print("⚠️ 數位文字提取字數過少，可能為掃描件 PDF，將自動回退至 Tesseract OCR 引擎進行高保真圖形辨識...")
            except Exception as e_pdf:
                print(f"⚠️ 數位文字提取失敗 ({e_pdf})，將自動回退至 Tesseract OCR 引擎進行高保真圖形辨識...")

        # 2. 如果是圖片，或數位提取無效/為掃描件，回退至 Tesseract OCR
        if pytesseract is None:
            return "❌ [錯誤] 未安裝 pytesseract 相關套件，請執行 pip install pytesseract pdf2image"
            
        print(f"👁️ 正在進行高保真 OCR 辨識: {file_path}...")
        try:
            if str(file_path).lower().endswith('.pdf'):
                images = convert_from_path(str(file_path))
                raw_text = "\n".join([pytesseract.image_to_string(img, lang='chi_tra+eng') for img in images])
            else:
                raw_text = pytesseract.image_to_string(Image.open(str(file_path)), lang='chi_tra+eng')
            return self.apply_glossary_fix(raw_text)
        except Exception as e:
            err_msg = str(e)
            if "poppler" in err_msg.lower() or "pdfinfo" in err_msg.lower():
                return "❌ OCR 失敗：此 PDF 為掃描件，需要使用 Poppler 進行圖像轉換，但系統缺少 Poppler 組件。請下載並安裝 Poppler，並將其 bin 目錄加入系統環境變數 PATH 中，或改用已具備文字層的數位 PDF。"
            if "tesseract" in err_msg.lower():
                return "❌ OCR 失敗：系統未偵測到 Tesseract OCR 引擎。請下載安裝 Tesseract-OCR，並確保 chi_tra 語言包已安裝，且將其路徑加入 PATH。"
            return f"❌ OCR 發生異常錯誤：{err_msg}"

    def post_refine_using_llm(self, text: str) -> str:
        """第二層：法語脈絡重構（大模型微觀校對）"""
        if not text:
            return ""
        prompt = (
            "你是一位在台灣法律實務界見習的高材生，精通繁體中文與台灣司法常用代稱與法條格式。\n"
            "以下是一段由語音識別（ASR）或圖片辨識（OCR）生成的法律文本草稿，其中仍可能包含同音錯別字、"
            "贅詞，或把「甲方」、「乙方」等天干稱呼聽錯的情況。\n"
            "請在【不改變原話意圖】的前提下，將其完整校對為符合台灣實務用語的精準文字，並維持任何已有的時間軸。[時間軸格式必須保留]。\n\n"
            f"待校對文本：\n{text}"
        )
        try:
            payload = {
                "model": "deepseek-r1:7b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1}
            }
            res = requests.post(self.llm_url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json().get('message', {}).get('content', text)
        except Exception as e:
            print(f"⚠️ 大模型校對失敗 (非致命): {e}")
        return text