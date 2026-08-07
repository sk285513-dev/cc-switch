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

BUFFER_FILE = "A:\\manifests_v6_test\\chosen_paths_buffer.json"

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

INGESTED_HISTORY_FILE = "A:\\manifests_v6_test\\ingested_history.json"

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
    
    STATE_FILE = "A:\\manifests_v6_test\\ingest_state.json"
    
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
    FILE_PATH = "A:\\manifests_v6_test\\subject_intelligence.json"
    
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


