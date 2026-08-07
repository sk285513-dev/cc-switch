# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path
import functools

# 【修復 Issue 26】架構：全域配置為單點熱點，利用 In-memory 緩存 (LRU Cache) 避免重複 I/O 讀取
@functools.lru_cache(maxsize=1)
def apply_hardware_config():
    config_path = Path('C:/LocalAI_Workstation/config.json')
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
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
        "ollama_host": "http://localhost:11434",
        "ollama_model": "deepseek-r1:7b"
    }
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["MKLNUM_THREADS"] = "4"
    return env

