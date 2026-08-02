import os
import sys
# Append project root to sys.path to resolve ModuleNotFoundError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
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

                if stt_engine == "gemini":
                    if not uploaded_file:
                        with key_lock:
                            active_key = current_key_ref[0]
                        upload_client = genai.Client(api_key=active_key)
                        logging.info(f"[Parallel STT] Uploading {chunk_filename}...")
                        uploaded_file = upload_client.files.upload(file=chunk_path)
                        logging.info(f"[Parallel STT] Uploaded → {uploaded_file.name}")
                    transcription = transcribe_chunk_gemini(upload_client, uploaded_file, config)

                elif stt_engine == "vertexai":
                    v_project = config.get("api", {}).get("vertexai_project") or config.get("settings", {}).get("vertexai_project")
                    v_loc = config.get("api", {}).get("vertexai_location") or config.get("settings", {}).get("vertexai_location", "us-central1")
                    upload_client = genai.Client(vertexai=True, project=v_project, location=v_loc)
                    
                    logging.info(f"[Parallel STT] Reading {chunk_filename} as bytes for Vertex AI...")
                    with open(chunk_path, "rb") as f:
                        audio_bytes = f.read()
                    vertex_part = genai.types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
                    logging.info(f"[Parallel STT] Prepared Part for Vertex AI")
                    transcription = transcribe_chunk_vertexai(upload_client, vertex_part, config)

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

            chunk["status"] = "completed"
            consecutive_429_count = 0
            if stt_engine == "gemini":
                qm.reset_key(current_key_ref[0])
            logging.info(f"[Parallel STT] ✅ 完成：{chunk_filename}")

            # 即時寫回 manifest（需持 per-task 鎖）
            # 注意：chunk dict 是共享的引用，其他執行緒可能也在改它，加鎖保護
            with manifest_write_lock:
                # 重新讀取（另一個執行緒可能剛寫過），只更新這個 chunk
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
                    with key_lock:
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
            chunk["retry_count"] += 1
            logging.error(
                f"[Parallel STT] chunk {chunk_filename} 失敗（{chunk['retry_count']}/{retry_limit}）：{e}"
            )
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
        chunk["status"] = "failed"
        return False
    return True


# --- 以下為被取代的舊版懸空程式碼（已廢棄，遵照指示註解而不刪除） ---
    # model = "gemini-2.5-flash"
    # if 'api' in config and 'gemini_model_low_cost' in config['api']:
    #     model = config['api']['gemini_model_low_cost']
    # elif 'gemini' in config and 'model_name' in config['gemini']:
    #     model = config['gemini']['model_name']
    # 
    # prompt = """..."""
    # 
    # time.sleep(2)
    # 
    # response = client.models.generate_content(
    #     model=model,
    #     contents=[uploaded_file, prompt]
    # )
    # return response.text
# -------------------------------------------------------------------

def get_prompt_and_model(config):
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
    return model, prompt

def transcribe_chunk_gemini(client, uploaded_file, config):
    model, prompt = get_prompt_and_model(config)
    time.sleep(2)
    response = client.models.generate_content(
        model=model,
        contents=[uploaded_file, prompt]
    )
    return response.text

def transcribe_chunk_vertexai(client, audio_part, config):
    model, prompt = get_prompt_and_model(config)
    response = client.models.generate_content(
        model=model,
        contents=[audio_part, prompt]
    )
    return response.text

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
            logging.FileHandler(workflow_log, encoding='utf-8')
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
        v_project = config.get("api", {}).get("vertexai_project") or config.get("settings", {}).get("vertexai_project")
        v_loc = config.get("api", {}).get("vertexai_location") or config.get("settings", {}).get("vertexai_location", "us-central1")
        
        if os.path.exists(cred_abs):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_abs
            logging.info(f"[STT] 使用 Vertex AI 企業通道，專案：{v_project} ({v_loc})，憑證：{v_cred_path}")
        else:
            logging.info(f"[STT] 找不到 JSON 憑證，自動改用全域 ADC 驗證，專案：{v_project} ({v_loc})")
            
        client = genai.Client(vertexai=True, project=v_project, location=v_loc)
        
        try:
            WhisperPool.get_model("medium")
        except Exception as e:
            pass

    # 共享可變金鑰引用（執行緒間傳遞）
    current_key_ref = [current_key]

    pending_chunks = [c for c in chunks if c["status"] != "completed"]
    logging.info(f"[STT] 共 {len(pending_chunks)} 個 chunk 待處理，並列度 M={CHUNK_CONCURRENCY}")

    # per-task manifest 寫入鎖
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
    subprocess.Popen(cmd, cwd=script_dir)
    return all_succeeded

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stt_runner.py {task_id}")
        sys.exit(1)
    run_stt(sys.argv[1])
