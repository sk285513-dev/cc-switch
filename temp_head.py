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
