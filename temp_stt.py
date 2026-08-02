import os
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import sys
# Append project root to sys.path to resolve ModuleNotFoundError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import yaml
import time
import datetime
import subprocess
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from google import genai
from google.genai import types
from scripts.quota_manager import QuotaManager
from scripts.whisper_pool import WhisperPool
from scripts.model_router import get_router  # Model Router Agent — 全權負責模型切換
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
    
    # 三級載入防崩潰降備網路
    model = None
    if device == "cuda":
        try:
            logging.info("Attempting load: device=cuda, compute_type=float16")
            model = WhisperModel(model_name, device="cuda", compute_type="float16")
            logging.info("Whisper model loaded successfully with float16 on CUDA.")
        except Exception as e:
            logging.warning(f"Failed loading CUDA float16: {e}. Trying CUDA float32...")
            try:
                model = WhisperModel(model_name, device="cuda", compute_type="float32")
                logging.info("Whisper model loaded successfully with float32 on CUDA.")
            except Exception as e2:
                logging.warning(f"Failed loading CUDA float32: {e2}. Falling back to CPU.")
                device = "cpu"
                
    if device == "cpu":
        try:
            logging.info("Attempting load: device=cpu, compute_type=int8")
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            logging.info("Whisper model loaded successfully with int8 on CPU.")
        except Exception as e3:
            logging.error(f"Failed loading CPU int8: {e3}. Trying CPU float32...")
            model = WhisperModel(model_name, device="cpu", compute_type="float32")
            logging.info("Whisper model loaded successfully with float32 on CPU.")
            
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
        logging.warning(f"[Distill Engine] CPU int8 load failed: {e}. Trying CPU float32...")
        model = WhisperModel(model_name, device="cpu", compute_type="float32")
        logging.info("[Distill Engine] Whisper CPU float32 loaded successfully.")
        return model

def transcribe_chunk_local(model, chunk_path):
    """向後相容的本地 Whisper 轉錄（單例 WhisperPool 的薄包裝）。"""
    return WhisperPool.transcribe(chunk_path)

def apply_glossary_fix(text):
    glossary = {
        "common_errors": {
            # 當事人稱謂
            "假芳": "甲方", "假方": "甲方",
            "倚芳": "乙方", "倚方": "乙方", "以方": "乙方",
            "炳芳": "丙方", "丙芳": "丙方", "炳方": "丙方",
            "丁芳": "丁方",
            # ── 高危同音錯字（xíng shì 完全同音） ──
            "形式訴訟法": "刑事訴訟法",  # 必須先替換長字串
            "形式訴訟":   "刑事訴訟",
            "形式法院":   "刑事法院",
            "形式被告":   "刑事被告",
            "形式案件":   "刑事案件",
            "形事訴訟":   "刑事訴訟",
            "形法": "刑法", "形訴": "刑訴",
            # 土地法相關
            "投地登記": "土地登記", "投地法": "土地法",
            "地政治": "地政士", "遞贈式": "地政士",
            # 時效
            "消滅實效": "消滅時效", "消滅士效": "消滅時效",
            # 各論
            "格論": "各論",
            # 口語隔了→隔了
            "割了一個": "隔了一個", "割了好幾": "隔了好幾",
            # 常見口誤
            "抵銷法": "抵押法", "行政府": "行政府",
        }
    }
    fixed_text = text
    for wrong, right in glossary.get("common_errors", {}).items():
        fixed_text = re.sub(wrong, right, fixed_text)
    return fixed_text

# ────────────────────────────────────────────────────────────────
# 並列 chunk 處理核心函式
# ────────────────────────────────────────────────────────────────

CHUNK_CONCURRENCY = 1  # 尖峰期降為 1：8 tasks × 1 chunk = 8 同時連線

API_UPLOAD_TIMEOUT      = 90   # 秒——上傳 WAV 超時
API_TRANSCRIBE_TIMEOUT  = 150  # 秒——轉寫超時（Google 接受但長時間不回應會讓 worker 永遠等待）

def _call_with_timeout(func, timeout_sec, *args, **kwargs):
    """Windows 相容的微簋式 Timeout——用 daemon 執行緒 + Event 實作。
    鴩 timeout 後援棄 (daemon thread 在主進程結束時自動消失)。"""
    import threading
    result_box = [None]
    error_box  = [None]
    done_evt   = threading.Event()

    def _target():
        try:
            result_box[0] = func(*args, **kwargs)
        except Exception as _e:
            error_box[0]  = _e
        finally:
            done_evt.set()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    fired = done_evt.wait(timeout_sec)
    if not fired:
        raise TimeoutError(f"{func.__name__} 逾時 {timeout_sec}s，放棄此呼叫")
    if error_box[0]:
        raise error_box[0]
    return result_box[0]


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
    retry_limit = 6   # 503 高峰期增強耐心：最多重試 6 次（原 3 次）
    uploaded_file = None
