# -*- coding: utf-8 -*-
import json
import os
import json
from pathlib import Path

def apply_hardware_config():
    config_path = Path('C:/LocalAI_Workstation/config.json')
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8-sig') as f:
                cfg = json.load(f)
            # Set env
            os.environ["OMP_NUM_THREADS"] = str(cfg.get("omp_num_threads", "4"))
            os.environ["MKL_NUM_THREADS"] = str(cfg.get("mkl_num_threads", "4"))
            return cfg
        except Exception as e:
            print(f"[WARNING] Config load failed: {e}")
    env = {
        "omp_num_threads": "4",
        "mkl_num_threads": "4",
        "chroma_text_limit": 150000,
        "base_path": "C:/LocalAI_Workstation",
        "whisper_gpu_id": 1,
        "chromadb_gpu_id": 1,
        "ollama_gpu_id": 0,
        "ollama_host": "http://127.0.0.1:11434",
        "ollama_model": "deepseek-r1:7b"
    }
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["MKLNUM_THREADS"] = "4"
    return env

