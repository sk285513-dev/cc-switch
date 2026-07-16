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
            return "[ERROR] 未安裝 faster-whisper 套件，請執行 pip install faster-whisper"
        
        # 執行過熱/過載降溫保護
        self.wait_for_gpu_cooldown(self.gpu_id)
        
        # 1. 針對大於 100MB 的影片檔案，預先使用 ffmpeg 提取音訊，避免 memory/decoding 卡死
        file_path_obj = Path(file_path)
        ext = file_path_obj.suffix.lower()
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024) if os.path.exists(file_path) else 0.0
        
        actual_transcribe_path = str(file_path_obj.resolve())
        temp_wav_path = None
        
        # 針對影音格式的大檔
        if ext in ['.mp4', '.avi', '.mkv', '.mov', '.mp3', '.wav', '.flac'] and file_size_mb > 100:
            import subprocess
            temp_wav_path = file_path_obj.parent / f"temp_extract_{file_path_obj.stem}_{int(time.time())}.wav"
            print(f"[INFO] 偵測到大型影音教材 ({file_size_mb:.1f} MB)，正在使用 ffmpeg 離線提取 16kHz mono 音訊以加速轉錄並防止卡死...")
            try:
                # 執行 ffmpeg 擷取音軌，16kHz mono, 16bit PCM
                cmd = [
                    "ffmpeg", "-y", "-i", str(file_path_obj.resolve()),
                    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    str(temp_wav_path.resolve())
                ]
                # 設定 240 秒超時，防止 ffmpeg 永久卡住
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240, check=True)
                actual_transcribe_path = str(temp_wav_path.resolve())
                print(f"[OK] 音訊擷取成功，臨時音軌大小: {os.path.getsize(temp_wav_path)/(1024*1024):.2f} MB")
            except Exception as fe:
                print(f"[WARN] ffmpeg 提取音軌失敗 ({fe})，回退至原生解碼...")
                if temp_wav_path and temp_wav_path.exists():
                    try:
                        temp_wav_path.unlink()
                    except:
                        pass
                temp_wav_path = None
                actual_transcribe_path = str(file_path_obj.resolve())
        
        if not self.whisper_model:
            # 優先離線載入 (local_files_only=True) 避免聯網逾時卡死
            try:
                self.whisper_model = WhisperModel(self.model_size, device='cuda', device_index=self.gpu_id, compute_type='float16', local_files_only=True)
            except Exception as e1:
                print(f"[WARN] 離線 CUDA 載入失敗 ({e1})，嘗試聯網 CUDA...")
                try:
                    self.whisper_model = WhisperModel(self.model_size, device='cuda', device_index=self.gpu_id, compute_type='float16', local_files_only=False)
                except Exception as e2:
                    print(f"[WARN] CUDA 聯網載入也失敗 ({e2})，嘗試離線 CPU...")
                    try:
                        self.whisper_model = WhisperModel(self.model_size, device='cpu', compute_type='int8', local_files_only=True)
                    except Exception as e3:
                        print(f"[WARN] 離線 CPU 載入失敗 ({e3})，嘗試聯網 CPU...")
                        try:
                            self.whisper_model = WhisperModel(self.model_size, device='cpu', compute_type='int8', local_files_only=False)
                        except Exception as e4:
                            # 發生錯誤前先清理臨時檔案
                            if temp_wav_path and temp_wav_path.exists():
                                try:
                                    temp_wav_path.unlink()
                                except:
                                    pass
                            return f"[ERROR] 無法初始化 Whisper 模型 (CUDA & CPU 皆失敗): {e4}"

        print(f"[TRANS] 正在轉錄影音學術教材: {file_path}...")
        
        try:
            segments, _ = self.whisper_model.transcribe(actual_transcribe_path, beam_size=5)
            
            raw_results = []
            for s in segments:
                # 校正語音
                clean_text = self.apply_glossary_fix(s.text)
                timestamp = f"[{int(s.start // 3600):02d}:{int((s.start % 3600) // 60):02d}:{s.start % 60:05.2f} -> {int(s.end // 3600):02d}:{int((s.end % 3600) // 60):02d}:{s.end % 60:05.2f}]"
                raw_results.append(f"{timestamp} {clean_text}")
                
            result_str = "\n".join(raw_results)
        finally:
            # 清理臨時音訊檔
            if temp_wav_path and temp_wav_path.exists():
                try:
                    temp_wav_path.unlink()
                    print(f"[OK] 已成功清理臨時音軌檔: {temp_wav_path.name}")
                except Exception as e_clean:
                    print(f"[WARN] 清理臨時音軌檔失敗: {e_clean}")
                    
        return result_str

    def ocr_document(self, file_path):
        """視覺：書狀、照片 PDF 之圖形辨識"""
        if pytesseract is None:
            return "[ERROR] 未安裝 pytesseract 相關套件，請執行 pip install pytesseract pdf2image"
            
        print(f"[OCR] 正在進行高保真 OCR 辨識: {file_path}...")
        try:
            if str(file_path).lower().endswith('.pdf'):
                images = convert_from_path(str(file_path))
                raw_text = "\n".join([pytesseract.image_to_string(img, lang='chi_tra+eng') for img in images])
            else:
                raw_text = pytesseract.image_to_string(Image.open(str(file_path)), lang='chi_tra+eng')
            return self.apply_glossary_fix(raw_text)
        except Exception as e:
            return f"[ERROR] OCR 發生異常錯誤：{e}"

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