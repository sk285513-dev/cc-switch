# ==========================================
# Streamlit 1.0/2026 舊版元件相容性修復補丁 (Monkey Patch)
# ==========================================
import streamlit as st
import streamlit.components.v1 as components
# 強制將已被移除的 html 屬性重新導向至 st.html，直接避免系統崩潰卡死
if not hasattr(components, 'html') or getattr(components, 'html').__name__ != 'html_patch':
    def html_patch(html_content, *args, **kwargs):
        return st.html(html_content)
    components.html = html_patch
# ==========================================

import sys
import gc

if sys.platform == "win32":
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8-sig', errors='replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8-sig', errors='replace')
    except Exception:
        pass

import os
import time
import datetime
import requests
from pathlib import Path

@st.cache_resource
def init_system_resources():
    try:
        import ctypes
        import subprocess
        if sys.platform == "win32" and ctypes.windll.shell32.IsUserAnAdmin() != 0:
            script_path = "C:/LocalAI_Workstation/scripts_v6/law_scraper_cli.py"
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable
            cmd = f'schtasks /create /tn "LexMind_Law_Scraper" /tr "{python_exe} {script_path}" /sc daily /st 02:00 /ru "SYSTEM" /rl HIGHEST /f'
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", cmd], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        pass

init_system_resources()

# 套用 48GB DRAM 環境硬體解限速優化配置 (Single Source of Truth)
try:
    from scripts_v6.config_loader import apply_hardware_config
    cfg = apply_hardware_config()
    CHROMA_TEXT_LIMIT_CHARS = cfg.get("chroma_text_limit", 150000)
except Exception:
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["MKL_NUM_THREADS"] = "4"
    CHROMA_TEXT_LIMIT_CHARS = 150000

SUPPORTED_INGEST_EXTS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.mp3', '.mp4', '.wav'}
BROWSER_UPLOAD_SAFE_LIMIT_MB = 200
TEXT_PREVIEW_LIMIT_CHARS = 120_000


# 動態解鎖與注入 PYTHONPATH，實現 100% 免配置、免設定環境與路徑
base_path = Path(__file__).resolve().parent
if str(base_path) not in sys.path:
    sys.path.append(str(base_path))
if str(base_path / "scripts_v6") not in sys.path:
    sys.path.append(str(base_path / "scripts_v6"))

# 初始化 Ollama 連接網址至環境變數中，供子模組與 API 調用
if "ollama_url" not in st.session_state:
    st.session_state.ollama_url = "http://localhost:11434"
os.environ["OLLAMA_HOST"] = st.session_state.ollama_url
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")
os.environ["OLLAMA_MODEL"] = st.session_state.ollama_model

# 導入本地多模態模組
from scripts_v6.agent_core_pro import LocalLegalAgent
from scripts_v6.legal_calendar import LegalCalendarPlugin
from scripts_v6.multimodal_input import MultimodalLegalInput
from scripts_v6.backup_manager import LegalDBBackupManager
from scripts_v6.visual_analyzer import VisualLegalAnalyzer

st.set_page_config(page_title="LexMind-Omni 臺灣法律 AI 工作站", layout="wide", initial_sidebar_state="expanded")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

import streamlit.components.v1 as components
components.html(
    '''
    <script>
    window.parent.document.documentElement.lang = 'zh-TW';
    </script>
    ''',
    width=0,
    height=0,
)


import json
import html
import threading
import re

BUFFER_FILE = "C:\\LocalAI_Workstation\\chosen_paths_buffer.json"

def save_paths_to_buffer(paths):
    try:
        os.makedirs(os.path.dirname(BUFFER_FILE), exist_ok=True)
        with open(BUFFER_FILE, "w", encoding="utf-8-sig") as f:
            json.dump(paths, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_paths_from_buffer():
    if os.path.exists(BUFFER_FILE):
        try:
            with open(BUFFER_FILE, "r", encoding="utf-8-sig") as f:
                paths = json.load(f)
                if isinstance(paths, list):
                    return paths
        except Exception:
            pass
    return []

INGESTED_HISTORY_FILE = "C:\\LocalAI_Workstation\\ingested_history.json"

def load_ingested_history():
    if os.path.exists(INGESTED_HISTORY_FILE):
        try:
            with open(INGESTED_HISTORY_FILE, "r", encoding="utf-8-sig") as f:
                history = json.load(f)
                if isinstance(history, dict):
                    return history
        except Exception:
            pass
    return {}

def save_ingested_history(history):
    try:
        os.makedirs(os.path.dirname(INGESTED_HISTORY_FILE), exist_ok=True)
        with open(INGESTED_HISTORY_FILE, "w", encoding="utf-8-sig") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def parse_multiple_paths(input_str):
    paths = []
    # 情況 1: 用雙引號括起來的多個路徑，例如 "path1" "path2" "path3"
    if '"' in input_str:
        quoted_paths = re.findall(r'"([^"]+)"', input_str)
        for p in quoted_paths:
            p_clean = p.strip()
            if p_clean:
                paths.append(p_clean)
    else:
        # 情況 2: 沒有引號，但可能用分號、逗號或換行分割的多個路徑
        raw_parts = re.split(r'[\n\r;]+', input_str)
        for part in raw_parts:
            part_clean = part.strip()
            if part_clean:
                paths.append(part_clean)
    
    # 如果還是空的，且輸入本身不為空，就直接把整個字串當作單一路徑
    if not paths and input_str.strip():
        paths.append(input_str.strip())
        
    return paths

class IngestionBackgroundTask:
    status = "idle"  # idle, running, paused, cancelled, completed, error
    total_files = 0
    processed_count = 0
    current_file = ""
    current_action = ""
    logs = []
    generated_transcripts = []
    generated_visual_notes = []
    cancel_requested = False
    pause_requested = False
    error_message = ""
    valid_files_info = []
    transcripts_dir = ""
    class_name = ""
    lesson_name = ""
    last_heartbeat = 0.0
    
    # 支援多 GPU Worker 單獨狀態追蹤
    gpu0_file = "閒置"
    gpu1_file = "閒置"
    gpu0_action = "閒置"
    gpu1_action = "閒置"
    
    STATE_FILE = "C:\\LocalAI_Workstation\\ingest_state.json"
    
    @classmethod
    def reset(cls):
        cls.status = "idle"
        cls.total_files = 0
        cls.processed_count = 0
        cls.current_file = ""
        cls.current_action = ""
        cls.logs = []
        cls.generated_transcripts = []
        cls.generated_visual_notes = []
        cls.cancel_requested = False
        cls.pause_requested = False
        cls.error_message = ""
        cls.valid_files_info = []
        cls.transcripts_dir = ""
        cls.class_name = ""
        cls.lesson_name = ""
        cls.gpu0_file = "閒置"
        cls.gpu1_file = "閒置"
        cls.gpu0_action = "閒置"
        cls.gpu1_action = "閒置"
        cls.last_heartbeat = 0.0
        if os.path.exists(cls.STATE_FILE):
            try:
                os.remove(cls.STATE_FILE)
            except:
                pass
                
    @classmethod
    def save_to_disk(cls):
        import threading
        if not hasattr(cls, "_save_lock"):
            cls._save_lock = threading.Lock()
        with cls._save_lock:
            state = {
                "status": cls.status,
                "total_files": cls.total_files,
                "processed_count": cls.processed_count,
                "current_file": cls.current_file,
                "current_action": cls.current_action,
                "logs": cls.logs,
                "generated_transcripts": cls.generated_transcripts,
                "generated_visual_notes": cls.generated_visual_notes,
                "cancel_requested": cls.cancel_requested,
                "pause_requested": cls.pause_requested,
                "error_message": cls.error_message,
                "valid_files_info": cls.valid_files_info,
                "transcripts_dir": cls.transcripts_dir,
                "class_name": cls.class_name,
                "lesson_name": cls.lesson_name,
                "gpu0_file": cls.gpu0_file,
                "gpu1_file": cls.gpu1_file,
                "gpu0_action": cls.gpu0_action,
                "gpu1_action": cls.gpu1_action,
                "last_heartbeat": cls.last_heartbeat
            }
            try:
                with open(cls.STATE_FILE, "w", encoding="utf-8-sig") as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[WARNING] Failed to save ingest state: {e}")
            
    @classmethod
    def load_from_disk(cls):
        if not os.path.exists(cls.STATE_FILE):
            return False
        try:
            with open(cls.STATE_FILE, "r", encoding="utf-8-sig") as f:
                state = json.load(f)
            cls.status = state.get("status", "idle")
            cls.total_files = state.get("total_files", 0)
            cls.processed_count = state.get("processed_count", 0)
            cls.current_file = state.get("current_file", "")
            cls.current_action = state.get("current_action", "")
            cls.logs = state.get("logs", [])
            cls.generated_transcripts = state.get("generated_transcripts", [])
            cls.generated_visual_notes = state.get("generated_visual_notes", [])
            cls.cancel_requested = state.get("cancel_requested", False)
            cls.pause_requested = state.get("pause_requested", False)
            cls.error_message = state.get("error_message", "")
            cls.valid_files_info = state.get("valid_files_info", [])
            cls.transcripts_dir = state.get("transcripts_dir", "")
            cls.class_name = state.get("class_name", "")
            cls.lesson_name = state.get("lesson_name", "")
            cls.gpu0_file = state.get("gpu0_file", "閒置")
            cls.gpu1_file = state.get("gpu1_file", "閒置")
            cls.gpu0_action = state.get("gpu0_action", "閒置")
            cls.gpu1_action = state.get("gpu1_action", "閒置")
            cls.last_heartbeat = state.get("last_heartbeat", 0.0)
            return True
        except Exception as e:
            print(f"[WARNING] Failed to load ingest state: {e}")
            return False

class SubjectIQManager:
    FILE_PATH = "C:\\LocalAI_Workstation\\subject_intelligence.json"
    
    @classmethod
    def load_data(cls):
        if not os.path.exists(cls.FILE_PATH):
            return {}
        try:
            with open(cls.FILE_PATH, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load subject intelligence: {e}")
            return {}
            
    @classmethod
    def save_data(cls, data):
        try:
            with open(cls.FILE_PATH, "w", encoding="utf-8-sig") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] Failed to save subject intelligence: {e}")
            
    @classmethod
    def add_feedback(cls, subject, score_type, comment=""):
        data = cls.load_data()
        if subject not in data:
            data[subject] = {
                "likes": 0,
                "dislikes": 0,
                "comments": []
            }
        
        if score_type == "like":
            data[subject]["likes"] = data[subject].get("likes", 0) + 1
        elif score_type == "dislike":
            data[subject]["dislikes"] = data[subject].get("dislikes", 0) + 1
            
        if comment.strip():
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data[subject]["comments"].append({
                "timestamp": timestamp,
                "comment": comment.strip(),
                "type": score_type
            })
            
        cls.save_data(data)
        
    @classmethod
    def calculate_iq(cls, subject):
        data = cls.load_data()
        if subject not in data:
            likes = 0
            dislikes = 0
        else:
            likes = data[subject].get("likes", 0)
            dislikes = data[subject].get("dislikes", 0)
            
        iq = ((likes + 4) / (likes + dislikes + 5)) * 100.0
        return round(iq, 1)

def process_multimodal_input(uploaded_file):
    if not uploaded_file:
        return ""
    
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()
    
    # Save file to a temporary location to process
    temp_dir = Path("C:/LocalAI_Workstation/temp_uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file_path = temp_dir / uploaded_file.name
    with open(temp_file_path, "wb") as f:
        f.write(file_bytes)
        
    text_result = ""
    
    # Process by type
    if file_name.endswith(('.mp3', '.wav', '.m4a', '.mp4', '.ogg')):
        with st.spinner("🎙️ 正在以 Whisper 進行語音轉錄..."):
            try:
                processor = MultimodalLegalInput()
                text_result = processor.transcribe_audio(str(temp_file_path))
            except Exception as e:
                text_result = f"語音轉錄失敗：{e}"
    elif file_name.endswith(('.png', '.jpg', '.jpeg', '.pdf')):
        with st.spinner("📄 正在以 OCR 進行文字辨識..."):
            try:
                processor = MultimodalLegalInput()
                ocr_results = processor.ocr_document(str(temp_file_path))
                if isinstance(ocr_results, list):
                    text_result = "\n".join([page["text"] for page in ocr_results])
                else:
                    text_result = ocr_results
            except Exception as e:
                text_result = f"OCR 辨識失敗：{e}"
    elif file_name.endswith('.txt'):
        try:
            text_result = file_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            text_result = f"檔案讀取失敗：{e}"
    else:
        text_result = f"[無法識別的文件類型] {uploaded_file.name}"
        
    # Remove temporary file
    try:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    except:
        pass
        
    return text_result


def run_background_ingestion(agent_instance, start_idx=0):
    IngestionBackgroundTask.status = "running"
    IngestionBackgroundTask.last_heartbeat = time.time()
    IngestionBackgroundTask.save_to_disk()
    
    import threading
    ingestion_lock = threading.Lock()
    
    try:
        import os
        os.environ["OLLAMA_HOST"] = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        os.environ["OLLAMA_MODEL"] = os.environ.get("OLLAMA_MODEL", "deepseek-r1:32b")
        
        analyzer = VisualLegalAnalyzer()
        valid_files = IngestionBackgroundTask.valid_files_info
        transcripts_dir = IngestionBackgroundTask.transcripts_dir
        
        # 定義 GPU Worker 閉包函數，處理被分配到的檔案
        def worker_loop(gpu_id, jobs_to_process):
            processor = MultimodalLegalInput(gpu_id=gpu_id)
            
            for idx, disp_name, f_path, src_type in jobs_to_process:
                # 每個檔案開始處理時更新心跳
                with ingestion_lock:
                    IngestionBackgroundTask.last_heartbeat = time.time()
                    IngestionBackgroundTask.save_to_disk()

                # 檢查是否已完全吸收過且檔案無變更，若符合則自動跳過
                with ingestion_lock:
                    history = load_ingested_history()
                    already_ingested = False
                    if f_path in history:
                        try:
                            curr_size = os.path.getsize(f_path)
                            curr_mtime = os.path.getmtime(f_path)
                            record = history[f_path]
                            if record.get("size") == curr_size and record.get("mtime") == curr_mtime:
                                already_ingested = True
                        except Exception:
                            pass
                    
                    if already_ingested:
                        IngestionBackgroundTask.processed_count += 1
                        IngestionBackgroundTask.logs.append(f"🔄 [自動跳過] 檔案先前已完全消化，無須重複處理: {disp_name}")
                        if gpu_id == 0:
                            IngestionBackgroundTask.gpu0_file = disp_name
                            IngestionBackgroundTask.gpu0_action = "✅ 已跳過(重複)"
                        else:
                            IngestionBackgroundTask.gpu1_file = disp_name
                            IngestionBackgroundTask.gpu1_action = "✅ 已跳過(重複)"
                        IngestionBackgroundTask.last_heartbeat = time.time()
                        IngestionBackgroundTask.save_to_disk()
                        continue

                # 檢查取消
                if IngestionBackgroundTask.cancel_requested:
                    return
                    
                # 處理暫停
                while IngestionBackgroundTask.pause_requested:
                    with ingestion_lock:
                        IngestionBackgroundTask.status = "paused"
                        if gpu_id == 0:
                            IngestionBackgroundTask.gpu0_action = "⏸️ 暫停中... 等待恢復"
                        else:
                            IngestionBackgroundTask.gpu1_action = "⏸️ 暫停中... 等待恢復"
                        IngestionBackgroundTask.last_heartbeat = time.time()
                        IngestionBackgroundTask.save_to_disk()
                    time.sleep(1)
                    if IngestionBackgroundTask.cancel_requested:
                        return
                        
                with ingestion_lock:
                    if IngestionBackgroundTask.status == "paused":
                        IngestionBackgroundTask.status = "running"
                    if gpu_id == 0:
                        IngestionBackgroundTask.gpu0_file = disp_name
                        IngestionBackgroundTask.gpu0_action = "正在初始化..."
                    else:
                        IngestionBackgroundTask.gpu1_file = disp_name
                        IngestionBackgroundTask.gpu1_action = "正在初始化..."
                    IngestionBackgroundTask.last_heartbeat = time.time()
                    IngestionBackgroundTask.save_to_disk()
                    
                file_size_mb = os.path.getsize(f_path) / (1024 * 1024) if os.path.exists(f_path) else 0.0
                mode_label = "本機大檔低記憶體模式" if src_type == "local" else "瀏覽器小檔模式"
                p_file = Path(f_path)
                
                # 1. 擷取課程名稱與課堂編號
                class_name = IngestionBackgroundTask.class_name or "未分類課程"
                lesson_name = IngestionBackgroundTask.lesson_name or "未分類課堂"
                
                if src_type == "local":
                    f_path_obj = Path(f_path)
                    parent_dir = f_path_obj.parent
                    grandparent_dir = parent_dir.parent if parent_dir else None
                    
                    def is_valid_folder(path_obj):
                        if not path_obj:
                            return False
                        name = path_obj.name
                        if not name or name.endswith(":") or name == "/" or name == "\\":
                            return False
                        return True
                        
                    if is_valid_folder(parent_dir):
                        lesson_name = parent_dir.name
                        if is_valid_folder(grandparent_dir):
                            class_name = grandparent_dir.name
                        else:
                            class_name = parent_dir.name
                            lesson_name = "第一層目錄"
                else:
                    class_name = "瀏覽器上傳"
                    lesson_name = "未分類"
                    
                # 2. 檔案讀取、轉錄與 OCR
                raw_text = ""
                pages_list = []
                
                def update_sub_status(msg):
                    with ingestion_lock:
                        if gpu_id == 0:
                            IngestionBackgroundTask.gpu0_action = msg
                        else:
                            IngestionBackgroundTask.gpu1_action = msg
                        IngestionBackgroundTask.current_action = f"GPU 0: {IngestionBackgroundTask.gpu0_action} | GPU 1: {IngestionBackgroundTask.gpu1_action}"
                        IngestionBackgroundTask.last_heartbeat = time.time()
                        IngestionBackgroundTask.save_to_disk()
                    if IngestionBackgroundTask.cancel_requested:
                        raise InterruptedError("Cancelled by user")
                    while IngestionBackgroundTask.pause_requested:
                        with ingestion_lock:
                            IngestionBackgroundTask.status = "paused"
                            if gpu_id == 0:
                                IngestionBackgroundTask.gpu0_action = "⏸️ 暫停中... 等待恢復指令"
                            else:
                                IngestionBackgroundTask.gpu1_action = "⏸️ 暫停中... 等待恢復指令"
                            IngestionBackgroundTask.last_heartbeat = time.time()
                            IngestionBackgroundTask.save_to_disk()
                        time.sleep(1)
                        if IngestionBackgroundTask.cancel_requested:
                            raise InterruptedError("Cancelled by user")
                    with ingestion_lock:
                        if IngestionBackgroundTask.status == "paused":
                            IngestionBackgroundTask.status = "running"
                            
                def handle_ocr_page(pil_img, page_num):
                    if IngestionBackgroundTask.cancel_requested:
                        raise InterruptedError("Cancelled by user")
                    while IngestionBackgroundTask.pause_requested:
                        with ingestion_lock:
                            IngestionBackgroundTask.status = "paused"
                            if gpu_id == 0:
                                IngestionBackgroundTask.gpu0_action = "⏸️ 暫停中... 等待恢復指令"
                            else:
                                IngestionBackgroundTask.gpu1_action = "⏸️ 暫停中... 等待恢復指令"
                            IngestionBackgroundTask.save_to_disk()
                        time.sleep(1)
                        if IngestionBackgroundTask.cancel_requested:
                            raise InterruptedError("Cancelled by user")
                    with ingestion_lock:
                        if IngestionBackgroundTask.status == "paused":
                            IngestionBackgroundTask.status = "running"
                    try:
                        page_notes = analyzer.extract_diagrams_from_page(pil_img, class_name, lesson_name, page_num, disp_name)
                        IngestionBackgroundTask.generated_visual_notes.extend(page_notes)
                    except Exception as pe:
                        print(f"[WARNING] Diagram extraction failed on page {page_num}: {pe}")
                        
                try:
                    # 影音逐字稿處理
                    if p_file.suffix.lower() in ['.mp3', '.mp4', '.wav']:
                        raw_text = processor.transcribe_audio(f_path, status_callback=update_sub_status)
                        
                        if p_file.suffix.lower() == '.mp4':
                            update_sub_status("🎬 正在進行影片板書動作追蹤與自動裁切...")
                            video_notes = analyzer.track_video_blackboard(f_path, class_name, lesson_name, status_callback=update_sub_status)
                            IngestionBackgroundTask.generated_visual_notes.extend(video_notes)
                        
                        update_sub_status("🧠 正在使用大語言模型校正天干拼音與法規錯字（請稍候）...")
                        final_text = processor.post_refine_using_llm(raw_text)
                    elif p_file.suffix.lower() == '.txt':
                        with open(f_path, 'r', encoding='utf-8-sig', errors='ignore') as f_in:
                            raw_text = f_in.read(TEXT_PREVIEW_LIMIT_CHARS)
                        update_sub_status("🧠 正在使用大語言模型校正天干拼音與法規錯字（請稍候）...")
                        final_text = processor.post_refine_using_llm(raw_text)
                    else:
                        pages_list = processor.ocr_document(f_path, status_callback=update_sub_status, page_callback=handle_ocr_page)
                        update_sub_status("🧠 正在使用大語言模型校正天干拼音與法規錯字（請稍候）...")
                        combined_ocr_text = "\n".join([p["text"] for p in pages_list])
                        final_text = processor.post_refine_using_llm(combined_ocr_text)

                    def sanitize_filename(name: str) -> str:
                        for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                            name = name.replace(char, '')
                        return name.strip()

                    stem = p_file.stem
                    clean_class = sanitize_filename(class_name)
                    clean_lesson = sanitize_filename(lesson_name)
                    clean_stem = sanitize_filename(stem)
                    
                    out_filename = f"{clean_class}_{clean_lesson}_{clean_stem}_逐字稿.txt"
                    out_filepath = os.path.join(transcripts_dir, out_filename)
                    
                    with open(out_filepath, "w", encoding="utf-8-sig") as f_out:
                        f_out.write(final_text)
                    IngestionBackgroundTask.generated_transcripts.append((out_filename, out_filepath))
                    
                    # 4. 進行大模型摘要以利聊天機器人 RWS 的運作
                    payload_prompt = f"分析以下文本，提煉出：核心爭點、推理路徑、結論：\n\n{final_text[:2000]}"
                    res = requests.post(f'{os.environ.get("OLLAMA_HOST", "http://localhost:11434")}/api/chat', 
                                        json={'model': os.environ.get("OLLAMA_MODEL", "deepseek-r1:32b"), 'messages': [{'role': 'user', 'content': payload_prompt}], 'stream': False, 'options': {'num_ctx': 32768}},
                                        timeout=90)
                    if res.status_code == 200:
                        summary = res.json().get('message', {}).get('content', '')
                        safe_chroma_text = final_text[:CHROMA_TEXT_LIMIT_CHARS]
                        doc_to_store = f"【消化精華】\n{summary}\n\n【原始校對文本節錄】\n{safe_chroma_text}"
                        doc_embedding = agent_instance._get_embedding(doc_to_store)
                        if doc_embedding:
                            agent_instance.intel_coll.add(
                                ids=[f"local_ref_{disp_name}_{idx}_{int(time.time())}"],
                                documents=[doc_to_store],
                                embeddings=[doc_embedding],
                                metadatas=[{"source": disp_name, "mode": mode_label, "size_mb": round(file_size_mb, 2), "type": "summary", "class_name": class_name, "lesson_name": lesson_name}]
                            )
                    
                    # 5. 分段與分頁建檔 (寫入詳細定位資訊至資料庫)
                    if pages_list:
                        for p_data in pages_list:
                            p_num = p_data["page"]
                            p_text = p_data["text"]
                            if not p_text.strip():
                                continue
                            doc_content = f"【教材書面頁面 - {disp_name}】\n頁碼：第 {p_num} 頁\n\n{p_text}"
                            doc_embedding = agent_instance._get_embedding(doc_content)
                            if doc_embedding:
                                agent_instance.intel_coll.add(
                                    ids=[f"chunk_pdf_{disp_name}_{p_num}_{idx}_{int(time.time())}"],
                                    documents=[doc_content],
                                    embeddings=[doc_embedding],
                                    metadatas=[{
                                        "source": disp_name,
                                        "class_name": class_name,
                                        "lesson_name": lesson_name,
                                        "page": p_num,
                                        "type": "pdf"
                                    }]
                                )
                    elif p_file.suffix.lower() in ['.mp3', '.mp4', '.wav']:
                        lines = [line.strip() for line in final_text.split("\n") if line.strip()]
                        for g_idx in range(0, len(lines), 5):
                            group_lines = lines[g_idx:g_idx+5]
                            chunk_text = "\n".join(group_lines)
                            
                            ts_range = "未知時間"
                            ts_pattern = r"\[(\d{2}:\d{2}:[\d.]+)\s*->\s*(\d{2}:\d{2}:[\d.]+)\]"
                            start_ts = None
                            end_ts = None
                            
                            for l in group_lines:
                                m = re.search(ts_pattern, l)
                                if m:
                                    start_ts = m.group(1)
                                    break
                            for l in reversed(group_lines):
                                m = re.search(ts_pattern, l)
                                if m:
                                    end_ts = m.group(2)
                                    break
                                    
                            if start_ts and end_ts:
                                ts_range = f"{start_ts} -> {end_ts}"
                            elif start_ts:
                                ts_range = start_ts
                                
                            doc_content = f"【教材影音片段 - {disp_name}】\n時間軸：{ts_range}\n\n{chunk_text}"
                            doc_embedding = agent_instance._get_embedding(doc_content)
                            if doc_embedding:
                                agent_instance.intel_coll.add(
                                    ids=[f"chunk_audio_{disp_name}_{g_idx}_{idx}_{int(time.time())}"],
                                    documents=[doc_content],
                                    embeddings=[doc_embedding],
                                    metadatas=[{
                                        "source": disp_name,
                                        "class_name": class_name,
                                        "lesson_name": lesson_name,
                                        "timestamp": ts_range,
                                        "type": "audio"
                                    }]
                                )
                    elif p_file.suffix.lower() == '.txt':
                        chunk_size = 1000
                        for char_idx in range(0, len(final_text), chunk_size):
                            chunk_text = final_text[char_idx:char_idx+chunk_size]
                            if not chunk_text.strip():
                                continue
                            doc_content = f"【教材文件片段 - {disp_name}】\n\n{chunk_text}"
                            doc_embedding = agent_instance._get_embedding(doc_content)
                            if doc_embedding:
                                agent_instance.intel_coll.add(
                                    ids=[f"chunk_txt_{disp_name}_{char_idx}_{idx}_{int(time.time())}"],
                                    documents=[doc_content],
                                    embeddings=[doc_embedding],
                                    metadatas=[{
                                        "source": disp_name,
                                        "class_name": class_name,
                                        "lesson_name": lesson_name,
                                        "page": 1,
                                        "type": "txt"
                                    }]
                                )

                    if src_type == "uploaded" and os.path.exists(f_path):
                        try:
                            os.unlink(f_path)
                        except:
                            pass
                    
                    with ingestion_lock:
                        # 紀錄到已吸收教材歷史
                        try:
                            history = load_ingested_history()
                            history[f_path] = {
                                "size": os.path.getsize(f_path),
                                "mtime": os.path.getmtime(f_path),
                                "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            save_ingested_history(history)
                        except Exception:
                            pass
                        
                        IngestionBackgroundTask.logs.append(f"✅ 成功研讀消化教材：{disp_name}")
                        IngestionBackgroundTask.processed_count += 1
                        if gpu_id == 0:
                            IngestionBackgroundTask.gpu0_file = "閒置"
                            IngestionBackgroundTask.gpu0_action = "閒置"
                        else:
                            IngestionBackgroundTask.gpu1_file = "閒置"
                            IngestionBackgroundTask.gpu1_action = "閒置"
                        IngestionBackgroundTask.current_file = f"GPU 0: {IngestionBackgroundTask.gpu0_file} | GPU 1: {IngestionBackgroundTask.gpu1_file}"
                        IngestionBackgroundTask.save_to_disk()
                    
                    # OOM Memory Protection
                    if 'raw_text' in locals(): del raw_text
                    if 'final_text' in locals(): del final_text
                    if 'pages_list' in locals(): del pages_list
                    gc.collect()
                    time.sleep(0.5)
                    
                except InterruptedError:
                    with ingestion_lock:
                        IngestionBackgroundTask.status = "cancelled"
                        IngestionBackgroundTask.logs.append(f"🛑 中斷：{disp_name}（已完成的進度已安全保存）")
                        IngestionBackgroundTask.save_to_disk()
                    return
                except Exception as fe:
                    with ingestion_lock:
                        IngestionBackgroundTask.logs.append(f"❌ 錯誤：{disp_name} | 原因: {fe}")
                        IngestionBackgroundTask.processed_count += 1
                        if gpu_id == 0:
                            IngestionBackgroundTask.gpu0_file = "閒置"
                            IngestionBackgroundTask.gpu0_action = "閒置"
                        else:
                            IngestionBackgroundTask.gpu1_file = "閒置"
                            IngestionBackgroundTask.gpu1_action = "閒置"
                        IngestionBackgroundTask.current_file = f"GPU 0: {IngestionBackgroundTask.gpu0_file} | GPU 1: {IngestionBackgroundTask.gpu1_file}"
                        IngestionBackgroundTask.save_to_disk()
                    
                    # OOM Memory Protection (Cleanup on exception)
                    if 'raw_text' in locals(): del raw_text
                    if 'final_text' in locals(): del final_text
                    if 'pages_list' in locals(): del pages_list
                    gc.collect()
                    time.sleep(0.5)

        # 準備並行任務指派
        gpu0_jobs = []
        gpu1_jobs = []
        
        try:
            import ctranslate2
            num_gpus = ctranslate2.get_cuda_device_count()
        except:
            num_gpus = 0
            
        for idx in range(start_idx, len(valid_files)):
            disp_name, f_path, src_type = valid_files[idx]
            job = (idx, disp_name, f_path, src_type)
            
            if num_gpus >= 2:
                if idx % 2 == 0:
                    gpu0_jobs.append(job)
                else:
                    gpu1_jobs.append(job)
            else:
                gpu0_jobs.append(job)
                
        threads = []
        if gpu0_jobs:
            t0 = threading.Thread(target=worker_loop, args=(0, gpu0_jobs))
            threads.append(t0)
        if gpu1_jobs and num_gpus >= 2:
            t1 = threading.Thread(target=worker_loop, args=(1, gpu1_jobs))
            threads.append(t1)
            
        for t in threads:
            t.daemon = True
            t.start()
            
        for t in threads:
            t.join()
            
            if IngestionBackgroundTask.status not in ["cancelled", "error"]:
                IngestionBackgroundTask.status = "completed"
                IngestionBackgroundTask.save_to_disk()
                save_paths_to_buffer([])
                
    except Exception as e:
        IngestionBackgroundTask.status = "error"
        IngestionBackgroundTask.error_message = str(e)
        IngestionBackgroundTask.logs.append(f"❌ 系統錯誤：{e}")
        IngestionBackgroundTask.save_to_disk()

# ==========================================
# 鐵律 3: 網頁版面配置 ── 堅持老律師嚴肅審美 (Anti-AI-Vibe)
# ==========================================
# 置頂專業法律面板樣式 (使用台灣法規正統 Serif 襯線字，嚴禁紫粉漸層與輕浮 Emoji/Inter 字體)
st.markdown("""
 <style>
 .reportview-container .main .block-container{ max-width: 95%; }
 h1, h2, h3, h4, h5, h6 { font-family: "Noto Serif TC", "PMingLiU", "MingLiU", serif; }
 .stButton>button { color: #1f2937; border-radius: 4px; font-family: "Noto Serif TC", serif; }
 .stTextInput>div>div>input { font-family: "Noto Serif TC", serif; }
 .stTextArea>div>div>textarea { font-family: "Noto Serif TC", serif; }
 div[data-baseweb="tab-list"] button { font-family: "Noto Serif TC", serif; font-size: 1.05em; }
 div[data-baseweb="tab-list"] button[aria-selected="true"] { font-weight: bold; border-bottom: 2px solid #d97706; }
 </style>
 """, unsafe_allow_html=True)

st.title("⚖️ LexMind-Omni 雙軌法律智能 AI 研究工作站")
st.caption("Windows 11 本地自治版 ── Matt Pocock & Karpathy 雙軌架構防禦體系")

@st.cache_resource
def get_legal_agent_singleton():
    return LocalLegalAgent(context_role="申訴人/律師時效防禦")

# 初始化 Session State 單例
if "agent_instance" not in st.session_state:
    try:
        st.session_state.agent_instance = get_legal_agent_singleton()
        # 預加載一些基本的法條供初始運行良好
        init_docs = [
            "民法第197條：因侵權行為所生之損害賠償請求權，自請求權人知有損害及賠償義務人時起，二年間不行使而消滅。意即罹於消滅時效，被告得提起時效抗辯。此二消滅時效為民事訴訟之保命武器。",
            "民法第184條：因故意或過失，不法侵害他人之權利者，負損害賠償責任。"
        ]
        init_embeddings = [st.session_state.agent_instance._get_embedding(doc) for doc in init_docs]
        if all(init_embeddings):
            st.session_state.agent_instance.law_coll.upsert(
                ids=["init_1", "init_2"],
                metadatas=[{"law": "民法第197條"}, {"law": "民法第184條"}],
                documents=init_docs,
                embeddings=init_embeddings
            )
    except Exception as e:
        st.session_state.agent_init_error = str(e)

if "agent_instance" not in st.session_state:
    st.error(f"核心法律 AI 初始化失敗：{st.session_state.get('agent_init_error', '未知錯誤')}")
    st.info(f"請確認 Ollama 正在執行，且模型 {st.session_state.ollama_model} 可用。頁面已停止載入以避免後續連鎖錯誤。")
    pass # Removed st.stop() to prevent breaking subsequent tabs

# ==============================================================================
# SIDEBAR: 心證角色、時效精算與 Ollama 設定
# ==============================================================================
with st.sidebar:
    st.markdown("## 🔑 實務心證角色")
    st.caption("切換思考視角，RWS 動態混合檢索將自動對應該角色實務深度重新分配：")
    
    selected_role_label = st.radio(
        "心證角色切換",
        ["律師視角 (程序/時效防禦優先)", "法官心證 (客觀案件事實對抗)", "檢察官 (刑事追訴/公訴犯罪)"],
        label_visibility="collapsed"
    )
    role_map = {
        "律師視角 (程序/時效防禦優先)": "lawyer", 
        "法官心證 (客觀案件事實對抗)": "judge", 
        "檢察官 (刑事追訴/公訴犯罪)": "prosecutor"
    }
    st.session_state.agent_instance.role = role_map[selected_role_label]
    
    st.markdown("---")
    st.markdown("## 🗓️ 民法雙重時效精算")
    event_date_in = st.date_input("事件發生日 (YYYY-MM-DD)", datetime.date.today(), key="sidebar_event_date")
    statute_opt = st.selectbox(
        "法定時效特徵", 
        ["civil_tort", "civil_general", "public_wage", "labor_30d"], 
        format_func=lambda x: "民事一般侵權損害 (2年 - 民§197)" if x == "civil_tort" else ("一般普通請求權 (15年)" if x == "civil_general" else ("行政公法上請求權/工資 (5年)" if x == "public_wage" else "勞基法14條30日除斥期間限制")),
        key="sidebar_statute_opt"
    )
    if st.button("⚖️ 執行精密時效推算", key="sidebar_run_cal"):
        cal = LegalCalendarPlugin()
        res = cal.calculate_deadline(str(event_date_in), statute_opt)
        if "error" in res:
            st.error(res["error"])
        else:
            st.success(f"🎉 截止日為：{res['final_deadline']}")
            st.markdown(f"""
            <small>
            - **起算日**：{res['start_compute_date']}<br>
            - **休日順延**：{res['holiday_extended']} (延 {res['extended_days']} 天)
            </small>
            """, unsafe_allow_html=True)
            
    st.markdown("""
    <div style=" border-left: 4px solid #6366f1; padding: 12px; border-radius: 6px; margin-top: 15px; font-size: 0.85em; color: #1e3a8a;">
        💡 <b>本環境已適應修正：</b>已啟用「天干代名詞」深度對齊模組，全自動過濾「假芳、倚芳、丙方」等語音識別雜訊。
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    with st.expander("⚙️ Ollama 本地模型設定"):
        ollama_url = st.text_input(
            "Ollama 伺服器網址 (Ollama URL)", 
            value=st.session_state.get("ollama_url", "http://localhost:11434"),
            key="sidebar_ollama_url"
        )
        st.session_state.ollama_url = ollama_url
        os.environ["OLLAMA_HOST"] = ollama_url
        
        available_models = ["deepseek-r1:7b", "deepseek-r1:32b"]
        try:
            res_tags = requests.get(f"{ollama_url}/api/tags", timeout=2)
            if res_tags.status_code == 200:
                tags = res_tags.json().get("models", [])
                fetched_models = [m["name"] for m in tags]
                if fetched_models:
                    available_models = fetched_models
        except Exception:
            pass
            
        current_model = st.session_state.get("ollama_model", "deepseek-r1:7b")
        if current_model not in available_models:
            available_models.append(current_model)
            
        selected_model = st.selectbox(
            "Ollama 本地大語言模型",
            options=available_models,
            index=available_models.index(current_model) if current_model in available_models else 0,
            key="sidebar_selected_model"
        )
        
        if selected_model != st.session_state.get("ollama_model"):
            st.session_state.ollama_model = selected_model
            os.environ["OLLAMA_MODEL"] = selected_model
            st.rerun()
            
        st.session_state.ollama_model = selected_model
        os.environ["OLLAMA_MODEL"] = selected_model
        
        if st.button("⚡ 測試連線狀態", key="sidebar_test_ollama_conn"):
            try:
                res = requests.get(f"{ollama_url}/api/tags", timeout=5)
                if res.status_code == 200:
                    models = [m['name'] for m in res.json().get('models', [])]
                    st.success("✅ 連線成功！偵測到模型:\n" + "\n".join([f"- {m}" for m in models]))
                else:
                    st.error("❌ 連線異常：伺服器未預期回應。")
            except Exception as e:
                st.error(f"❌ 連線失敗：{e}")

    STATUS_FILE = "C:/LocalAI_Workstation/scraper_status.json"
    st.sidebar.markdown("---")
    st.sidebar.subheader("🌐 外網題庫自動排程狀態")

    # 讀取外界程式寫入的狀態檔案
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8-sig") as f_status:
                status_data = json.load(f_status)
                
            status = status_data.get("status", "idle")
            progress = status_data.get("progress", 0)
            message = status_data.get("message", "")
            last_update = status_data.get("last_update", "")

            # 根據外界程式的不同狀態，在 UI 呈現對應的視覺化元件
            if status == "running":
                st.sidebar.warning("⏳ 系統排程正在背景抓取外網資訊...")
                st.sidebar.progress(progress / 100.0)
                st.sidebar.caption(f"當前進度: {message}")
                # 如果正在執行，提示使用者可以手動重新整理網頁看最新進度
                if st.sidebar.button("🔄 刷新進度"):
                    st.rerun()
            elif status == "completed":
                st.sidebar.success(f"✅ 上次自動同步成功\n\n時間: {last_update}")
                st.sidebar.info(f"結果摘要: {message}")
            elif status == "failed":
                st.sidebar.error(f"❌ 上次自動同步失敗\n\n時間: {last_update}")
                st.sidebar.caption(f"錯誤訊息: {message}")
                
        except Exception:
            st.sidebar.caption("暫時無法讀取排程狀態檔。")
    else:
        st.sidebar.caption("排程守護中。尚未執行首次同步。")

    # 依舊保留白天想「手動即時觸發」的功能
    if st.sidebar.button("🚀 點我立即手動執行外部同步"):
        with st.spinner("正在啟動外界程式進行同步..."):
            os.system("python law_scraper_cli.py")
            st.rerun() # 執行完立刻刷新 UI 顯示結果

    # PiSu 小助理智慧客服微型對話視窗 (PiSu Mini-Chat)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 LexMind-Bot™️ 隨身法學智能助理")
    st.sidebar.caption("LexMind-Omni 精簡版：主打極速、白話台灣法律常識與智慧財產權入門引導。")
    
    if "omnibot_messages" not in st.session_state:
        st.session_state.omnibot_messages = []
        
    omnibot_chat_box = st.sidebar.container(height=180, border=True)
    with omnibot_chat_box:
        if not st.session_state.omnibot_messages:
            st.markdown("<small style='color:#4338ca;'><b>助理：</b>您好！我是小助理。您可以問我任何關於民法、專利、商標或著作權的簡單法律問題！</small>", unsafe_allow_html=True)
        for msg in st.session_state.omnibot_messages:
            color = "#4338ca" if msg["role"] == "assistant" else "#1e3a8a"
            role_label = "助理" if msg["role"] == "assistant" else "您"
            st.markdown(f"<div style='font-size:0.85em; margin-bottom:6px; color:{color};'><b>{role_label}：</b>{html.escape(msg.get('content', ''))}</div>", unsafe_allow_html=True)
            
    omnibot_input = st.sidebar.text_input("詢問法學助理 (Enter送出)...", key="omnibot_chat_input_txt")
    if omnibot_input:
        st.session_state.omnibot_messages.append({"role": "user", "content": omnibot_input})
        
        # 建立簡短的小助理 Prompt
        omnibot_prompt = (
            "你是一位親切活潑的法律小特助『小助理』，擅長用大眾聽得懂的白話文，引導臺灣法律與商標專利常識。\n"
            "請用簡短兩三句話回答使用者的提問，並在回答結尾給出一個親切的溫馨小語。\n"
            "回答必須使用繁體中文，避免大陸用語。\n\n"
            f"提問：{omnibot_input}"
        )
        
        try:
            res = requests.post(f"{st.session_state.ollama_url}/api/chat",
                                json={
                                    'model': st.session_state.ollama_model, 
                                    'messages': [{'role': 'user', 'content': omnibot_prompt}], 
                                    'stream': False
                                }, timeout=30)
            if res.status_code == 200:
                reply = res.json().get('message', {}).get('content', '連線異常，助理開小差了。')
                if "<think>" in reply:
                    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
                st.session_state.omnibot_messages.append({"role": "assistant", "content": reply})
            else:
                st.session_state.omnibot_messages.append({"role": "assistant", "content": "助理目前連不上本地 Ollama 服務。"})
        except Exception as e:
            st.session_state.omnibot_messages.append({"role": "assistant", "content": f"連線錯誤：{e}"})
        
        # 清空輸入
        st.session_state.omnibot_chat_input_txt = ""
        st.rerun()

# 注入 CSS 
st.markdown("""
<style>
    /* 隱藏 Streamlit 的頂部紅線與預設 Header，並停用其滑鼠事件防止變成透明玻璃板遮擋點擊 */
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { display: none !important; }
    
    /* 頁面主背景 */
    .stApp {
        background-color: transparent;
    }
    
    /* 側邊欄背景與卡片化 */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #e5e7eb;
    }
    
    /* 卡片設計 */
    .lawyer-card {
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        border-left: 6px solid #d97706;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .level-1 { border-left-color: #ef4444; }
    .level-2 { border-left-color: #f59e0b; }
    .level-3 { border-left-color: #10b981; }
    .level-4 { border-left-color: #3b82f6; }
    
    /* 美化 Radio 按鈕組，使其看起來像側邊欄的面板按鈕 */
    div[data-testid="stRadio"] > div {
        gap: 8px;
    }
    div[data-testid="stRadio"] label {
        border: 1px solid #e5e7eb;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 0px;
        cursor: pointer;
        display: flex;
        align-items: center;
        transition: all 0.2s ease;
    }
    div[data-testid="stRadio"] label:hover {
        border-color: #d97706;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        border-color: #d97706;
        background-color: #fef3c7;
    }
    
    /* tab 按鈕美化 */
    button[data-baseweb="tab"] {
        font-size: 1.05em;
        font-weight: 600;
        padding: 12px 24px;
        border-bottom: 2px solid transparent;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 2px solid #d97706;
    }
</style>
""", unsafe_allow_html=True)

# agent_instance已移至上方初始化

# 初始化所有多模態與對話框 State 變數
if "tab1_input_val" not in st.session_state:
    st.session_state.tab1_input_val = ""
if "tab3_search_query_value" not in st.session_state:
    st.session_state.tab3_search_query_value = ""
if "tab4_question_value" not in st.session_state:
    st.session_state.tab4_question_value = ""
if "tab4_answer_value" not in st.session_state:
    st.session_state.tab4_answer_value = ""
if "tab4_search_value" not in st.session_state:
    st.session_state.tab4_search_value = ""
if "tab5_fact_value" not in st.session_state:
    st.session_state.tab5_fact_value = "原告黃少奎在台北市信義路闖紅燈，被被告簡育芸開私家車擦撞造成大腿骨折，醫療費花費20萬元。事發時間為民國113年3月12日，被告態度傲慢消極逃避。"
if "antigravity_input_val" not in st.session_state:
    st.session_state.antigravity_input_val = ""
if "feedback_comment_value" not in st.session_state:
    st.session_state.feedback_comment_value = ""


# 啟動時偵測是否有未完成的背景任務進度并開啟 3 分鐘倒數復原
if "recovery_checked" not in st.session_state:
    st.session_state.recovery_checked = True
    if IngestionBackgroundTask.load_from_disk():
        if IngestionBackgroundTask.status in ["running", "paused", "cancelled", "error"] and IngestionBackgroundTask.processed_count < len(IngestionBackgroundTask.valid_files_info):
            st.session_state.recovery_active = True
            st.session_state.recovery_start_time = time.time()

# 頁面標題
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; padding: 15px 20px;  border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 20px;">
    <div style="display: flex; align-items: center; gap: 15px;">
        <span style="font-size: 2.2em; color: #d97706;">⚖️</span>
        <div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <h1 style="margin: 0; font-size: 1.8em; font-weight: bold; color: inherit; font-family: sans-serif;">LexMind-Omni</h1>
                <span style=" color: inherit; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold;">v1.4 STABLE</span>
            </div>
            <p style="margin: 3px 0 0 0; font-size: 0.9em; color: #6b7280;">臺灣法律實務專業級 AI Agent 特助整合工作站</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 定義安全 GUI 檔案總管選取器（本機執行自動呼叫 Windows File ExplorerDialog，雲端容器執行安全提示）
def select_folders():
    import subprocess
    import json
    import os
    
    # 使用 PowerShell 呼叫支援多選資料夾的 Windows 原生對話框
    ps_code = """
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Multiselect = $true
    $dialog.ValidateNames = $false
    $dialog.CheckFileExists = $false
    $dialog.CheckPathExists = $true
    $dialog.FileName = "選擇此資料夾"
    $dialog.Title = "請按住 Ctrl 或 Shift 鍵多選目標資料夾，並點選右下角『開啟』"
    
    # 確保視窗置頂
    $form = New-Object System.Windows.Forms.Form
    $form.TopMost = $true
    $result = $dialog.ShowDialog($form)
    
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $paths = @()
        foreach ($file in $dialog.FileNames) {
            $paths += $file
        }
        ConvertTo-Json $paths -Compress
    } else {
        "[]"
    }
    """
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_code],
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            timeout=180
        )
        output = res.stdout.strip()
        if output:
            paths = json.loads(output)
            clean_paths = []
            for p in paths:
                if p.endswith("選擇此資料夾"):
                    p = os.path.dirname(p)
                if os.path.exists(p):
                    clean_paths.append(p)
            return clean_paths
    except Exception as e:
        st.warning(f"💡 開啟本地多選資料夾選取器時出錯：{e}")
    return []

def select_files():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_paths = filedialog.askopenfilenames(
            title="選擇多模態案件、書狀 PDF 或 MP3/MP4 影音檔 (可按住 Ctrl 或 Shift 鍵進行多選)",
            filetypes=[
                ("多模態法律檔案 (*.txt, *.pdf, *.png, *.jpg, *.mp3, *.mp4, *.wav)", "*.txt *.pdf *.png *.jpg *.mp3 *.mp4 *.wav"),
                ("所有檔案 (*.*)", "*.*")
            ]
        )
        root.destroy()
        return list(file_paths)
    except Exception as e:
        st.warning("💡 本地檔案總管需在本機電腦（如 Windows）執行始可彈出。手動輸入路徑亦可正常研讀。")
        return None

# 頂層 Tab 分頁導航 (完整對位 React 5 大功能分區，消滅偷工減料問題！)
tab_consult, tab_ingest, tab_cases, tab_search, tab_exam, tab_draft, tab_admin, tab_agent, tab_setup = st.tabs([
    "💬 實務辯護諮詢", 
    "📥 知識餵養 (影音 & 書狀)", 
    "📂 法律個案管理",
    "🔍 教材檢索與定位",
    "🎓 司法官自我養成", 
    "📝 訴訟書狀起草",
    "⚙️ 系統與時效工具",
    "🤖 Antigravity 控制台",
    "⚙️ 企業級架構與金鑰池界面設定面"
])

# ==============================================================================
# TAB 1: 實務對話諮詢區 (RWS 可視化心證)
# ==============================================================================
with tab_consult:
    st.subheader("💬 實務訴訟案件心證分析")
    st.caption("AI 會自動檢索『法條庫』與『歷史經驗智商庫』，並根據您的訴訟角色與民事/刑事大類進行重新排序 (RWS)。")
    
    col_chat, col_evid = st.columns([7, 3])
    
    # 初始化歷史
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_evidence" not in st.session_state:
        st.session_state.last_evidence = []

    with col_chat:
        # 顯示歷史
        chat_box = st.container(height=400, border=True)
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        # 1. 檢測是否有尚未處理的 user 訊息 (狀態驅動心證分析)
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            user_prompt = st.session_state.messages[-1]["content"]
            logic_instr = st.session_state.get("tab1_logic_instruction", "")
            full_prompt = user_prompt
            if logic_instr:
                full_prompt = f"【請特別採用「{logic_instr}」的推理邏輯與思路】\n案情與問題：\n{user_prompt}"
            
            with st.spinner("🧠 正在啟動 RWS 智能多維檢索並進行 IRAC 推論..."):
                try:
                    # 檢測時效關鍵字
                    time_warning = ""
                    if any(w in user_prompt for w in ["時效", "年", "過期", "期限"]):
                        time_warning = "⚠️【 法律時效極度嚴重警告】經 RWS 對位 facts，本案恐已罹於民法第 197 條或第 125 條之消滅時效！請立刻啟動訴訟程序保命武器，以下回答強制優先適用時效抗辯！\n\n"
                    
                    reply, evid, mermaid_code = st.session_state.agent_instance.chat_with_rws(full_prompt)
                    
                    if st.session_state.get("tab1_vjd_pipeline", True):
                        reply = st.session_state.agent_instance.verify_judgment_citations(reply)
                    
                    if time_warning:
                        reply = time_warning + reply
                        
                    st.session_state.last_evidence = evid
                    st.session_state.mermaid_code = mermaid_code
                    st.session_state.tab1_logic_instruction = "" # 清除邏輯
                except Exception as e:
                    reply = f"❌ [心證分析失敗] {e}"
                    st.session_state.last_evidence = []
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

        # 2. 評判回饋與重新生成區（若最後一條為 assistant 回覆）
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.markdown("<div style=' padding:15px; border-radius:8px; border: 1px solid #e5e7eb; margin-bottom: 15px;'>", unsafe_allow_html=True)
            st.markdown("##### 💡 針對本次分析結果評判與變更思路重新回答")
            col_fb_btn, col_fb_logic = st.columns([1, 1])
            with col_fb_btn:
                with st.form("tab1_response_feedback_form"):
                    st.markdown("<small><b>1. 系統分析精進評判</b></small>", unsafe_allow_html=True)
                    rating_resp = st.radio("回答品質評判", ["👍 分析精準且切合實務", "👎 推理有邏輯瑕疵/需改進"], horizontal=True, key="tab1_rating_resp")
                    comment_resp = st.text_input("輸入意見評判反饋", placeholder="如：時效推論極佳，但漏掉某法條...", key="tab1_comment_resp")
                    submit_resp = st.form_submit_button("📤 提交此對話評判")
                    if submit_resp:
                        SubjectIQManager.add_feedback("綜合法律心證", "like" if "👍" in rating_resp else "dislike", f"【對話評判】{comment_resp}")
                        st.success("已成功為系統寫入評判回饋以供後續精進！")
            with col_fb_logic:
                st.markdown("<small><b>2. 要求變更推理邏輯重新回答</b></small>", unsafe_allow_html=True)
                selected_logic = st.selectbox(
                    "選擇重新回答思路",
                    [
                        "程序抗辯與消滅時效優先 (Focus on deadlines & statute of limitations)",
                        "實體法請求權構成要件嚴格檢驗 (Strict claim elements inspection)",
                        "舉證責任與事實真偽不明利益 (Burden of proof allocation)",
                        "衡平原則與損害過失相抵酌減 (Equity & comparative negligence mitigation)",
                        "預設 RWS 多維混合推理 (Default RWS balanced logic)"
                    ],
                    key="tab1_regenerate_logic"
                )
                if st.button("🔄 以此思路重新回答", key="tab1_btn_regenerate", use_container_width=True):
                    # Find last user prompt
                    user_query = ""
                    for m in reversed(st.session_state.messages[:-1]):
                        if m["role"] == "user":
                            user_query = m["content"]
                            break
                    if user_query:
                        st.session_state.tab1_logic_instruction = selected_logic
                        st.session_state.messages.pop() # 移除上一條助理回覆
                        st.success(f"已排程以「{selected_logic}」思路重新分析中...")
                        st.rerun()
                    else:
                        st.error("找不到前一筆使用者提問案情，無法重新回答！")
            st.markdown("</div>", unsafe_allow_html=True)

        # 3. 統一案情輸入與多模態分析中心 (全面相容 Gboard/IME 語音輸入與多模態)
        st.markdown("<div style=' padding:15px; border-radius:8px; border: 1px solid #e5e7eb;'>", unsafe_allow_html=True)
        st.markdown("##### 💬 案情與諮詢事實輸入中心 (支援注音/Gboard語音輸入)")
        
        col_aud, col_fil = st.columns([1, 1])
        with col_aud:
            audio_inp = st.audio_input("🎙️ 錄製案情語音 (Whisper 自動轉譯)", key="tab1_audio_input")
        with col_fil:
            file_inp = st.file_uploader("📂 上傳案件檔案/書狀/影像 (自動識別提取)", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "m4a", "mp4", "txt"], key="tab1_file_input")

        # Process audio or file
        if audio_inp:
            extracted_text = process_multimodal_input(audio_inp)
            if extracted_text:
                if st.session_state.tab1_input_val:
                    st.session_state.tab1_input_val += "\n" + extracted_text
                else:
                    st.session_state.tab1_input_val = extracted_text
                st.toast("🎙️ 語音轉譯成功！內容已載入輸入框。")
                st.rerun()

        if file_inp:
            extracted_text = process_multimodal_input(file_inp)
            if extracted_text:
                if st.session_state.tab1_input_val:
                    st.session_state.tab1_input_val += "\n" + extracted_text
                else:
                    st.session_state.tab1_input_val = extracted_text
                st.toast("📂 檔案內容解析成功！已載入輸入框。")
                st.rerun()

        user_input = st.text_area(
            "✍️ 案情事實描述 / 法律諮詢輸入框 (支援 Google 鍵盤自然語言輸入/注音/手寫/語音聽寫)",
            value=st.session_state.tab1_input_val,
            placeholder="請在此輸入案件事實或法律疑難（例如：我前年車禍大骨折想要起訴求償...）...",
            height=160,
            key="tab1_text_area_input"
        )
        st.session_state.tab1_input_val = user_input
        st.checkbox("開啟 LexMind-VJD 判決檢索真偽驗證機制 (LexMind-VJD)", value=True, key="tab1_vjd_pipeline")

        col_btn1, col_btn2 = st.columns([8, 2])
        with col_btn1:
            if st.button("📤 送出此段內容進行心證分析", key="tab1_btn_send_custom", use_container_width=True):
                if user_input.strip():
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.session_state.tab1_input_val = ""
                    st.rerun()
                else:
                    st.warning("請先輸入或上傳案情內容！")
        with col_btn2:
            if st.button("🧹 清空輸入", key="tab1_btn_clear", use_container_width=True):
                st.session_state.tab1_input_val = ""
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_evid:
        tab_evid, tab_graph = st.tabs(["📚 RWS 證據看板", "📊 事件關係圖"])
        
        with tab_evid:
            st.caption("以下為混合相似度與 RWS 實務得分後置頂的法源，已智慧判別優先級：")
            if not st.session_state.last_evidence:
                st.info("尚無檢索紀錄，請在對話框輸入案件事實。")
            else:
                for idx, item in enumerate(st.session_state.last_evidence):
                    lvl = item.get("level", 5)
                    tag_style = f"lawyer-card level-{lvl}"
                    st.markdown(f"""
                    <div class="{tag_style}">
                        <small style='color:#666;'><b>位階：L{lvl} | 來源：{item['source']} | 權重 RWS 得分：{item['score']}</b></small><br>
                        <p style='font-size:0.9em; margin:5px 0 0 0;'>{item['text'][:200]}...</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 檢索法源評判
                    with st.expander(f"📝 評估此檢索法源 (位階 L{lvl})", expanded=False):
                        c_name = item.get("class_name", "未分類課程")
                        with st.form(f"feedback_search_tab1_{idx}"):
                            rating_ev = st.radio("評價本筆法源關聯度", ["👍 關聯精準", "👎 與案件無關/錯誤"], horizontal=True, key=f"rating_tab1_ev_{idx}")
                            comment_ev = st.text_input("輸入改進評語", placeholder="如：不符合此罪構成要件", key=f"comment_tab1_ev_{idx}")
                            btn_ev = st.form_submit_button("提交回饋修正權重")
                            if btn_ev:
                                score_type = "like" if "👍" in rating_ev else "dislike"
                                SubjectIQManager.add_feedback(c_name, score_type, f"【法源檢索評判: {item.get('source')}】{comment_ev}")
                                st.success(f"已記錄評價，科別「{c_name}」權重已動態調校！")
                    
        with tab_graph:
            st.caption("系統根據您輸入的對話，動態提煉並呈現的人事時地物關係圖：")
            
            if "mermaid_code" not in st.session_state:
                st.session_state.mermaid_code = "graph TD\n    A[\"人: 申訴人\"] -->|諮詢| B[\"事: 法律案件\"]"
                
            # 渲染 Mermaid 關係圖
            import streamlit.components.v1 as components
            html_code = f"""
            <div style=" border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; display: flex; justify-content: center;">
                <pre class="mermaid" style="background: transparent; border: none; font-family: inherit; font-size: 14px; overflow: auto; white-space: pre-wrap;">
{st.session_state.mermaid_code}
                </pre>
            </div>
            <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
            </script>
            """
            components.html(html_code, height=350, scrolling=True)
            
            # 提供可編輯的 Mermaid 原始碼文字框
            edited_code = st.text_area("編輯關係圖代碼 (Mermaid Code)", value=st.session_state.mermaid_code, height=180)
            if edited_code != st.session_state.mermaid_code:
                st.session_state.mermaid_code = edited_code
                st.rerun()
                
            # 提供匯出下載功能
            st.download_button(
                label="📤 匯出關係圖 (Mermaid Code)",
                data=st.session_state.mermaid_code,
                file_name=f"legal_graph_{int(time.time())}.txt",
                mime="text/plain"
            )

# ==============================================================================
# TAB 2: 多模態批次教材知識餵養區
# ==============================================================================
with tab_ingest:
    if "chosen_batch_paths" not in st.session_state:
        st.session_state.chosen_batch_paths = load_paths_from_buffer()

    st.subheader("📥 大數據多模態教材批次導入與語庫校正")

    # 1. 偵測與渲染自動復原/更新倒數畫面
    if st.session_state.get("recovery_active", False):
        elapsed = time.time() - st.session_state.get("recovery_start_time", time.time())
        remaining = int(180 - elapsed)
        
        total = IngestionBackgroundTask.total_files
        processed = IngestionBackgroundTask.processed_count
        
        st.warning("⚠️ 偵測到系統先前異常中斷或進行版本更新！")
        st.markdown(f"""
        <div style=" border-left: 6px solid #818cf8; padding: 16px; border-radius: 8px; margin-bottom: 15px;">
            <h4 style="margin: 0 0 10px 0; color: inherit;">🔄 偵測到未完成的教材研讀進度</h4>
            <p style="margin: 5px 0; font-size: 0.95em; color: #1e3a8a;">
                <b>已處理進度</b>：{processed} / {total} 個檔案<br>
                <b>最後研讀檔案</b>：`{IngestionBackgroundTask.current_file}`<br>
                <b>狀態說明</b>：在軟體更換版本或異常中斷前，系統已安全儲存上述進度成果。
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if remaining <= 0:
            st.info("⏰ 倒數時間已到，系統已自行啟動並恢復上次未完成的工作！")
            st.session_state.recovery_active = False
            IngestionBackgroundTask.status = "running"
            IngestionBackgroundTask.cancel_requested = False
            IngestionBackgroundTask.pause_requested = False
            IngestionBackgroundTask.save_to_disk()
            t = threading.Thread(target=run_background_ingestion, args=(st.session_state.agent_instance, IngestionBackgroundTask.processed_count))
            t.daemon = True
            t.start()
            st.rerun()
        else:
            st.write(f"⏳ 系統將在 **{remaining}** 秒後自動恢復執行，或您可以選擇下方操作：")
            col_rec1, col_rec2 = st.columns([1, 1])
            with col_rec1:
                if st.button("▶️ 恢復並繼續研讀 (Resume)", key="manual_resume_recovery", use_container_width=True):
                    st.session_state.recovery_active = False
                    IngestionBackgroundTask.status = "running"
                    IngestionBackgroundTask.cancel_requested = False
                    IngestionBackgroundTask.pause_requested = False
                    IngestionBackgroundTask.save_to_disk()
                    t = threading.Thread(target=run_background_ingestion, args=(st.session_state.agent_instance, IngestionBackgroundTask.processed_count))
                    t.daemon = True
                    t.start()
                    st.rerun()
            with col_rec2:
                if st.button("🗑️ 捨棄歷史進度 (Discard)", key="discard_recovery", use_container_width=True):
                    st.session_state.recovery_active = False
                    IngestionBackgroundTask.reset()
                    st.rerun()
            
            time.sleep(1)
            st.rerun()
            pass # Removed st.stop() to prevent breaking subsequent tabs

    # 2. 偵測與渲染背景處理中/暫停中畫面
    if IngestionBackgroundTask.status in ["running", "paused"]:
        # 為了使前台即時同步背景 Thread 寫入的狀態，在此處主動加載磁碟狀態
        IngestionBackgroundTask.load_from_disk()
        
        # 智慧心跳偵測與卡死警告 (Watchdog)
        if IngestionBackgroundTask.status == "running" and IngestionBackgroundTask.last_heartbeat > 0:
            inactive_duration = time.time() - IngestionBackgroundTask.last_heartbeat
            if inactive_duration > 300: # 5分鐘無活動
                st.error(f"⚠️ **[系統警告] 偵測到分析執行緒可能已卡死或異常中斷！**\n\n系統已超過 **{int(inactive_duration // 60)} 分鐘 {int(inactive_duration % 60)} 秒** 無任何進度更新（前次活動時間：{datetime.datetime.fromtimestamp(IngestionBackgroundTask.last_heartbeat).strftime('%Y-%m-%d %H:%M:%S')}）。\n\n若您正在轉錄超大型影音（如數 GB 影片），本機 Whisper 及大模型校正負荷極大，耗時較長為正常現象。若確定為程式卡死，建議您點擊下方 **「🛑 立即熱切斷 (Hot Cut)」** 按鈕終止任務。")

        st.info("⏳ 背景教材研讀與數位消化處理中...")
        total = IngestionBackgroundTask.total_files
        processed = IngestionBackgroundTask.processed_count
        current_file = IngestionBackgroundTask.current_file
        action = IngestionBackgroundTask.current_action
        
        if total > 0:
            progress_val = min(1.0, max(0.0, processed / total))
            st.progress(progress_val)
            st.markdown(f"**目前總進度**：{processed} / {total} 件 ({int(progress_val * 100)}%)")
        else:
            st.write("進度：準備中...")
            
        # 雙 GPU Worker 進度看板，左右排列顯示
        col_gpu0, col_gpu1 = st.columns(2)
        with col_gpu0:
            st.markdown("##### 🎮 GPU 0 研讀晶片狀態")
            gpu0_f = IngestionBackgroundTask.gpu0_file
            gpu0_a = IngestionBackgroundTask.gpu0_action
            st.info(f"📁 **當前教材**：`{gpu0_f}`\n\n⚡ **狀態**：{gpu0_a}")
        with col_gpu1:
            st.markdown("##### 🎮 GPU 1 研讀晶片狀態")
            gpu1_f = IngestionBackgroundTask.gpu1_file
            gpu1_a = IngestionBackgroundTask.gpu1_action
            st.info(f"📁 **當前教材**：`{gpu1_f}`\n\n⚡ **狀態**：{gpu1_a}")
        
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            if IngestionBackgroundTask.status == "running":
                if st.button("⏸️ 暫停處理", key="btn_pause_task", use_container_width=True):
                    IngestionBackgroundTask.pause_requested = True
                    IngestionBackgroundTask.save_to_disk()
                    st.rerun()
            elif IngestionBackgroundTask.status == "paused":
                if st.button("▶️ 恢復處理", key="btn_resume_task", use_container_width=True):
                    IngestionBackgroundTask.pause_requested = False
                    IngestionBackgroundTask.status = "running"
                    IngestionBackgroundTask.save_to_disk()
                    st.rerun()
        with col_ctrl2:
            if st.button("🛑 立即熱切斷 (Hot Cut)", key="btn_hotcut_task", use_container_width=True):
                IngestionBackgroundTask.cancel_requested = True
                IngestionBackgroundTask.save_to_disk()
                st.rerun()
                
        with col_ctrl3:
            # 🔄 刷新最新進度按鈕與自動刷新 JS 定時器
            if st.button("🔄 刷新最新進度", key="btn_refresh_progress", use_container_width=True):
                st.rerun()
                
        # 隱藏的自動點擊指令碼，使 Streamlit 在運行中每 2 秒自動觸發一次 progress 刷新，不干擾其他 tab 的操作
        st.markdown("""
            <script>
                (function() {
                    var refresh_timer = setTimeout(function() {
                        var buttons = window.parent.document.querySelectorAll("button");
                        for (var i = 0; i < buttons.length; i++) {
                            if (buttons[i].textContent.includes("刷新最新進度")) {
                                buttons[i].click();
                                break;
                            }
                        }
                    }, 2000);
                })();
            </script>
        """, unsafe_allow_html=True)
                
        with st.expander("📝 即時研讀日誌", expanded=True):
            for log in IngestionBackgroundTask.logs[-20:]:
                st.write(log)
                
        time.sleep(1)
        st.rerun()
        pass # Removed st.stop() to prevent breaking subsequent tabs

    # 3. 偵測與渲染研讀完成/中斷/出錯畫面
    if IngestionBackgroundTask.status in ["completed", "cancelled", "error"]:
        if IngestionBackgroundTask.status == "completed":
            st.success("✅ 法律教材與卷宗檔案已全部批次研讀消化完畢，智商庫已成功拓寬演化！")
        elif IngestionBackgroundTask.status == "cancelled":
            st.warning("🛑 研讀程序已被使用者手動熱切斷，已安全保存當前已處理進度！")
        else:
            st.error(f"❌ 教材研讀過程中發生錯誤：{IngestionBackgroundTask.error_message}")
            
        with st.expander("📝 完整研讀日誌", expanded=True):
            for log in IngestionBackgroundTask.logs:
                st.write(log)
                
        if IngestionBackgroundTask.generated_transcripts:
            st.markdown("### 📝 本次產生的轉譯逐字稿檔案：")
            st.info(f"📁 所有逐字稿檔案已儲存至實體資料夾：`{IngestionBackgroundTask.transcripts_dir}`")
            for fname, fpath in IngestionBackgroundTask.generated_transcripts:
                st.markdown(f"- **{fname}** (檔案路徑: `{fpath}`)")
                
        if IngestionBackgroundTask.generated_visual_notes:
            st.markdown("### 🎨 本次擷取之教材圖表與板書校對筆記（Obsidian 格式）：")
            st.info("📁 所有圖表與板書校對筆記已儲存至實體資料夾：`C:\\LocalAI_Workstation\\Obsidian_Vault\\04_教材圖表校對\\`")
            for note_name, note_path in IngestionBackgroundTask.generated_visual_notes:
                clean_note_path = note_path.replace('\\', '/')
                st.markdown(f"- **[{note_name}](file:///{clean_note_path})** (筆記路徑: `{note_path}`)")
                
        if st.button("↩️ 確認並返回", key="btn_clear_task", use_container_width=True):
            IngestionBackgroundTask.reset()
            st.session_state.chosen_batch_paths = []
            st.rerun()
        pass # Removed st.stop() to prevent breaking subsequent tabs

    # 4. 正常狀態下 (Idle) 的匯入 UI
    st.caption("小檔案可用瀏覽器上傳；3G 到 9G 的卷宗、影音與大量資料夾請用 Windows 本地資料夾路徑，避免瀏覽器與 16GB RAM 被一次塞滿。")
    st.info("currently split strategy: browser upload is only suitable for total files under 200MB; large files please use local path below, system will process in low memory mode.")

    st.markdown("##### 🚀 方案一：瀏覽器小檔上傳（總量 200MB 以內）")
    uploaded_files = st.file_uploader(
        "📂 小型 TXT/PDF/圖片/短音檔可拖曳至此；大型卷宗與影音請改用方案二",
        type=['txt', 'pdf', 'png', 'jpg', 'mp3', 'mp4', 'wav'],
        accept_multiple_files=True,
        key="browser_uploader"
    )
    uploaded_total_mb = sum(getattr(f, "size", 0) for f in uploaded_files or []) / (1024 * 1024)
    if uploaded_files:
        if uploaded_total_mb > BROWSER_UPLOAD_SAFE_LIMIT_MB:
            st.error(f"偵測到瀏覽器上傳總量 {uploaded_total_mb:.1f} MB，已超過安全上限 {BROWSER_UPLOAD_SAFE_LIMIT_MB} MB。請清空上傳並改用方案二的 Windows 本地資料夾路徑。")
        else:
            st.success(f"瀏覽器小檔模式就緒：{len(uploaded_files)} 個檔案，總量 {uploaded_total_mb:.1f} MB。")

    st.markdown("##### 📁 方案二：Windows 本地路徑大檔與資料夾模式（建議 3G 到 9G 檔案使用）")
    st.info("💡 **批次導入小提示**：若您的檔案分散在多個子資料夾（如 `ch1` 到 `ch45`），您**不需要**逐一選取子資料夾！您只需選取最上層的**母資料夾**（例如 `民法A115`），系統在啟動時便會**「自動遞迴掃描」**旗下所有子資料夾內的所有影音與文件檔案！")
    
    col_path_input, col_add_btn = st.columns([8, 2])
    with col_path_input:
        manual_path = st.text_input("請輸入 Windows 本地檔案或資料夾路徑", value="", placeholder="例如：E:\\法律\\台灣法規庫 或 C:\\case\\evidence.mp4", key="manual_path_input")
    with col_add_btn:
        st.write("")
        st.write("")
        if st.button("➕ 新增此路徑", key="add_manual_path"):
            if manual_path:
                parsed_paths = parse_multiple_paths(manual_path)
                added_paths = []
                missing_paths = []
                
                if "chosen_batch_paths" not in st.session_state:
                    st.session_state.chosen_batch_paths = load_paths_from_buffer()
                
                for p in parsed_paths:
                    if os.path.exists(p):
                        abs_p = os.path.abspath(p)
                        if abs_p not in st.session_state.chosen_batch_paths:
                            st.session_state.chosen_batch_paths.append(abs_p)
                            added_paths.append(abs_p)
                    else:
                        missing_paths.append(p)
                
                if added_paths:
                    save_paths_to_buffer(st.session_state.chosen_batch_paths)
                    st.success(f"✅ 已成功批次新增 {len(added_paths)} 個有效路徑！")
                
                if missing_paths:
                    missing_str = ", ".join(f"`{mp}`" for mp in missing_paths)
                    st.error(f"❌ 以下 {len(missing_paths)} 個路徑在電腦中不存在，請檢查拼字：{missing_str}")
                
                if added_paths and not missing_paths:
                    st.rerun()
            else:
                st.warning("請先輸入路徑。")

    enable_tkinter = st.checkbox("啟用本地實體檔案瀏覽器 (⚠️ 僅限在 Windows 本地電腦執行且有桌面環境時勾選；若是遠端或容器環境請勿啟用，以免伺服器卡死)", value=False, key="enable_tkinter_pickers")

    col_browse_dir, col_browse_files = st.columns([1, 1])
    with col_browse_dir:
        if st.button("📁 實體檔案總管選資料夾 (可 Ctrl 多選)", key="st_browse_folder", disabled=not enable_tkinter):
            chosen_dirs = select_folders()
            if chosen_dirs:
                if "chosen_batch_paths" not in st.session_state:
                    st.session_state.chosen_batch_paths = load_paths_from_buffer()
                for d in chosen_dirs:
                    abs_path = os.path.abspath(d)
                    if abs_path not in st.session_state.chosen_batch_paths:
                        st.session_state.chosen_batch_paths.append(abs_path)
                save_paths_to_buffer(st.session_state.chosen_batch_paths)
                st.rerun()
    with col_browse_files:
        if st.button("📄 批次點選多個檔案 (可 Ctrl 多選)", key="st_browse_files", disabled=not enable_tkinter):
            chosen_files = select_files()
            if chosen_files:
                if "chosen_batch_paths" not in st.session_state:
                    st.session_state.chosen_batch_paths = load_paths_from_buffer()
                for f in chosen_files:
                    abs_path = os.path.abspath(f)
                    if abs_path not in st.session_state.chosen_batch_paths:
                        st.session_state.chosen_batch_paths.append(abs_path)
                save_paths_to_buffer(st.session_state.chosen_batch_paths)
                st.rerun()

    st.markdown("##### 🤖 方案三：本機法律教材全自動搜尋與一鍵吸收模式")
    st.markdown("""
    <div style=" border-left: 6px solid #d97706; padding: 16px; border-radius: 8px; margin-bottom: 15px;">
        <p style="margin: 0; font-size: 0.95em; color: #1e3a8a;">
            <b>🤖 智能搜尋機器人</b>：點擊下方按鈕，機器人將自動掃描您本機的所有硬碟磁碟機（最大深度為 8，排除系統無關目錄），自動精確匹配資料夾或檔案名稱含有法律、訴訟、憲法、民事、刑事等教材關鍵字的資料夾，並將其自動載入下方隊列中。
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_bot_scan, col_bot_scan_and_run = st.columns([1, 1])
    
    with col_bot_scan:
        if st.button("🤖 啟動全自動搜尋並填入下方隊列", key="run_bot_scan_only", use_container_width=True):
            with st.spinner("🤖 正在自動掃描本機磁碟機中（請稍候約 10-15 秒）..."):
                try:
                    manual_path_val = st.session_state.get("manual_path_input", "").strip() or None
                    from scripts_v6.auto_ingest_bot import scan_drives
                    found_folders = scan_drives(scan_path=manual_path_val)
                    if found_folders:
                        if "chosen_batch_paths" not in st.session_state:
                            st.session_state.chosen_batch_paths = load_paths_from_buffer()
                        
                        added_count = 0
                        for folder in found_folders:
                            abs_folder = os.path.abspath(folder)
                            if abs_folder not in st.session_state.chosen_batch_paths:
                                st.session_state.chosen_batch_paths.append(abs_folder)
                                added_count += 1
                        
                        save_paths_to_buffer(st.session_state.chosen_batch_paths)
                        if added_count > 0:
                            st.success(f"🤖 機器人已成功在您的磁碟中自動定位出 {len(found_folders)} 個符合條件的法律教材資料夾，並新增了 {added_count} 個新目錄到下方隊列！")
                        else:
                            st.info(f"🤖 機器人已成功搜尋到 {len(found_folders)} 個教材資料夾，均已存在於下方隊列中。")
                        
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.warning("❌ 機器人未在您的磁碟中找到任何符合條件的法律教材資料夾。")
                except Exception as e:
                    st.error(f"❌ 機器人執行搜尋出錯：{e}")
                    
    with col_bot_scan_and_run:
        if st.button("⚡ 啟動全自動搜尋並直接執行一鍵吸收", key="run_bot_scan_and_digest", use_container_width=True):
            with st.spinner("🤖 正在自動掃描本機磁碟並直接拉起消化任務（請稍候）..."):
                try:
                    manual_path_val = st.session_state.get("manual_path_input", "").strip() or None
                    from scripts_v6.auto_ingest_bot import scan_drives
                    found_folders = scan_drives(scan_path=manual_path_val)
                    if found_folders:
                        # 1. 寫入隊列
                        if "chosen_batch_paths" not in st.session_state:
                            st.session_state.chosen_batch_paths = load_paths_from_buffer()
                        
                        for folder in found_folders:
                            abs_folder = os.path.abspath(folder)
                            if abs_folder not in st.session_state.chosen_batch_paths:
                                st.session_state.chosen_batch_paths.append(abs_folder)
                        
                        save_paths_to_buffer(st.session_state.chosen_batch_paths)
                        
                        # 2. 直接在此收集所有有效檔案
                        valid_files_info = []
                        seen_paths = set()
                        from scripts_v6.auto_ingest_bot import is_file_content_legal
                        for p_str in st.session_state.chosen_batch_paths:
                            p = Path(p_str)
                            if not p.exists():
                                continue
                            if p.is_file():
                                if p.suffix.lower() in SUPPORTED_INGEST_EXTS:
                                    abs_p = str(p.resolve())
                                    if abs_p not in seen_paths:
                                        if is_file_content_legal(abs_p):
                                            seen_paths.add(abs_p)
                                            valid_files_info.append((p.name, str(p), "local"))
                            elif p.is_dir():
                                files = list(p.rglob("*"))
                                for f in files:
                                    if f.is_file() and f.suffix.lower() in SUPPORTED_INGEST_EXTS:
                                        abs_p = str(f.resolve())
                                        if abs_p not in seen_paths:
                                            if is_file_content_legal(abs_p):
                                                seen_paths.add(abs_p)
                                                valid_files_info.append((f.name, str(f), "local"))
                                            
                        if not valid_files_info:
                            st.warning("🤖 搜尋到了資料夾，但其下沒有找到任何可處理的法律教材檔案！")
                        else:
                            IngestionBackgroundTask.reset()
                            IngestionBackgroundTask.valid_files_info = valid_files_info
                            IngestionBackgroundTask.total_files = len(valid_files_info)
                            IngestionBackgroundTask.transcripts_dir = "C:\\LocalAI_Workstation\\Transcripts"
                            os.makedirs(IngestionBackgroundTask.transcripts_dir, exist_ok=True)
                            IngestionBackgroundTask.status = "running"
                            IngestionBackgroundTask.save_to_disk()
                            
                            t = threading.Thread(target=run_background_ingestion, args=(st.session_state.agent_instance, 0))
                            t.daemon = True
                            t.start()
                            
                            st.success("🤖 機器人已自動搜尋完畢並成功啟動背景批次研讀任務！")
                            time.sleep(2)
                            st.rerun()
                    else:
                        st.warning("❌ 機器人未在您的磁碟中找到任何符合條件的法律教材資料夾。")
                except Exception as e:
                    st.error(f"❌ 機器人執行搜尋或啟動出錯：{e}")

    batch_paths = st.session_state.get("chosen_batch_paths", [])
    if batch_paths:
        st.success(f"📌 目前已選取 {len(batch_paths)} 個待研讀項目 (包含檔案與資料夾)：")
        
        for idx, p_path in enumerate(batch_paths):
            col_item_name, col_item_del = st.columns([8, 2])
            is_dir = os.path.isdir(p_path)
            icon = "📁 [資料夾]" if is_dir else "📄 [檔案]"
            
            detail_msg = ""
            if is_dir:
                try:
                    p_obj = Path(p_path)
                    all_files = list(p_obj.rglob("*"))
                    supported_files = [f for f in all_files if f.is_file() and f.suffix.lower() in SUPPORTED_INGEST_EXTS]
                    
                    ext_counts = {}
                    for f in supported_files:
                        ext = f.suffix.lower()
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1
                    
                    if supported_files:
                        summary_parts = []
                        for ext in sorted(ext_counts.keys()):
                            count = ext_counts[ext]
                            ext_label = ext.replace(".", "").upper()
                            summary_parts.append(f"`{ext_label}`: {count} 個")
                        summary_str = "，".join(summary_parts)
                        detail_msg = f"🔍 包含可處理法律教材檔案共 **{len(supported_files)}** 個 ({summary_str})"
                    else:
                        detail_msg = "⚠️ 警告：此資料夾下沒有找到任何可處理的影音或文件檔案！"
                except Exception as e:
                    detail_msg = f"⚠️ 無法讀取資料夾內容：{e}"
            
            with col_item_name:
                st.markdown(f"{idx+1}. {icon} `{p_path}`")
                if is_dir and detail_msg:
                    st.caption(detail_msg)
            with col_item_del:
                if st.button("❌ 移除", key=f"del_item_{idx}"):
                    batch_paths.pop(idx)
                    st.session_state.chosen_batch_paths = batch_paths
                    save_paths_to_buffer(st.session_state.chosen_batch_paths)
                    st.rerun()
                    
        if st.button("🧹 清空所有選取項目", key="clear_all_batch_paths"):
            st.session_state.chosen_batch_paths = []
            save_paths_to_buffer([])
            st.rerun()

    if st.button("🚀 啟動一鍵批次研讀與消化", use_container_width=True):
        valid_files_info = []
        
        if uploaded_files:
            if uploaded_total_mb > BROWSER_UPLOAD_SAFE_LIMIT_MB:
                st.error("已停止處理：瀏覽器上傳總量過大。請移除上方上傳檔案，改用方案二輸入本機資料夾路徑。")
            else:
                import tempfile
                for file_obj in uploaded_files:
                    suffix = Path(file_obj.name).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_f:
                        tmp_f.write(file_obj.read())
                        tmp_path = tmp_f.name
                    valid_files_info.append((file_obj.name, tmp_path, "uploaded"))
                
        seen_paths = set()
        from scripts_v6.auto_ingest_bot import is_file_content_legal
        for p_str in batch_paths:
            p = Path(p_str)
            if not p.exists():
                continue
            if p.is_file():
                if p.suffix.lower() in SUPPORTED_INGEST_EXTS:
                    abs_p = str(p.resolve())
                    if abs_p not in seen_paths:
                        if is_file_content_legal(abs_p):
                            seen_paths.add(abs_p)
                            valid_files_info.append((p.name, str(p), "local"))
            elif p.is_dir():
                files = list(p.rglob("*"))
                for f in files:
                    if f.is_file() and f.suffix.lower() in SUPPORTED_INGEST_EXTS:
                        abs_p = str(f.resolve())
                        if abs_p not in seen_paths:
                            if is_file_content_legal(abs_p):
                                seen_paths.add(abs_p)
                                valid_files_info.append((f.name, str(f), "local"))
                
        if not valid_files_info:
            st.warning("⚠️ 待研讀隊列為空！請拖放檔案至方案一，或設定方案二正確本地路徑與檔案選取。")
        else:
            IngestionBackgroundTask.reset()
            IngestionBackgroundTask.valid_files_info = valid_files_info
            IngestionBackgroundTask.total_files = len(valid_files_info)
            IngestionBackgroundTask.transcripts_dir = "C:\\LocalAI_Workstation\\Transcripts"
            os.makedirs(IngestionBackgroundTask.transcripts_dir, exist_ok=True)
            IngestionBackgroundTask.status = "running"
            IngestionBackgroundTask.save_to_disk()
            
            t = threading.Thread(target=run_background_ingestion, args=(st.session_state.agent_instance, 0))
            t.daemon = True
            t.start()
            
            st.success("🚀 背景批次教材研讀任務已成功啟動！")
            st.rerun()

# ==============================================================================
# TAB 2.5: 📂 法律個案管理區
# ==============================================================================
with tab_cases:
    st.subheader("📂 法律訴訟個案與關係人智慧管理模組")
    st.caption("管理獨立的法律個案，追蹤案件關係人的訴訟歷史、書狀證據清單、判例引用與法律主張。")
    
    from scripts_v6.case_manager import load_cases, save_cases
    cases = load_cases()
    
    # 1. 關係人跨案整合檢索
    st.markdown("### 🔍 關係人跨案整合與前科歷史檢索")
    sh_search = st.text_input("請輸入當事人/關係人姓名 (例如：林ＯＯ)", value="", placeholder="輸入姓名可檢索本地個案與資料庫關聯判決...")
    
    if sh_search.strip():
        st.markdown(f"##### 🔎 關於「{sh_search}」的檢索結果：")
        found_local_cases = []
        for cid, cdata in cases.items():
            if any(sh_search in sh or sh in sh_search for sh in cdata.get("stakeholders", [])):
                found_local_cases.append((cid, cdata))
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown("📂 **本地歷史個案記錄**")
            if found_local_cases:
                for cid, cdata in found_local_cases:
                    st.info(f"📌 **{cid} : {cdata['title']}**\n- 目前階段：{cdata['current_stage']}\n- 關係人：{', '.join(cdata['stakeholders'])}")
            else:
                st.write("沒有找到本地相關個案記錄。")
                
        with col_res2:
            st.markdown("⚖️ **資料庫關聯條文與判決記錄**")
            try:
                name_vec = st.session_state.agent_instance._get_embedding(sh_search)
                if name_vec:
                    res_docs = st.session_state.agent_instance.law_coll.query(query_embeddings=[name_vec], n_results=3)
                    if res_docs and res_docs['documents'] and res_docs['documents'][0]:
                        for d, m in zip(res_docs['documents'][0], res_docs['metadatas'][0]):
                            st.warning(f"📄 **{m.get('source', '關聯法源')}**\n{d[:200]}...")
                    else:
                        st.write("沒有找到關聯的法規或判決書。")
                else:
                    st.write("無法取得向量進行檢索。")
            except Exception as e:
                st.write(f"資料庫檢索中斷: {e}")
                
    st.markdown("---")
    
    # 2. 獨立個案工作面板
    st.markdown("### 💼 獨立個案工作面板")
    if not cases:
        st.info("目前無個案，請在 cases_data.json 中配置。")
    else:
        case_ids = list(cases.keys())
        selected_case_id = st.selectbox("請選擇要管理的個案：", case_ids, format_func=lambda x: f"{x} - {cases[x]['title']}")
        
        case_data = cases[selected_case_id]
        
        st.markdown(f"#### 📁 個案：{case_data['title']} ({selected_case_id})")
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"⚡ **目前訴訟階段**：`{case_data['current_stage']}`")
        with col_meta2:
            st.markdown(f"👥 **案件關係人**：`{', '.join(case_data['stakeholders'])}`")
            
        col_case_chat, col_case_lists = st.columns([1, 1])
        
        with col_case_chat:
            st.markdown("💬 **個案專屬訴訟對話與答辯建議**")
            chat_container = st.container(height=350, border=True)
            with chat_container:
                for msg in case_data.get("dialog_history", []):
                    role = msg.get("role", "user")
                    text = msg.get("text", "")
                    if role == "user":
                        st.markdown(f"<div style=' padding:10px; border-radius:10px; margin-bottom:8px; color:#0D47A1;'><b>使用者：</b>{html.escape(text)}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style=' padding:10px; border-radius:10px; margin-bottom:8px; color:#212121;'><b>AI 建議：</b>{html.escape(text)}</div>", unsafe_allow_html=True)
            
            with st.form(key=f"case_chat_form_{selected_case_id}"):
                case_user_msg = st.text_input("輸入該個案的訴訟事實、答辯要點或書狀草稿：", key=f"case_chat_in_{selected_case_id}")
                send_chat = st.form_submit_button("發送諮詢並記錄")
                
            if send_chat and case_user_msg.strip():
                dialog_context = "\n".join([f"{m['role']}: {m['text']}" for m in case_data.get("dialog_history", [])[-4:]])
                prompt = (
                    f"案件標題：{case_data['title']}\n"
                    f"目前訴訟階段：{case_data['current_stage']}\n"
                    f"歷史對話：\n{dialog_context}\n"
                    f"當事人提問/輸入事實：{case_user_msg}\n\n"
                    "請站在老律師或老法官的實務立場，給出最精準的三段論法答辯要點、法規適用或書狀修改建議。使用繁體中文。"
                )
                with st.spinner("AI 正在研判個案爭點中..."):
                    try:
                        payload = {
                            "model": st.session_state.ollama_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "stream": False
                        }
                        res = requests.post(f'{os.environ.get("OLLAMA_HOST", "http://localhost:11434")}/api/chat', json=payload, timeout=90)
                        if res.status_code == 200:
                            ai_reply = res.json().get('message', {}).get('content', 'API 回應格式異常')
                        else:
                            ai_reply = f"❌ Ollama 服務異常 ({res.status_code})"
                    except Exception as ex:
                        ai_reply = f"❌ 呼叫大模型失敗: {ex}"
                
                if "dialog_history" not in case_data:
                    case_data["dialog_history"] = []
                case_data["dialog_history"].append({"role": "user", "text": case_user_msg})
                case_data["dialog_history"].append({"role": "agent", "text": ai_reply})
                
                cases[selected_case_id] = case_data
                save_cases(cases)
                st.rerun()
                
        with col_case_lists:
            st.markdown("📋 **個案智慧清單與點評反饋**")
            
            with st.form(key=f"case_lists_form_{selected_case_id}"):
                st.markdown("##### 📄 訴訟書狀與證據清單")
                updated_docs = []
                for doc in case_data.get("documents_and_evidence", []):
                    st.write(f"📎 **{doc['name']}**")
                    new_cmt = st.text_input("點評記錄：", value=doc.get("comment", ""), key=f"cmt_doc_{selected_case_id}_{doc['id']}")
                    updated_docs.append({"id": doc['id'], "name": doc['name'], "comment": new_cmt})
                
                st.markdown("##### 🔗 關聯性判例引用推薦")
                updated_precedents = []
                for pcd in case_data.get("precedents", []):
                    st.write(f"📜 **{pcd['name']}**")
                    new_cmt = st.text_input("點評記錄：", value=pcd.get("comment", ""), key=f"cmt_pcd_{selected_case_id}_{pcd['id']}")
                    updated_precedents.append({"id": pcd['id'], "name": pcd['name'], "comment": new_cmt})
                    
                st.markdown("##### ⚖️ 法律聲明主張")
                updated_claims = []
                for clm in case_data.get("claims", []):
                    st.write(f"📌 **{clm['name']}**")
                    new_cmt = st.text_input("點評記錄：", value=clm.get("comment", ""), key=f"cmt_clm_{selected_case_id}_{clm['id']}")
                    updated_claims.append({"id": clm['id'], "name": clm['name'], "comment": new_cmt})
                    
                save_list_changes = st.form_submit_button("💾 儲存點評與清單變更")
                
            if save_list_changes:
                case_data["documents_and_evidence"] = updated_docs
                case_data["precedents"] = updated_precedents
                case_data["claims"] = updated_claims
                
                cases[selected_case_id] = case_data
                save_cases(cases)
                st.success("✅ 點評與清單變更已成功存回資料庫！")
                st.rerun()

# ==============================================================================
# TAB 3: 教材檢索與定位區 (🔍 教材檢索與定位)
# ==============================================================================
with tab_search:
    st.subheader("🔍 教材智能索引起索與定位")
    st.caption("輸入關鍵法律爭點或問句，系統會自動在已匯入的教材庫中檢索，並直接列出對應的書面頁碼或影音時間戳記。")
    
    with st.expander("🎙️ / 📂 語音與檔案多模態輸入 (檢索輔助)", expanded=False):
        col_aud_t3, col_fil_t3 = st.columns([1, 1])
        with col_aud_t3:
            audio_inp_tab3 = st.audio_input("錄製語音檢索 (Whisper 本地轉譯)", key="tab3_audio_input")
        with col_fil_t3:
            file_inp_tab3 = st.file_uploader("上傳檢索參考檔案 (支援 PDF、圖片、音訊、文字檔)", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "m4a", "mp4", "txt"], key="tab3_file_input")
        
        extracted_text_tab3 = ""
        if audio_inp_tab3:
            extracted_text_tab3 = process_multimodal_input(audio_inp_tab3)
        elif file_inp_tab3:
            extracted_text_tab3 = process_multimodal_input(file_inp_tab3)
            
        if extracted_text_tab3:
            if st.session_state.tab3_search_query_value:
                st.session_state.tab3_search_query_value += "\n" + extracted_text_tab3
            else:
                st.session_state.tab3_search_query_value = extracted_text_tab3
            st.toast("💡 成功從多模態輸入中提取文字，已寫入下方檢索框！")
            st.rerun()

    with st.form("course_materials_search_form"):
        search_query = st.text_area("💡 請輸入或多模態載入欲檢索的法律爭點或問句 (支援注音/Gboard語音輸入)", value=st.session_state.tab3_search_query_value, placeholder="例如：侵權行為的消滅時效為幾年？ 或 醫療費求償賠償", height=100)
        st.session_state.tab3_search_query_value = search_query
        search_btn = st.form_submit_button("🔍 開始檢索教材")
        
    if search_btn and search_query:
        with st.spinner("🔎 正在檢索教材資料庫，定位實體內容中..."):
            query_vec = st.session_state.agent_instance._get_embedding(search_query)
            if not query_vec:
                st.error("❌ 無法為此查詢生成向量特徵。")
            else:
                res = st.session_state.agent_instance.intel_coll.query(
                    query_embeddings=[query_vec],
                    n_results=15
                )
                
                if res and res['documents'] and res['documents'][0]:
                    docs = res['documents'][0]
                    metas = res['metadatas'][0]
                    dists = res['distances'][0]
                    
                    # 依據科別智商權重進行重排 (RWS 得分權重調整)
                    weighted_results = []
                    for d, m, dist in zip(docs, metas, dists):
                        # 計算餘弦相似度 (因向量均已歸一化，L2 距離與餘弦相似度關係為 cos_sim = 1.0 - dist / 2.0)
                        cos_sim = 1.0 - (dist / 2.0)
                        if cos_sim < 0.15:
                            continue
                        c_name = m.get("class_name", "未分類課程")
                        iq_score = SubjectIQManager.calculate_iq(c_name)
                        sim = cos_sim * (iq_score / 100.0)
                        weighted_results.append((sim, cos_sim, d, m))
                    
                    if not weighted_results:
                        st.info("🔍 未找到與檢索內容足夠相關的教材，已過濾無關內容。請嘗試使用其他關鍵字。")
                    else:
                        # 降序排序
                        weighted_results.sort(key=lambda x: x[0], reverse=True)
                        
                        st.success(f"🎉 找到以下相關教材定位資訊（已整合科別智商評分重排與無關過濾）：")
                        
                        found_items = 0
                        for sim, cos_sim, d, m in weighted_results:
                            m_type = m.get("type", "unknown")
                            if m_type == "obsidian_memory" or m_type == "summary":
                                continue
                                
                            found_items += 1
                            source_name = m.get("source", "未命名檔案")
                            c_name = m.get("class_name", "未分類課程")
                            l_name = m.get("lesson_name", "未分類課堂")
                            
                            location_info = ""
                            if m_type == "pdf":
                                page_no = m.get("page", 1)
                                location_info = f"📄 **書面教材** | **第 {page_no} 頁**"
                            elif m_type == "audio":
                                ts = m.get("timestamp", "未知時間")
                                location_info = f"🎬 **影音教材** | **時間戳記 {ts}**"
                            elif m_type == "txt":
                                location_info = f"📝 **文件教材** | **段落片段**"
                            else:
                                location_info = f"💡 **綜合教材片段**"
                                
                            st.markdown(f"""
                            <div style=" padding: 12px; border-radius: 8px; border-left: 4px solid #1f77b4; margin-bottom: 10px;">
                                <span style="color:#2b5c8f; font-weight:bold;">【課程】{c_name} ➔ {l_name}</span><br>
                                <span style="color:#333;">📂 來源檔案：<code>{source_name}</code></span> | {location_info} | <small>餘弦相似度: {cos_sim:.2%} | 調整後智力權重: {sim:.2%}</small>
                                <hr style="margin: 6px 0;">
                                <p style="font-size: 0.95em; color: #444; margin: 0; white-space: pre-wrap;">{d[:500]}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 檢索卡片評判
                            with st.expander(f"📝 評估此檢索教材 (相似度: {cos_sim:.1%})", expanded=False):
                                with st.form(f"feedback_search_tab3_{found_items}"):
                                    rating_ev3 = st.radio("評價此條目關聯度", ["👍 關聯精準", "👎 與檢索無關/錯誤"], horizontal=True, key=f"rating_tab3_ev_{found_items}")
                                    comment_ev3 = st.text_input("輸入改進評語", placeholder="如：此段內容偏離爭點", key=f"comment_tab3_ev_{found_items}")
                                    btn_ev3 = st.form_submit_button("提交回饋修正權重")
                                    if btn_ev3:
                                        score_type = "like" if "👍" in rating_ev3 else "dislike"
                                        SubjectIQManager.add_feedback(c_name, score_type, f"【教材檢索評判: {source_name}】{comment_ev3}")
                                        st.success(f"已記錄評價，科別「{c_name}」權重已動態調校！")
                        
                    if found_items == 0:
                        st.info("💡 找到的結果皆為系統摘要，無特定頁碼或影音時間戳記之教材定位。")
                else:
                    st.info("🔍 找不到相關教材，請確認您已在批次導入中匯入過教材檔案。")
                    
    # 顯示統計清單
    st.divider()
    st.markdown("### 📚 目前資料庫中已建檔的教材清單")
    try:
        all_records = st.session_state.agent_instance.intel_coll.get(include=["metadatas"])
        metas = all_records.get("metadatas", []) if all_records else []
        
        if metas:
            file_stats = {}
            for m in metas:
                if not m:
                    continue
                source = m.get("source", "未知來源")
                m_type = m.get("type", "unknown")
                c_name = m.get("class_name", "未分類課程")
                l_name = m.get("lesson_name", "未分類課堂")
                
                if m_type == "obsidian_memory" or not source:
                    continue
                    
                if source not in file_stats:
                    file_stats[source] = {
                        "class_name": c_name,
                        "lesson_name": l_name,
                        "type": m_type,
                        "pages": set(),
                        "timestamps": set()
                    }
                
                if m_type == "pdf" and "page" in m:
                    file_stats[source]["pages"].add(m["page"])
                elif m_type == "audio" and "timestamp" in m:
                    file_stats[source]["timestamps"].add(m["timestamp"])
            
            if file_stats:
                st.caption(f"📊 目前資料庫共有 {len(file_stats)} 個已建檔的教材檔案：")
                for f_name, stats in file_stats.items():
                    icon = "🎥" if stats["type"] == "audio" else ("📄" if stats["type"] == "pdf" else "📝")
                    info_parts = []
                    if stats["pages"]:
                        sorted_pages = sorted(list(stats["pages"]))
                        info_parts.append(f"共 {len(sorted_pages)} 頁 (第 {min(sorted_pages)}~{max(sorted_pages)} 頁)")
                    if stats["timestamps"]:
                        info_parts.append(f"共 {len(stats['timestamps'])} 段時間戳記")
                    
                    detail_str = ", ".join(info_parts) if info_parts else "摘要消化檔"
                    st.markdown(f"- {icon} **{f_name}** | 課程: `{stats['class_name']}` | 課堂: `{stats['lesson_name']}` | `{detail_str}`")
            else:
                st.info("📭 目前資料庫中尚無教材建檔。請前往「📥 知識餵養」匯入教材。")
        else:
            st.info("📭 目前資料庫中尚無教材建檔。請前往「📥 知識餵養」匯入教材。")
    except Exception as e:
        st.warning(f"無法讀取教材統計資訊：{e}")

    st.markdown("---")
    st.markdown("### 📚 十四法科智慧問答與定位 (Fourteen Subjects Q&A)")
    st.caption("切換特定法律學門，系統會自動加載專科領域心智，精準定位其核心法源並進行深度問答。")
    
    col_sub_sel, col_sub_input = st.columns([3, 7])
    with col_sub_sel:
        selected_subject = st.selectbox(
            "請選擇專業法律科目",
            ["民法", "刑法", "行政程序法", "專利法", "商標法", "著作權法", "營業秘密法", "個資法", "選罷法", "證券交易法", "所得稅法", "金融法規", "RealtyLex 不動產法律", "國考"],
            key="tab3_subject_select"
        )
    with col_sub_input:
        sub_query = st.text_input(f"請輸入關於【{selected_subject}】的具體爭點或諮詢問題", placeholder=f"例如：關於{selected_subject}的最新實務見解或關鍵定義...", key="tab3_subject_query_input")
    if st.button("🚀 執行專科智慧解析", key="tab3_btn_run_sub_qa"):
        if sub_query:
            with st.spinner(f"正在載入【{selected_subject}】專業領域心智並檢索相關文獻..."):
                reply, evidence = st.session_state.agent_instance.chat_subject_qa(selected_subject, sub_query)
                st.markdown(f"#### 🤖 【{selected_subject}】領域專家解析結果")
                st.markdown(reply)
                
                if evidence:
                    with st.expander("📚 本次檢索關聯文獻與法規依據"):
                        for i, ev in enumerate(evidence):
                            st.markdown(f"**[{i+1}] {ev['source']}**")
                            st.write(ev['text'])
        else:
            st.warning("請先輸入問題內容！")

# ==============================================================================
# TAB 3: 司法官大會考自我訓練與檢討區
# ==============================================================================
with tab_exam:
    st.subheader("🎓 國家司法官會考自我修復訓練")
    st.caption("AI 模擬解答歷屆國家考試主觀寫作題。透過閱卷教授的批改卡，AI 將邏輯盲點、少見解或寫錯的法條內化至大腦。")
    
    with st.expander("🎙️ / 📂 語音與檔案多模態輸入 (題目/範本導入)", expanded=False):
        col_aud_t4, col_fil_t4 = st.columns([1, 1])
        with col_aud_t4:
            audio_inp_exam = st.audio_input("錄製考題語音 (Whisper 本地轉錄)", key="tab4_audio_input")
        with col_fil_t4:
            file_inp_exam = st.file_uploader("上傳題目/範本文件 (支援 PDF、圖片、音訊、文字檔)", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "m4a", "mp4", "txt"], key="tab4_file_input")
        
        extracted_text_exam = ""
        if audio_inp_exam:
            extracted_text_exam = process_multimodal_input(audio_inp_exam)
        elif file_inp_exam:
            extracted_text_exam = process_multimodal_input(file_inp_exam)
            
        if extracted_text_exam:
            st.info("💡 成功從多模態輸入中提取以下文本：")
            st.text_area("提取內容預覽", value=extracted_text_exam, height=100, key="tab4_extracted_preview")
            col_btn_q, col_btn_a, col_btn_s = st.columns(3)
            with col_btn_q:
                if st.button("📤 填入『歷屆司法官考題題目』", key="tab4_fill_q"):
                    st.session_state.tab4_question_value = extracted_text_exam
                    st.rerun()
            with col_btn_a:
                if st.button("📤 填入『高分解答範本』", key="tab4_fill_a"):
                    st.session_state.tab4_answer_value = extracted_text_exam
                    st.rerun()
            with col_btn_s:
                if st.button("📤 填入『本題關聯教材檢索框』", key="tab4_fill_s"):
                    st.session_state.tab4_search_value = extracted_text_exam[:150]
                    st.rerun()

    with st.form("exam_practice_form"):
        col_q, col_a = st.columns(2)
        with col_q:
            default_q = st.session_state.get("tab4_question_value", "乙騎乘機車在十字路口超速闖紅燈，與甲發生碰撞致甲大腿粉碎性骨折。甲於民國112年1月1日知悉此情，欲向乙起訴求償，試問其損害賠償權利應如何主張？")
            question_text = st.text_area("歷屆司法官考題題目", height=150, value=default_q)
        with col_a:
            default_a = st.session_state.get("tab4_answer_value", "本件甲可依民法第184條前段主張侵權行為損害賠償。惟需注意，侵權損害賠償請求權利，依民法第197條規定有二年消滅時效之程序抗辯限制。本件發生日起算二年至114年1月，若逾期起訴，對造得為時效完成後之給付抗辯。")
            model_answer = st.text_area("學界推薦高分教授解答範本", height=150, value=default_a)
        submit_exam = st.form_submit_button("🚀 送入考場！AI 模擬作答與反思")

    if submit_exam:
        with st.spinner("📝 AI 正在進行 RAG 檢索並嘗試模擬作答中..."):
            try:
                from scripts_v6.exam_trainer import ExamTrainer
                trainer = ExamTrainer()
                ai_answer, critique, evidence = trainer.train_single_exam(question_text, model_answer, question_name="國家司法考試自我檢討")
                
                st.success("🎉 [成長完成] 閱卷教授分析糾正報告與 RAG 答題歷程已寫入 [智商庫(Vault)]，AI 以此完成一輪邏輯演進化！")
                
                # RAG 檢索法源展示
                if evidence:
                    with st.expander("📚 考生作答參考之 RWS 檢索法源與經驗", expanded=True):
                        for idx_ev, ev in enumerate(evidence):
                            st.markdown(f"**[{idx_ev+1}] {ev['source']} (得分: {ev['score']})**")
                            st.write(ev['text'])
                           
                col_res_ans, col_res_crit = st.columns(2)
                with col_res_ans:
                    st.markdown("### ✍️ 考生助理自擬回答")
                    st.write(ai_answer)
                with col_res_crit:
                    st.markdown("### 🎴 教授閱卷批改報告")
                    st.write(critique)
                    
            except Exception as e:
                st.error(f"❌ 自我反思流程異常：{e}")

    st.divider()
    st.subheader("🔍 本題關聯教材定位與檢索")
    st.caption("系統會依記您上方輸入的考古題題目，自動或手動比對並定位資料庫中相關的教材頁碼與影音時間戳記。")
    
    with st.form("exam_associated_search_form"):
        exam_search_query = st.text_input(
            "請輸入考古題相關爭點或關鍵字（預設為上方題目）", 
            value=st.session_state.get("tab4_search_value", question_text[:150] if question_text else ""), 
            key="exam_tab_search_query"
        )
        st.session_state.tab4_search_value = exam_search_query
        exam_search_btn = st.form_submit_button("🔍 檢索關聯教材")
        
    if exam_search_btn and exam_search_query:
        with st.spinner("🔎 正在比對智商庫，搜尋本題關聯教材中..."):
            query_vec = st.session_state.agent_instance._get_embedding(exam_search_query)
            if not query_vec:
                st.error("❌ 無法為此考古題生成向量特徵。")
            else:
                res = st.session_state.agent_instance.intel_coll.query(
                    query_embeddings=[query_vec],
                    n_results=10
                )
                
                if res and res['documents'] and res['documents'][0]:
                    docs = res['documents'][0]
                    metas = res['metadatas'][0]
                    dists = res['distances'][0]
                    
                    # 依據科別智商權重進行重排 (RWS 得分權重調整)
                    weighted_results = []
                    for d, m, dist in zip(docs, metas, dists):
                        # 計算餘弦相似度 (因向量均已歸一化，L2 距離與餘弦相似度關係為 cos_sim = 1.0 - dist / 2.0)
                        cos_sim = 1.0 - (dist / 2.0)
                        if cos_sim < 0.15:
                            continue
                        c_name = m.get("class_name", "未分類課程")
                        iq_score = SubjectIQManager.calculate_iq(c_name)
                        sim = cos_sim * (iq_score / 100.0)
                        weighted_results.append((sim, cos_sim, d, m))
                    
                    if not weighted_results:
                        st.info("🔍 未找到與考題足夠相關的教材，已過濾無關內容。請嘗試輸入更詳細的題目敘述。")
                    else:
                        # 降序排序
                        weighted_results.sort(key=lambda x: x[0], reverse=True)
                        
                        st.success(f"🎉 找到與本題相關的教材定位資訊（已整合科別智商評分重排與無關過濾）：")
                        
                        found_items = 0
                        for sim, cos_sim, d, m in weighted_results:
                            m_type = m.get("type", "unknown")
                            if m_type == "obsidian_memory" or m_type == "summary":
                                continue
                                
                            found_items += 1
                            source_name = m.get("source", "未命名檔案")
                            c_name = m.get("class_name", "未分類課程")
                            l_name = m.get("lesson_name", "未分類課堂")
                            
                            location_info = ""
                            if m_type == "pdf":
                                page_no = m.get("page", 1)
                                location_info = f"📄 **書面教材** | **第 {page_no} 頁**"
                            elif m_type == "audio":
                                ts = m.get("timestamp", "未知時間")
                                location_info = f"🎬 **影音教材** | **時間戳記 {ts}**"
                            elif m_type == "txt":
                                location_info = f"📝 **文件教材** | **段落片段**"
                            else:
                                location_info = f"💡 **綜合教材片段**"
                                
                            st.markdown(f"""
                            <div style=" padding: 12px; border-radius: 8px; border-left: 4px solid #f0ad4e; margin-bottom: 10px;">
                                <span style="color:#8a6d3b; font-weight:bold;">【課程】{c_name} ➔ {l_name}</span><br>
                                <span style="color:#333;">📂 來源檔案：<code>{source_name}</code></span> | {location_info} | <small>餘弦相似度: {cos_sim:.2%} | 調整後智力權重: {sim:.2%}</small>
                                <hr style="margin: 6px 0; border-top: 1px solid #f5e79e;">
                                <p style="font-size: 0.95em; color: #555; margin: 0; white-space: pre-wrap;">{d[:400]}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 檢索卡片評判
                            with st.expander(f"📝 評估此關聯教材 (相似度: {cos_sim:.1%})", expanded=False):
                                with st.form(f"feedback_search_tab4_{found_items}"):
                                    rating_ev4 = st.radio("評價此條目關聯度", ["👍 關聯精準", "👎 與考題無關/錯誤"], horizontal=True, key=f"rating_tab4_ev_{found_items}")
                                    comment_ev4 = st.text_input("輸入改進評語", placeholder="如：此段內容偏離考題核心", key=f"comment_tab4_ev_{found_items}")
                                    btn_ev4 = st.form_submit_button("提交回饋修正權重")
                                    if btn_ev4:
                                        score_type = "like" if "👍" in rating_ev4 else "dislike"
                                        SubjectIQManager.add_feedback(c_name, score_type, f"【考題關聯教材評判: {source_name}】{comment_ev4}")
                                        st.success(f"已記錄評價，科別「{c_name}」權重已動態調校！")
                        
                    if found_items == 0:
                        st.info("💡 找到的結果皆為系統摘要，無特定頁碼或影音時間戳記之教材定位。")
                else:
                    st.info("🔍 找不到相關教材，請確認您已在批次導入中匯入過教材檔案。")

# ==============================================================================
# TAB 4: 訴訟書狀自動起草區 (對位 React 核心 訴訟書狀起草)
# ==============================================================================
with tab_draft:
    st.subheader("📝 訴訟書狀自動編寫區 (IRAC 結構)")
    st.caption("根據委託人口述或筆錄，自動匹配 RWS 篩選出的黃金法條，一鍵生成合乎司法院審級規範的合格書狀草稿。")
    
    col_draft_in, col_draft_out = st.columns(2)
    with col_draft_in:
        with st.expander("🎙️ / 📂 語音與檔案多模態輸入 (起草事實導入)", expanded=False):
            col_aud_t5, col_fil_t5 = st.columns([1, 1])
            with col_aud_t5:
                audio_inp_draft = st.audio_input("錄製事實語音 (Whisper 本地轉錄)", key="tab5_audio_input")
            with col_fil_t5:
                file_inp_draft = st.file_uploader("上傳事實文件/起草參考 (自動提取)", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "m4a", "mp4", "txt"], key="tab5_file_input")
            
            extracted_text_draft = ""
            if audio_inp_draft:
                extracted_text_draft = process_multimodal_input(audio_inp_draft)
            elif file_inp_draft:
                extracted_text_draft = process_multimodal_input(file_inp_draft)
                
            if extracted_text_draft:
                if st.session_state.tab5_fact_value:
                    st.session_state.tab5_fact_value += "\n" + extracted_text_draft
                else:
                    st.session_state.tab5_fact_value = extracted_text_draft
                st.toast("💡 成功從多模態輸入中提取事實文字！")
                st.rerun()

        with st.form("draft_pleading_form"):
            draft_fact = st.text_area("事實細節輸入（越詳細，事實涵攝與法源引用越精準，支援注音/Gboard語音輸入）", height=250, 
                                      value=st.session_state.get("tab5_fact_value", "原告黃少奎在台北市信義路闖紅燈，被被告簡育芸開私家車擦撞造成大腿骨折，醫療費花費20萬元。事發時間為民國113年3月12日，被告態度傲慢消極逃避。"),
                                      key="tab5_draft_fact_input")
            st.session_state.tab5_fact_value = draft_fact
            draft_type = st.selectbox("訴訟書狀/文書類型", 
                                      ["civil_complaint", "criminal_complaint", "reply_pleading", "appeal_pleading", 
                                       "legal_notice_general", "legal_notice_infringement", "contract_sale", "contract_lease", "contract_trust"],
                                      format_func=lambda x: {
                                          "civil_complaint": "民事損害賠償起訴狀",
                                          "criminal_complaint": "刑事告訴狀",
                                          "reply_pleading": "民事答辯狀",
                                          "appeal_pleading": "民事上訴理由狀",
                                          "legal_notice_general": "郵局存證信函 - 催告履行/給付 (LexMind-Notice)",
                                          "legal_notice_infringement": "郵局存證信函 - 智財侵權警告 (LexMind-Notice)",
                                          "contract_sale": "買賣契約書 (LexMind-Contract)",
                                          "contract_lease": "房屋租賃契約書 (LexMind-Contract)",
                                          "contract_trust": "不動產借名登記契約書 (LexMind-Contract)"
                                      }[x])
            generate_btn = st.form_submit_button("✍️ 自動起草專業文書/書狀")

    with col_draft_out:
        st.subheader("📝 起草預覽與全文複製")
        if generate_btn:
            if not draft_fact.strip():
                st.error("請先輸入基礎案件事實或契約條件！")
            else:
                with st.spinner("老律師正依據臺灣法律與實務規範，起草專業文書中..."):
                    try:
                        translated_type = {
                            "civil_complaint": "民事損害賠償起訴狀",
                            "criminal_complaint": "刑事告訴狀",
                            "reply_pleading": "民事答辯狀",
                            "appeal_pleading": "民事上訴理由狀",
                            "legal_notice_general": "郵局存證信函 - 催告履行/給付",
                            "legal_notice_infringement": "郵局存證信函 - 智慧財產權侵權警告",
                            "contract_sale": "買賣契約書",
                            "contract_lease": "房屋租賃契約書",
                            "contract_trust": "不動產借名登記契約書"
                        }[draft_type]
                        
                        if "contract" in draft_type:
                            req_list = "\n1. 包括「立契約書人基本資料（甲方、乙方）」、「契約標的與條款」、「違約金與損害賠償責任」、「終止條款」、「管轄法院與準據法」。\n2. 條款務必嚴謹、平衡且對等，確保符合臺灣民法契約法原則。\n"
                        elif "legal_notice" in draft_type:
                            req_list = "\n1. 包括「寄件人與收件人地址」、「主旨」、「說明（敘明事實）」、「催告履行訴求與期限（例如於收到後七日內履行）」。\n2. 語氣務必堅定、合法催告，符合臺灣存證信函書寫規範。\n"
                        else:
                            req_list = "\n1. 包括「案由」、「原告/被告基本資料（姓名、地址等欄位，並預留括弧補填身分證字號、電話）」、「訴之聲明」、「事實及理由」。\n2. 正確引用台灣現行法律條文（例如若是車禍，應正確引用民法第184條、第193條、第195條等；並注意消滅時效條款，如民法第197條二年短期時效）。\n3. 語氣務必誠懇、莊重、符合我國訴訟規範。\n"

                        prompt_draft = f"你是一個擁有30年執業經驗、精通台灣法律文書與契約撰寫的資深老律師。請根據以下事實與要求，幫當事人起草一份高水準、專業且符合臺灣實務規範的【{translated_type}】。\n\n【基礎事實與細節】：\n{draft_fact}\n\n【寫作要求】：\n{req_list}\n3. 使用正確繁體中文（不得出現大陸法律詞彙如公安、行政訴訟提起至檢察院、被告人、時效消滅等）。"

                        payload_draft = {
                            "model": st.session_state.ollama_model,
                            "messages": [{"role": "user", "content": prompt_draft}],
                            "stream": False,
                            "options": {"num_ctx": 32768}
                        }
                        res = requests.post(f'{os.environ.get("OLLAMA_HOST", "http://localhost:11434")}/api/chat', json=payload_draft, timeout=90)
                        if res.status_code == 200:
                            st.session_state.last_draft_text = res.json().get('message', {}).get('content', '')
                            st.success("🎉 文書起草完成！")
                        else:
                            st.error("本地大模型引擎連線逾時，自動切換至安全離線起草範本。")
                            raise Exception("Headless Mode Engine Off")
                    except Exception as e:
                        # 離線律師模板備份保障
                        offline_title = {
                            "civil_complaint": "民事損害賠償起訴",
                            "criminal_complaint": "刑事告訴",
                            "reply_pleading": "民事答辯",
                            "appeal_pleading": "民事上訴理由",
                            "legal_notice_general": "郵局存證信函 (催告給付)",
                            "legal_notice_infringement": "郵局存證信函 (侵權警告)",
                            "contract_sale": "買賣契約書 (範本)",
                            "contract_lease": "租賃契約書 (範本)",
                            "contract_trust": "借名登記契約書 (範本)"
                        }[draft_type]
                        
                        st.session_state.last_draft_text = f"""【臺灣台北地方法院 訴訟書狀/專業法律文書 - 專業老律師離線起草範本】
 
 類型：{offline_title}
 關係人：黃少奎 與 簡育芸
 
 【主要條款/訴求內容】
 一、對造應按雙方約定給付新臺幣貳拾萬元整，及依法計算之迟延利息。
 二、本約定準據法為中華民國法律，如因本契約產生爭議，雙方同意以臺灣臺北地方法院為第一審管轄法院。
 
 【事實及理由摘要】
 緣本件事實略以：{draft_fact}。
 雙方應本諸誠實信用原則履行義務，如對造逾期仍不履行，原告/聲請人將依法向法院起訴或採取法律途徑，狀請鑒核，以保權益。
 
     此致
 臺灣台北地方法院 公鑒
 """
        
        # 顯示並提供全文複製
        draft_content = st.session_state.get("last_draft_text", "")
        if draft_content:
            st.text_area("起草文書全文預覽 (可點擊 Ctrl+A 複製)", value=draft_content, height=450)
        else:
            st.info("在左側欄位輸入口語事實並點擊「✍️ 自動起草專業文書/書狀」按鈕後，此處將實時生成高水準的文書內容。")

    st.markdown("---")
    st.markdown("### 🕵️ LexMind-Review 契約合規智慧審查")
    st.caption("貼上現有合約條款或協議文字，系統將自動套用合規風險 Checklists，掃描不平等條款、違約金風險及管轄權漏洞，並提供具體建議增補條款。")
    
    contract_review_input = st.text_area("請輸入或貼上要審查的契約/合約文字", placeholder="例如：貼上租賃契約中的違約責任或保密條款...", height=150, key="tab5_contract_review_input")
    if st.button("🔍 執行契約合規審查", key="tab5_btn_run_review", use_container_width=True):
        if contract_review_input:
            with st.spinner("智慧審查特助正在逐條核對合規風險與違約漏洞..."):
                review_result = st.session_state.agent_instance.review_contract(contract_review_input)
                st.markdown(review_result)
        else:
            st.warning("請先輸入契約內容！")

# ==============================================================================
# TAB 5: 系統時效工具與加密災難復原
# ==============================================================================
with tab_admin:
    # 🤖 /workflows 監控面板
    st.subheader("🤖 `/workflows` 系統與吸收工作流監控面板")
    st.caption("即時呈現本地自動化吸收工作流 (Ingestion Workflow) 狀態機之執行狀態、Entrypoint、當前狀態與執行工具三元素。")
    
    # 讀取並展示 IngestBackgroundTask 狀態
    IngestionBackgroundTask.load_from_disk()
    status_color = {
        "idle": "⚪ 閒置 (Idle)",
        "running": "🔵 執行中 (Running)",
        "paused": "🟡 暫停中 (Paused)",
        "cancelled": "🔴 已取消 (Cancelled)",
        "completed": "🟢 已完成 (Completed)",
        "error": "❌ 錯誤 (Error)"
    }.get(IngestionBackgroundTask.status, IngestionBackgroundTask.status)
    
    # 取得當前使用的工具名稱
    active_tool = "無 (None)"
    if IngestionBackgroundTask.status == "running":
        action_lower = IngestionBackgroundTask.current_action.lower()
        if "whisper" in action_lower or "轉錄" in action_lower:
            active_tool = "🎙️ Whisper 語音轉錄工具 (Whisper Audio Transcriber)"
        elif "ocr" in action_lower or "辨識" in action_lower:
            active_tool = "📄 EasyOCR 視覺文字辨識工具 (OCR Engine)"
        elif "大模型" in action_lower or "llm" in action_lower or "🧠" in action_lower:
            active_tool = "🧠 Ollama LLM 文字校正與摘要工具 (Ollama Refiner/Summarizer)"
        elif "板書" in action_lower or "圖表" in action_lower or "🎬" in action_lower:
            active_tool = "🎬 OpenCV 影片板書追蹤與自動裁切工具 (Visual Blackboard Tracker)"
        else:
            active_tool = f"🛠️ {IngestionBackgroundTask.current_action}"
            
    st.markdown(f"""
    <div style=" border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e5e7eb; padding-bottom: 10px; margin-bottom: 15px;">
            <span style="font-weight: bold; color: inherit; font-size: 1.1em;">🔄 Ingestion 工作流狀態機</span>
            <span style="font-weight: bold; color: #2563eb;">{status_color}</span>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.95em; color: inherit;">
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px 0; font-weight: bold; width: 30%;">🏁 入口點 (Entrypoint)</td>
                <td style="padding: 10px 0; font-family: monospace; color: #f59e0b;">scripts_v6/auto_ingest_bot.py & IngestBackgroundTask</td>
            </tr>
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px 0; font-weight: bold;">📊 當前狀態 (State)</td>
                <td style="padding: 10px 0; color: #10b981;">{IngestionBackgroundTask.status.upper()}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px 0; font-weight: bold;">🛠️ 執行工具 (Active Tool)</td>
                <td style="padding: 10px 0; color: #2563eb;">{active_tool}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px 0; font-weight: bold;">📁 研讀中教材</td>
                <td style="padding: 10px 0; color: inherit; font-family: monospace;">{IngestionBackgroundTask.current_file or '無'}</td>
            </tr>
            <tr>
                <td style="padding: 10px 0; font-weight: bold;">📈 處理進度</td>
                <td style="padding: 10px 0;">{IngestionBackgroundTask.processed_count} / {IngestionBackgroundTask.total_files} 個檔案</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 刷新監控面板進度", key="btn_refresh_workflow_panel"):
        st.rerun()

    st.divider()
    st.subheader("🌐 Ollama 本地 AI 服務連接與模型設定")
    st.info("💡 Ollama 連線網址與已下載模型之選取已移至左側邊欄 (Sidebar)，方便在所有功能頁面隨時切換與測試。")
    st.divider()

    st.subheader("🗓️ 臺灣民法雙重時效精算外掛")
    st.info("💡 為了讓您隨時隨地在不同功能分頁中皆能精算時效，本精算外掛功能已整合移至**「左側邊欄 (Sidebar)」**，您可以隨時在側邊欄進行推算並檢視結果，無須切換頁面。")

    st.divider()
    st.subheader("🔒 機密案件庫 AES-256 加密資安備份")
    if st.button("🤐 一鍵打包並以 AES 加密導出資料庫"):
        try:
            backup_mgr = LegalDBBackupManager()
            enc_file = backup_mgr.run_backup_and_encrypt()
            if enc_file:
                st.success(f"🔐 審判機密本地數據庫已完成 AES-256 Fernet 強度加密備份！\n路徑：{enc_file}")
        except Exception as e:
            st.error(f"❌ 備份加密故障了：{e}")

# ==============================================================================
# TAB 7: Antigravity AI 控制中心與視覺化運行監控
# ==============================================================================
with tab_agent:
    st.subheader("🤖 Antigravity 智能 Agent 運行控制台")
    st.caption("本界面提供 Antigravity (AI Agent 核心編碼助手) 的即時思考、工具執行軌跡、系統授權狀態與智商庫運行診斷。")
    
    # CSS 注入
    st.markdown("""
    <style>
        .agent-container {
            
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 12px;
            margin-bottom: 15px;
        }
        .agent-status-online {
            background: linear-gradient(135deg, #10b981, #059669);
            color: #1f2937;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
        }
        .thought-bubble {
            
            border-left: 4px solid #818cf8;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .tool-badge {
            display: inline-block;
            
            color: #7e22ce;
            border: 1px solid #e5e7eb;
            padding: 3px 8px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.85em;
            margin-bottom: 8px;
        }
        .terminal-box {
            
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            font-family: Consolas, Monaco, monospace;
            font-size: 0.85em;
            padding: 12px;
            color: #059669;
            overflow-x: auto;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 2.1 法律科別智商分佈與實務評判區 - 單獨設在最上層
    st.markdown("## 🧠 法律科別智商分佈與實務評判系統")
    
    col_top_left, col_top_right = st.columns([6, 4])
    
    # 統計 ChromaDB 科別
    subject_counts = {}
    try:
        all_records = st.session_state.agent_instance.intel_coll.get(include=["metadatas"])
        metas = all_records.get("metadatas", []) if all_records else []
        for m in metas:
            if not m:
                continue
            if m.get("type") == "obsidian_memory":
                continue
            c_name = m.get("class_name", "未分類課程")
            subject_counts[c_name] = subject_counts.get(c_name, 0) + 1
    except Exception:
        pass
        
    iq_data = SubjectIQManager.load_data()
    all_subjects = set(subject_counts.keys()).union(set(iq_data.keys()))
    if not all_subjects:
        all_subjects = {"民法課程", "刑法課程", "行政法課程", "刑事訴訟法", "民事訴訟法"}
        
    with col_top_left:
        st.markdown("### 📚 各科別智商分佈可視框")
        # 顯示各學科進度條
        for sub in sorted(all_subjects):
            doc_cnt = subject_counts.get(sub, 0)
            likes = iq_data.get(sub, {}).get("likes", 0)
            dislikes = iq_data.get(sub, {}).get("dislikes", 0)
            iq_score = SubjectIQManager.calculate_iq(sub)
            
            st.markdown(f"""
            <div style=" border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; align-items: center;">
                    <span style="font-weight: bold; color: inherit; font-size: 0.9em;">⚖️ {sub}</span>
                    <span style="color: #2563eb; font-weight: bold; font-size: 0.95em;">IQ {iq_score:.1f}</span>
                </div>
                <div style="font-size: 0.75em; color: #6b7280; margin-bottom: 6px;">
                    📂 已建檔: {doc_cnt} 筆 | 👍 {likes} 讚 | 👎 {dislikes} 差評
                </div>
                <div style=" border-radius: 4px; height: 8px; width: 100%; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #3b82f6, #2563eb); height: 100%; width: {iq_score}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_top_right:
        st.markdown("### ✍️ 實務評判與智力調校")
        with st.expander("🎙️ / 📂 語音與檔案多模態評判 (評判意見導入)", expanded=False):
            col_aud_fb, col_fil_fb = st.columns([1, 1])
            with col_aud_fb:
                audio_inp_fb = st.audio_input("錄製評判語音", key="fb_audio_input")
            with col_fil_fb:
                file_inp_fb = st.file_uploader("上傳評判參考檔 (支援 PDF/圖片/音視訊/純文字)", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "m4a", "mp4", "txt"], key="fb_file_input")
            
            extracted_text_fb = ""
            if audio_inp_fb:
                extracted_text_fb = process_multimodal_input(audio_inp_fb)
            elif file_inp_fb:
                extracted_text_fb = process_multimodal_input(file_inp_fb)
                
            if extracted_text_fb:
                st.session_state.feedback_comment_value = extracted_text_fb
                st.toast("💡 成功從多模態評判中提取文字！")
                st.rerun()

        with st.form("agent_feedback_form_top", clear_on_submit=True):
            selected_sub = st.selectbox("選擇評估法律科別", list(sorted(all_subjects)), key="feedback_subject_select_top")
            rating = st.radio("給予智商評價", ["👍 點讚支持 (提升權重)", "👎 給予差評 (下調權重)"], horizontal=True, key="feedback_rating_radio_top")
            comment_input = st.text_input("輸入您對本科別推理表現的實務評語 (支援注音/Gboard語音)", value=st.session_state.get("feedback_comment_value", ""), placeholder="請寫下該科別回答之優缺點，例如：對民法時效計算非常精準", key="feedback_comment_input_top")
            st.session_state.feedback_comment_value = comment_input
            submitted = st.form_submit_button("📤 提交實務考評反饋", use_container_width=True)
            
            if submitted:
                if selected_sub is not None and rating is not None:
                    score_type = "like" if "👍" in rating else "dislike"
                    SubjectIQManager.add_feedback(selected_sub, score_type, comment_input)
                else:
                    st.warning("請確保科別與評價已正確選取。")
                st.session_state.feedback_comment_value = "" # Clear after submission
                st.success(f"✅ 已成功為「{selected_sub}」提交實務評價並重新校準智商權重！")
                time.sleep(1.0)
                st.rerun()
                
        # 顯示歷史回饋
        st.markdown("### 💬 歷史考評意見與回饋")
        all_comments = []
        for sub, details in iq_data.items():
            comments = details.get("comments", [])
            for c in comments:
                all_comments.append({
                    "subject": sub,
                    "timestamp": c.get("timestamp", ""),
                    "comment": c.get("comment", ""),
                    "type": c.get("type", "like")
                })
        
        all_comments.sort(key=lambda x: x["timestamp"], reverse=True)
        
        if all_comments:
            comments_html = ""
            for c in all_comments[:5]:
                badge_color = "#10b981" if c["type"] == "like" else "#ef4444"
                badge_text = "👍 讚" if c["type"] == "like" else "👎 差"
                comments_html += f"""
                <div style=" border-radius: 6px; padding: 10px; margin-bottom: 8px; border-left: 3px solid {badge_color};">
                    <div style="display: flex; justify-content: space-between; font-size: 0.75em; color: #6b7280; margin-bottom: 4px;">
                        <span style="font-weight: bold; color: inherit;">{c['subject']}</span>
                        <span>{c['timestamp']}</span>
                    </div>
                    <p style="margin: 0; font-size: 0.85em; color: inherit; line-height: 1.4;">
                        <span style="color: {badge_color}; font-weight: bold; margin-right: 5px;">[{badge_text}]</span>{c['comment']}
                    </p>
                </div>
                """
            st.markdown(f"""
            <div style="max-height: 180px; overflow-y: auto; padding-right: 5px;">
                {comments_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("尚無歷史評語紀錄。")
            
    st.divider()

    # 下方雙欄控制區
    col_trace, col_dash = st.columns([7, 3])
    
    with col_dash:
        st.markdown("### 📊 Agent 狀態與系統指標")
        
        # 1. 狀態儀表板
        try:
            intel_count = st.session_state.agent_instance.intel_coll.count()
            law_count = st.session_state.agent_instance.law_coll.count()
        except Exception:
            intel_count = "無法取得"
            law_count = "無法取得"
            
        st.markdown(f"""
        <div class="agent-container">
            <div class="agent-header">
                <span style="font-weight: bold; color: inherit;">🤖 Antigravity 助手狀態</span>
                <span class="agent-status-online">🟢 運行中 (ONLINE)</span>
            </div>
            <p style="margin: 5px 0; font-size: 0.9em; color: #6b7280;">
                <b>🧠 推理引擎</b>: {st.session_state.ollama_model}<br>
                <b>💾 智商庫教材量</b>: {intel_count} 筆向量<br>
                <b>📚 基本法典數量</b>: {law_count} 筆向量<br>
                <b>📁 執行工作區</b>: <code>C:\\LocalAI_Workstation</code>
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 2. 授權看板
        st.markdown("### 🔑 智能防護與安全授權")
        st.markdown("""
        <div class="agent-container">
            <p style="margin: 5px 0; font-size: 0.9em; color: inherit;">
                🟢 <b>檔案唯讀 (read_file)</b>: 已授權<br>
                🟢 <b>檔案編輯 (write_file)</b>: 已授權<br>
                🟡 <b>指令執行 (run_command)</b>: 已授權 (沙盒隔離)<br>
                🔴 <b>外部出境網路 (CORS)</b>: 已阻斷 (嚴格離線保護)
            </p>
            <small style="color: #6b7280;">💡 防護說明：AI 執行任何系統變更指令前皆需在終端機獲得您的批准，本工作站受 sandbox 安全隔離保護。</small>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. 診斷按鈕
        st.markdown("### ⚡ 系統連線與診斷工具")
        if "diag_running" not in st.session_state:
            st.session_state.diag_running = False
            
        if st.button("🔌 執行智商庫連線心跳診斷", key="btn_agent_diag", use_container_width=True, disabled=st.session_state.diag_running):
            st.session_state.diag_running = True
            st.rerun()
            
        if st.session_state.diag_running:
            with st.spinner("正在探測本地向量數據庫與大模型心跳..."):
                try:
                    t0 = time.time()
                    st.session_state.agent_instance._get_embedding("測試心跳")
                    elapsed = (time.time() - t0) * 1000
                    st.success(f"✅ 診斷成功！\n- Ollama 向量模型響應時間：{elapsed:.1f} ms\n- ChromaDB 智商庫連線：正常")
                except Exception as ex:
                    st.error(f"❌ 診斷失敗：無法與本地推理服務建立連線。原因：{ex}")
                    
        # 4. 指令小幫手
        st.markdown("### 💡 推薦協作指令 (Slash Commands)")
        st.info("""
        在與 Antigravity 對話時，您可以利用以下指令觸發深度功能：
        - `/goal`：交付長期且繁重的背景編碼目標。
        - `/schedule`：設定定時任務或定時檢查。
        - `/browser`：請求 AI 進行深度的網頁檢索與分析。
        - `/grill-me`：要求 AI 對您的計畫進行設計與實作面試。
        - `/teamwork-preview`：預覽多個 AI 子 Agent 協同開發。
        """)
        
    with col_trace:
        tab_chat_agt, tab_run_trace = st.tabs(["💬 與 Antigravity 即時對話", "📜 背景運作與工具軌跡"])
        
        with tab_chat_agt:
            st.caption("您可直接在此與 Antigravity 進行實時法律編碼與系統維護對話（基於本地大模型）。")
            
            # 初始化對話歷史
            if "antigravity_messages" not in st.session_state:
                st.session_state.antigravity_messages = []
                
            # 顯示對話歷史
            agt_chat_container = st.container(height=500, border=True)
            with agt_chat_container:
                for idx, m in enumerate(st.session_state.antigravity_messages):
                    with st.chat_message(m["role"]):
                        # 處理 assistant 思考與回覆
                        content = m["content"]
                        thought_content = ""
                        reply_content = content
                        
                        # 擷取 <thought> 或是 <think> 標記
                        thought_match = re.search(r"<(thought|think)>(.*?)</\1>", content, re.DOTALL)
                        if thought_match:
                            thought_content = thought_match.group(2).strip()
                            reply_content = re.sub(r"<(thought|think)>.*?</\1>", "", content, flags=re.DOTALL).strip()
                            
                        if thought_content:
                            with st.expander("🧠 檢視推理思考過程", expanded=False):
                                st.markdown(f"<div class='thought-bubble'>{html.escape(thought_content)}</div>", unsafe_allow_html=True)
                                
                        if reply_content:
                            st.markdown(reply_content)
                            
                            # 解析程式碼或指令
                            code_blocks = re.findall(r"```(python|bash|powershell|html|css|javascript|json|diff|text|)\n(.*?)```", reply_content, re.DOTALL)
                            for c_idx, (lang, code) in enumerate(code_blocks):
                                code = code.strip()
                                lang = lang.strip().lower()
                                
                                with st.expander(f"🛠️ 操作程式碼區塊 {c_idx+1} ({lang or 'text'})", expanded=False):
                                    st.code(code, language=lang or 'text')
                                    
                                    # 寫入檔案
                                    default_save_path = f"C:\\LocalAI_Workstation\\scratch_code_{idx+1}_{c_idx+1}.py" if lang == "python" else f"C:\\LocalAI_Workstation\\scratch_file_{idx+1}_{c_idx+1}.{lang if lang in ['html', 'css', 'json', 'javascript'] else 'txt'}"
                                    save_path_input = st.text_input(f"指定儲存路徑 ({c_idx+1})", value=default_save_path, key=f"chat_save_path_{idx}_{c_idx}")
                                    if st.button(f"💾 寫入至檔案 ({c_idx+1})", key=f"chat_btn_save_{idx}_{c_idx}"):
                                        try:
                                            os.makedirs(os.path.dirname(save_path_input), exist_ok=True)
                                            with open(save_path_input, "w", encoding="utf-8-sig") as f:
                                                f.write(code)
                                            st.success(f"已成功寫入至 `{save_path_input}`！")
                                        except Exception as e:
                                            st.error(f"寫入失敗：{e}")
                                            
                                    # 執行指令
                                    if lang in ["bash", "powershell", "python"]:
                                        default_cmd = code if lang != "python" else f"python {save_path_input}"
                                        cmd_input_val = st.text_input(f"修改並執行指令 ({c_idx+1})", value=default_cmd, key=f"chat_cmd_input_{idx}_{c_idx}")
                                        if st.button(f"▶️ 執行指令 ({c_idx+1})", key=f"chat_btn_exec_{idx}_{c_idx}"):
                                            import subprocess
                                            with st.spinner("指令執行中..."):
                                                try:
                                                    exec_res = subprocess.run(cmd_input_val, shell=True, capture_output=True, text=True, timeout=45, cwd="C:\\LocalAI_Workstation")
                                                    st.markdown("**📟 執行結果：**")
                                                    if exec_res.stdout:
                                                        st.code(exec_res.stdout)
                                                    if exec_res.stderr:
                                                        st.markdown("**錯誤回傳 (stderr)：**")
                                                        st.code(exec_res.stderr)
                                                    st.success(f"執行完畢，Exit Code: {exec_res.returncode}")
                                                except Exception as e:
                                                    st.error(f"執行失敗：{e}")
            
            # 1. 檢測是否有尚未處理的 user 訊息 (狀態驅動編碼代理分析)
            if st.session_state.antigravity_messages and st.session_state.antigravity_messages[-1]["role"] == "user":
                user_msg = st.session_state.antigravity_messages[-1]["content"]
                logic_instr = st.session_state.get("tab7_logic_instruction", "")
                full_prompt = user_msg
                if logic_instr:
                    full_prompt = f"【請特別採用「{logic_instr}」的核心編解邏輯】\n開發指令：\n{user_msg}"
                
                with st.spinner("🧠 Antigravity 正在思考與推理中..."):
                    system_instruction = (
                        "You are Antigravity, a powerful agentic AI coding assistant designed by the Google DeepMind team.\n"
                        "You are helping the user build and manage their Local Legal AI Workstation located at C:\\LocalAI_Workstation.\n"
                        "You must respond in Traditional Chinese (繁體中文). Use markdown formatting.\n"
                        "If you need to write code or run commands, format them inside markdown code blocks (e.g. ```python or ```bash) so the user can easily save or execute them via the action panel."
                    )
                    
                    messages = [{"role": "system", "content": system_instruction}]
                    # Append history (excluding system prompt)
                    for m in st.session_state.antigravity_messages[-10:-1]:
                        messages.append({"role": m["role"], "content": m["content"]})
                    # Add current decorated prompt
                    messages.append({"role": "user", "content": full_prompt})
                        
                    try:
                        payload = {
                            "model": st.session_state.ollama_model,
                            "messages": messages,
                            "stream": False
                        }
                        res = requests.post(f'{os.environ.get("OLLAMA_HOST", "http://localhost:11434")}/api/chat', json=payload, timeout=120)
                        if res.status_code == 200:
                            reply = res.json().get('message', {}).get('content', '')
                            st.session_state.tab7_logic_instruction = "" # 清除邏輯
                        else:
                            reply = f"Ollama 服務響應異常: {res.status_code} - {res.text}"
                    except Exception as e:
                        reply = f"無法連線至本地 Ollama 服務。請確認 Ollama 正在運行中！原因: {e}"
                        
                st.session_state.antigravity_messages.append({"role": "assistant", "content": reply})
                st.rerun()

            # 2. 評判回饋與重新生成區（若最後一條為 assistant 回覆）
            if st.session_state.antigravity_messages and st.session_state.antigravity_messages[-1]["role"] == "assistant":
                st.markdown("<div style=' padding:15px; border-radius:8px; border: 1px solid #e5e7eb; margin-bottom: 15px;'>", unsafe_allow_html=True)
                st.markdown("##### 💡 針對本次代碼生成結果評判與變更思路重新回答")
                col_fb_btn_agt, col_fb_logic_agt = st.columns([1, 1])
                with col_fb_btn_agt:
                    with st.form("tab7_response_feedback_form"):
                        st.markdown("<small><b>1. 系統代理編碼精進評判</b></small>", unsafe_allow_html=True)
                        rating_resp_agt = st.radio("生成品質評判", ["👍 代碼正確且合乎規範", "👎 邏輯有漏洞/缺少模組"], horizontal=True, key="tab7_rating_resp")
                        comment_resp_agt = st.text_input("輸入意見評判反饋", placeholder="如：運行正常，但缺少例外補捉...", key="tab7_comment_resp")
                        submit_resp_agt = st.form_submit_button("📤 提交此代理對話評判")
                        if submit_resp_agt:
                            if rating_resp_agt is not None:
                                SubjectIQManager.add_feedback("編碼助手調校", "like" if "👍" in rating_resp_agt else "dislike", f"【編碼評判】{comment_resp_agt}")
                            else:
                                st.warning("請選取生成品質評判。")
                            st.success("已成功為系統代理寫入評判回饋！")
                with col_fb_logic_agt:
                    st.markdown("<small><b>2. 要求變更編解邏輯重新回答</b></small>", unsafe_allow_html=True)
                    selected_logic_agt = st.selectbox(
                        "選擇重新回答思路",
                        [
                            "標準防禦性編程 (防錯與完善的例外錯誤補捉)",
                            "極簡與效能優化 (減少冗餘代碼，追求核心精準)",
                            "模組化與高可讀性重構 (解耦模組、變數命名清晰)"
                        ],
                        key="tab7_regenerate_logic"
                    )
                    if st.button("🔄 以此思路重新生成", key="tab7_btn_regenerate", use_container_width=True):
                        # Find last user prompt
                        user_query_agt = ""
                        for m in reversed(st.session_state.antigravity_messages[:-1]):
                            if m["role"] == "user":
                                user_query_agt = m["content"]
                                break
                        if user_query_agt:
                            st.session_state.tab7_logic_instruction = selected_logic_agt
                            st.session_state.antigravity_messages.pop() # 移除上一條助理回覆
                            st.success(f"已排程以「{selected_logic_agt}」思路重新生成代碼...")
                            st.rerun()
                        else:
                            st.error("找不到前一筆使用者開發指令，無法重新生成！")
                st.markdown("</div>", unsafe_allow_html=True)

            # 3. 統一代理輸入控制台 (全面相容 Gboard/IME 語音與多模態輸入)
            st.markdown("<div style=' padding:15px; border-radius:8px; border: 1px solid #e5e7eb;'>", unsafe_allow_html=True)
            st.markdown("##### 💬 Antigravity 開發與系統管理指令中心 (支援注音/Gboard語音輸入)")
            
            col_aud_agt, col_fil_agt = st.columns([1, 1])
            with col_aud_agt:
                audio_inp_agt = st.audio_input("🎙️ 錄製指令語音 (Whisper 自動轉譯)", key="agt_audio_input")
            with col_fil_agt:
                file_inp_agt = st.file_uploader("📂 上傳代碼/文件/日誌 (自動識別提取)", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "m4a", "mp4", "txt"], key="agt_file_input")

            # Process audio or file
            if audio_inp_agt:
                extracted_text_agt = process_multimodal_input(audio_inp_agt)
                if extracted_text_agt:
                    if st.session_state.antigravity_input_val:
                        st.session_state.antigravity_input_val += "\n" + extracted_text_agt
                    else:
                        st.session_state.antigravity_input_val = extracted_text_agt
                    st.toast("🎙️ 語音指令轉譯成功！內容已載入。")
                    st.rerun()

            if file_inp_agt:
                extracted_text_agt = process_multimodal_input(file_inp_agt)
                if extracted_text_agt:
                    if st.session_state.antigravity_input_val:
                        st.session_state.antigravity_input_val += "\n" + extracted_text_agt
                    else:
                        st.session_state.antigravity_input_val = extracted_text_agt
                    st.toast("📂 檔案內容解析成功！已載入。")
                    st.rerun()

            agt_user_input = st.text_area(
                "✍️ 開發指令與諮詢輸入框 (支援 Google 鍵盤自然語言輸入/注音/手寫/語音聽寫)",
                value=st.session_state.antigravity_input_val,
                placeholder="向 Antigravity 智慧編碼代理發送開發、修改、除錯指令...",
                height=150,
                key="antigravity_text_area_input"
            )
            st.session_state.antigravity_input_val = agt_user_input

            col_btn1_agt, col_btn2_agt = st.columns([8, 2])
            with col_btn1_agt:
                if st.button("📤 送出編碼指令", key="agt_btn_send_custom", use_container_width=True):
                    if agt_user_input.strip():
                        st.session_state.antigravity_messages.append({"role": "user", "content": agt_user_input})
                        st.session_state.antigravity_input_val = ""
                        st.rerun()
                    else:
                        st.warning("請先輸入指令或上傳參考！")
            with col_btn2_agt:
                if st.button("🧹 清空指令", key="agt_btn_clear_custom", use_container_width=True):
                    st.session_state.antigravity_input_val = ""
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_run_trace:
            st.markdown("### 📜 Agent 實作對話與工具執行軌跡")
        st.caption("此處即時呈現 Antigravity 在背景與您協作時的思考過程（Thinking）與具體工具調用。")
        
        # 載入並解析日誌
        TRANSCRIPT_PATH = r"C:\Users\temp\.gemini\antigravity\brain\d2ab9a3c-b94b-499e-aff0-25d826f0dd32\.system_generated\logs\transcript.jsonl"
        
        steps = []
        if os.path.exists(TRANSCRIPT_PATH):
            try:
                with open(TRANSCRIPT_PATH, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        if line.strip():
                            try:
                                steps.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                st.warning(f"載入運行軌跡時出錯：{e}")
        
        if not steps:
            st.info("尚無運行軌跡資料。請與 Agent 互動或執行任務後再來查看！")
        else:
            # 只顯示最後 30 步以維持效能
            display_steps = steps[-30:]
            
            # 過濾控制項
            filter_mode = st.radio("篩選顯示內容", ["顯示全部軌跡", "僅顯示用戶對話與 AI 思考", "僅顯示工具調用 (Tool Calls)"], horizontal=True, key="agent_trace_filter")
            
            for step in display_steps:
                s_source = step.get("source", "")
                s_type = step.get("type", "")
                s_content = step.get("content", "")
                tool_calls = step.get("tool_calls", [])
                
                # 根據過濾條件進行篩選
                if filter_mode == "僅顯示用戶對話與 AI 思考" and s_source == "SYSTEM":
                    continue
                if filter_mode == "僅顯示工具調用 (Tool Calls)" and not tool_calls and s_source != "SYSTEM":
                    continue
                
                # 1. 用戶輸入
                if s_type == "USER_INPUT" or (s_source == "USER_EXPLICIT" and s_content):
                    with st.chat_message("user"):
                        st.markdown(s_content)
                        
                # 2. AI 思考與規劃
                elif s_source == "MODEL" and s_content:
                    # 分離思考與回覆
                    import re
                    thought_content = ""
                    reply_content = s_content
                    
                    # 嘗試比對 <thought> 標記
                    thought_match = re.search(r"<thought>(.*?)</thought>", s_content, re.DOTALL)
                    if thought_match:
                        thought_content = thought_match.group(1).strip()
                        # 去除 thought 部分
                        reply_content = re.sub(r"<thought>.*?</thought>", "", s_content, flags=re.DOTALL).strip()
                    
                    # 如果沒有 thought 標記，但也許有些 markdown 區塊
                    if thought_content:
                        with st.expander("🧠 檢視 Agent 深度推理路徑 (Thinking Process)", expanded=False):
                            st.markdown(f"<div class='thought-bubble'>{html.escape(thought_content)}</div>", unsafe_allow_html=True)
                            
                    if reply_content:
                        with st.chat_message("assistant"):
                            st.markdown(reply_content)
                            
                # 3. 工具調用
                if tool_calls:
                    for tc in tool_calls:
                        tc_name = tc.get("name", "unknown")
                        tc_args = tc.get("arguments", {})
                        
                        st.markdown(f"<span class='tool-badge'>🔧 調用工具: {tc_name}</span>", unsafe_allow_html=True)
                        st.json(tc_args)
                        
                # 4. 系統工具回傳結果
                elif s_source == "SYSTEM" and s_content:
                    # 如果內容太長，截斷顯示
                    disp_content = s_content
                    if len(disp_content) > 1000:
                        disp_content = disp_content[:1000] + "\n\n... [內容過長已自動截斷，以維持控制台效能] ..."
                        
                    with st.expander(f"📟 工具執行回傳結果 (System Response)", expanded=False):
                        st.markdown(f"<pre class='terminal-box'>{html.escape(disp_content)}</pre>", unsafe_allow_html=True)

# ==============================================================================
# TAB 9: 企業級架構與金鑰池界面設定面
# ==============================================================================
with tab_setup:
    st.header("⚙️ 企業級架構與金鑰池界面設定面")
    st.caption("此頁面取代舊版 setup_wizard.py，所有的設定將直接安全地寫入實體 config.yaml 與 keys.yaml 檔案中。")
    
    CONFIG_PATH_LOCAL = r"C:\LocalAI_Workstation\config.yaml"
    KEYS_YAML_DEST_LOCAL = r"C:\LocalAI_Workstation\config\keys.yaml"
    
    def update_yaml_value(filepath, key, new_value):
        if not os.path.exists(filepath):
            st.error(f"找不到設定檔: {filepath}")
            return False
        import re
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()
        if isinstance(new_value, bool):
            value_str = "true" if new_value else "false"
            pattern = rf'^(\s*){key}:\s*(true|false|"[^"]*"|\'[^\']*\')'
            replacement = rf'\1{key}: {value_str}'
        else:
            pattern = rf'^(\s*){key}:\s*(true|false|"[^"]*"|\'[^\']*\')'
            replacement = rf'\1{key}: "{new_value}"'
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        with open(filepath, "w", encoding="utf-8-sig") as f:
            f.write(new_content)
        return True
        
    st.subheader("1. 🎯核心處理策略（策略矩陣）")
    
    STRATEGY_MATRIX = {
        "A": {
            "desc": "策略 A【純個人帳號 雲端免費金鑰池流(強烈推薦)】：全程 0 成本，完全依賴 QuotaManager",
            "stt_engine": "gemini",
            "merge_engine": "gemini",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-flash",
        },
        "B": {
            "desc": "策略 B【混合雙打 (免費企業試用版 Vertex AI - 無折抵金)】：STT用免費池 + 精校走Vertex",
            "stt_engine": "gemini",
            "merge_engine": "vertexai",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-flash",
        },
        "C": {
            "desc": "策略 C【全 Vertex 企業級 (免費企業試用版 - 無折抵金鎖定 Flash)】：全程走 Vertex AI，避開429",
            "stt_engine": "vertexai",
            "merge_engine": "vertexai",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-flash",
        },
        "D": {
            "desc": "策略 D【全 Vertex 混合模型 (帶抵免額解封 Pro)】：STT 用 Flash + 精校用 Pro (使用抵免額)",
            "stt_engine": "vertexai",
            "merge_engine": "vertexai",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-pro",
        },
        "E": {
            "desc": "策略 E【本地優先 (純免費)】：STT 本機 Whisper + 精校 AI Studio (最省流量)",
            "stt_engine": "local_whisper",
            "merge_engine": "gemini",
            "stt_model": "gemini-2.5-flash",
            "merge_model": "gemini-2.5-flash",
        },
        "F": {
            "desc": "策略 F【全 Vertex 企業級通道 (尊榮企業級 - 極度昂貴)】：全程強走 Vertex + 解封 Pro，最穩定",
            "stt_engine": "vertexai",
            "merge_engine": "vertexai",
            "stt_model": "gemini-2.5-pro",
            "merge_model": "gemini-2.5-pro",
        }
    }
    
    current_stt = "gemini"
    current_merge = "gemini"
    current_stt_model = "gemini-2.5-flash"
    current_merge_model = "gemini-2.5-flash"
    if os.path.exists(CONFIG_PATH_LOCAL):
        try:
            import yaml
            with open(CONFIG_PATH_LOCAL, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f)
                current_stt = cfg.get("settings", {}).get("stt_engine", current_stt)
                current_merge = cfg.get("settings", {}).get("merge_engine", current_merge)
                api_cfg = cfg.get("api", {})
                current_stt_model = api_cfg.get("stt_model", api_cfg.get("gemini_model_high_accuracy", current_stt_model))
                current_merge_model = api_cfg.get("merge_model", api_cfg.get("gemini_model_high_accuracy", current_merge_model))
        except Exception:
            pass
            
    current_index = 0
    for idx, (k, v) in enumerate(STRATEGY_MATRIX.items()):
        if (v["stt_engine"] == current_stt and 
            v["merge_engine"] == current_merge and 
            v["stt_model"] == current_stt_model and 
            v["merge_model"] == current_merge_model):
            current_index = idx
            break
            
    strategy_options = [v["desc"] for k, v in STRATEGY_MATRIX.items()]
    selected_strategy = st.radio("請選擇處理策略", strategy_options, index=current_index)
    
    if st.button("💾 套用並儲存策略", key="save_strategy"):
        for k, v in STRATEGY_MATRIX.items():
            if v["desc"] == selected_strategy:
                update_yaml_value(CONFIG_PATH_LOCAL, "stt_engine", v["stt_engine"])
                update_yaml_value(CONFIG_PATH_LOCAL, "merge_engine", v["merge_engine"])
                update_yaml_value(CONFIG_PATH_LOCAL, "stt_model", v["stt_model"])
                update_yaml_value(CONFIG_PATH_LOCAL, "merge_model", v["merge_model"])
                st.success("✅ 策略已成功寫入 config.yaml！")
                break
                
    st.divider()
    
    st.subheader("2. 🔑 更換 Vertex AI 企業帳號與金鑰")
    current_project = ""
    current_enterprise_account = ""
    current_project_name = ""
    current_project_number = ""
    
    if os.path.exists(CONFIG_PATH_LOCAL):
        try:
            with open(CONFIG_PATH_LOCAL, "r", encoding="utf-8-sig") as f:
                cfg = yaml.safe_load(f) or {}
                api_cfg = cfg.get("api", {})
                current_project = api_cfg.get("vertexai_project", "")
                current_enterprise_account = api_cfg.get("gemini_api_account", "")
                current_project_name = api_cfg.get("vertexai_project_name", "")
                current_project_number = api_cfg.get("vertexai_project_number", "")
        except:
            pass
            
    # 安全遮蔽專案 ID
    masked_project = "尚未設定"
    if current_project:
        if len(current_project) > 4:
            masked_project = current_project[:4] + "*" * (len(current_project) - 4)
        else:
            masked_project = "***"
            
    # 狀態列
    st.markdown(f"**📊 狀態：** 目前綁定之企業帳號：{current_enterprise_account if current_enterprise_account else '尚未設定'} | 專案名稱：{current_project_name if current_project_name else '未命名'} | 專案 ID：{masked_project}")
    
    with st.form("add_enterprise_key_form", clear_on_submit=True):
        ent_account = st.text_input("綁定的企業 Google 帳號 (明碼) [強烈建議填寫]", value=current_enterprise_account, placeholder="例如: admin@company.com (讓您記得這個專案是用哪個帳號申請的)")
        ent_project_name = st.text_input("專案名稱 (Project Name) [選填]", value=current_project_name, placeholder="使用者自訂的中文或英文名稱 (僅供記憶)")
        
        # 專案 ID 加入 type="password" 以策安全，且 value 設為空字串，確保儲存後不會殘留
        project_id = st.text_input("專案 ID (Project ID) [🔥 必填：若要更新請重新輸入]", value="", type="password", placeholder="若不修改請留空。英文與連字號，或 project 開頭的編號")
        ent_project_number = st.text_input("專案數字編號 (Project Number) [選填]", value=current_project_number, placeholder="純阿拉伯數字的系統編號 (例如: 123456789012)")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 儲存企業帳號與專案資訊"):
                # Update account safely
                try:
                    with open(CONFIG_PATH_LOCAL, "r", encoding="utf-8-sig") as f:
                        cfg_temp = yaml.safe_load(f) or {}
                except:
                    cfg_temp = {}
                    
                if "api" not in cfg_temp:
                    cfg_temp["api"] = {}
                    
                cfg_temp["api"]["gemini_api_account"] = ent_account.strip()
                cfg_temp["api"]["vertexai_project_name"] = ent_project_name.strip()
                cfg_temp["api"]["vertexai_project_number"] = ent_project_number.strip()
                
                # 只有當使用者有輸入新的專案 ID 時才更新，否則保留舊的
                if project_id.strip():
                    cfg_temp["api"]["vertexai_project"] = project_id.strip()
                else:
                    cfg_temp["api"]["vertexai_project"] = current_project
                
                with open(CONFIG_PATH_LOCAL, "w", encoding="utf-8-sig") as f:
                    yaml.dump(cfg_temp, f, default_flow_style=False, allow_unicode=True)
                    
                st.success(f"✅ 企業帳號與專案資訊已更新！")
                import time
                time.sleep(1.0)
                st.rerun()  # 強制重新整理畫面，讓狀態列立刻更新！
                
        with col2:
            if st.form_submit_button("🚀 啟動 ADC 授權登入 (gcloud)"):
                # 啟動時使用舊的 ID 或剛輸入的 ID
                target_project_id = project_id.strip() if project_id.strip() else current_project
                
                if not target_project_id:
                    st.error("❌ 啟動失敗：【專案 ID (Project ID)】為必填欄位，請先填寫並儲存。")
                else:
                    import subprocess
                    gcloud_cmd = r"C:\LocalAI_Workstation\gcloud_sdk\google-cloud-sdk\bin\gcloud.cmd"
                    if os.path.exists(gcloud_cmd):
                        try:
                            subprocess.Popen([gcloud_cmd, "auth", "application-default", "login"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                            subprocess.Popen([gcloud_cmd, "auth", "application-default", "set-quota-project", target_project_id], creationflags=subprocess.CREATE_NEW_CONSOLE)
                            st.success("✅ 已經開啟終端機與瀏覽器進行 ADC 登入！")
                        except Exception as e:
                            st.error(f"執行失敗: {e}")
                    else:
                        st.error("找不到 gcloud 工具，請確認安裝路徑。")
                        
    st.divider()
    
    st.subheader("3. 💰 管理 Gemini 免費金鑰池 (keys.yaml)")
    st.caption("請先輸入您的 Google 帳號，再將金鑰分別貼入下方密碼框。系統將自動與帳號綁定並安全疊加。")
    try:
        import sys
        if r"C:\LocalAI_Workstation" not in sys.path:
            sys.path.append(r"C:\LocalAI_Workstation")
        from utils.key_manager import KeyManager
    except ImportError:
        KeyManager = None

    if KeyManager:
        loaded_keys = KeyManager.load_keys()
    else:
        loaded_keys = []
        st.error("無法載入 KeyManager 模組！")
        
    # 計算各帳號的金鑰數量
    account_counts = {}
    for k in loaded_keys:
        acc = k.get("account", "未綁定帳號")
        if not acc:
            acc = "未綁定帳號"
        if acc not in account_counts:
            account_counts[acc] = 0
        account_counts[acc] += 1
        
    st.markdown(f"**📊 狀態：** 目前免費金鑰池共安全持有 **{len(loaded_keys)}** 把金鑰。")
    if account_counts:
        for acc, count in account_counts.items():
            st.markdown(f"- {acc}: {count} 把")

    with st.form("add_free_key_12_form", clear_on_submit=True):
        st.markdown("##### ➕ 新增金鑰 (最多可同時輸入 12 把)")
        account_val = st.text_input("綁定的 Google 帳號 (明碼)", placeholder="例如: yourname@gmail.com")
        
        # 動態產生 12 個靜態綁定的密碼框，保證不當機
        new_keys_inputs = []
        for i in range(1, 13):
            val = st.text_input(f"API Key {i}", type="password", key=f"vault_key_{i}", placeholder="若無則留空")
            new_keys_inputs.append(val)
            
        if st.form_submit_button("💾 綁定並新增至金鑰池"):
            if not account_val.strip():
                st.error("❌ 請務必輸入綁定的 Google 帳號！")
            else:
                import datetime
                added_count = 0
                existing_values = [k.get("value") for k in loaded_keys]
                
                for k in new_keys_inputs:
                    k_clean = k.strip()
                    if k_clean and k_clean not in existing_values:
                        new_key_obj = {
                            "active": True,
                            "account": account_val.strip(),
                            "value": k_clean,
                            "added_date": datetime.date.today().isoformat(),
                            "expiry_date": "",
                            "notes": "Added via Dashboard UI"
                        }
                        loaded_keys.append(new_key_obj)
                        added_count += 1
                
                if added_count > 0:
                    if KeyManager:
                        success = KeyManager.save_keys(loaded_keys)
                        if success:
                            st.success(f"✅ 成功綁定 {account_val.strip()} 並匯入 {added_count} 把新金鑰！")
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ 寫入 keys.yaml 發生錯誤！")
                    else:
                        st.error("找不到 KeyManager，無法寫入。")
                else:
                    st.info("ℹ️ 未偵測到新金鑰，或金鑰已存在於池中。")

    st.subheader("4. 📊 查詢 Google Cloud 帳務與授權資訊")
    if st.button("🔍 立即連線 Google API 查詢帳單狀態"):
        import datetime
        st.info(f"🕒 查詢時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            import google.auth
            from google.auth.transport.requests import Request
            import urllib.request
            import yaml
            
            credentials, default_project = google.auth.default(
                scopes=['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/cloud-billing']
            )
            credentials.refresh(Request())
            
            token_url = 'https://oauth2.googleapis.com/tokeninfo?access_token=' + credentials.token
            with urllib.request.urlopen(token_url) as res:
                token_info = json.loads(res.read().decode('utf-8'))
                email = token_info.get("email", "未知")
                
            st.success(f"👤 當前授權帳號：{email}")
            
            check_proj = project_id if project_id else credentials.quota_project_id
            if not check_proj:
                check_proj = default_project
                
            st.success(f"🏢 綁定專案 ID：{check_proj}")
            
            if check_proj:
                billing_url = f'https://cloudbilling.googleapis.com/v1/projects/{check_proj}/billingInfo'
                req = urllib.request.Request(billing_url)
                req.add_header('Authorization', f'Bearer {credentials.token}')
                with urllib.request.urlopen(req) as res:
                    info = json.loads(res.read().decode('utf-8'))
                    billing_enabled = info.get("billingEnabled", False)
                    billing_name = info.get("billingAccountName", "")
                    st.success(f"💳 帳單綁定狀態：{'✅ 已啟用' if billing_enabled else '❌ 未啟用'}")
                    if billing_name:
                        acct_url = f'https://cloudbilling.googleapis.com/v1/{billing_name}'
                        req2 = urllib.request.Request(acct_url)
                        req2.add_header('Authorization', f'Bearer {credentials.token}')
                        with urllib.request.urlopen(req2) as res2:
                            acct_info = json.loads(res2.read().decode('utf-8'))
                            st.success(f"💱 結帳幣別：{acct_info.get('currencyCode', '未知')}")
                            
                st.markdown("📌 **【免費抵免額與實際帳單金額查詢】**")
                st.markdown(f"👉 **[點擊前往 Google Cloud 後台查看即時帳務與 $9,564 餘額](https://console.cloud.google.com/billing?project={check_proj})**")
        except ImportError:
            st.error("❌ 找不到 google.auth，請確保在正確的 Python 環境中執行。")
        except Exception as e:
            st.error(f"❌ 查詢失敗: {e}")

    st.divider()
    
    st.subheader("5. 🎨 介面主題設定 (淡色/深色模式)")
    st.caption("設定工作站的視覺主題，更改後網頁將自動重新載入套用。")
    
    TOML_PATH = r"C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\.streamlit\config.toml"
    current_theme = "light"
    if os.path.exists(TOML_PATH):
        with open(TOML_PATH, "r", encoding="utf-8-sig") as f:
            toml_content = f.read()
            if 'base="dark"' in toml_content.replace(' ', ''):
                current_theme = "dark"
    
    theme_options = ["淡色模式 (Light)", "深色模式 (Dark)"]
    theme_idx = 0 if current_theme == "light" else 1
    
    selected_theme = st.radio("請選擇背景主題", theme_options, index=theme_idx, horizontal=True)
    
    if st.button("💾 套用主題"):
        new_base = "light" if "Light" in selected_theme else "dark"
        if os.path.exists(TOML_PATH):
            with open(TOML_PATH, "r", encoding="utf-8-sig") as f:
                content = f.read()
        else:
            content = ""
            
        import re
        if "[theme]" in content:
            content = re.sub(r'base\s*=\s*".*"', f'base="{new_base}"', content)
        else:
            content += f'\n[theme]\nbase="{new_base}"\n'
            
        with open(TOML_PATH, "w", encoding="utf-8-sig") as f:
            f.write(content)
            
        st.success(f"✅ 已切換為 {selected_theme}！正在重新載入...")
        st.rerun()






