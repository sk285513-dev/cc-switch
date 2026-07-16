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
    upload_client = None
    last_upload_key = None   # 追蹤 upload_client 使用的金鑰（替代 ._api_key 私有屬性）
    consecutive_429_count = 0

    logging.info(f"[Parallel STT] Processing chunk: {chunk_filename}")

    while chunk["retry_count"] < retry_limit:
        try:
            # ── 雲端 Gemini 路徑 ──
            if stt_engine == "gemini":
                file_size = os.path.getsize(chunk_path)
                if file_size > 2000 * 1024 * 1024:
                    raise ValueError(f"{chunk_filename} 超過 2GB 上傳上限")

                # 若金鑰變換，清理舊雲端檔案並重新上傳
                with key_lock:
                    active_key = current_key_ref[0]

                if upload_client is not None and last_upload_key != active_key:
                    if uploaded_file:
                        try:
                            upload_client.files.delete(name=uploaded_file.name)
                        except Exception:
                            pass
                    uploaded_file = None
                    upload_client = None
                    last_upload_key = None

                if not uploaded_file:
                    with key_lock:
                        active_key = current_key_ref[0]
                    upload_client = genai.Client(api_key=active_key)
                    last_upload_key = active_key   # 記錄此 client 使用的金鑰
                    logging.info(f"[Parallel STT] Uploading {chunk_filename}...")
                    uploaded_file = _call_with_timeout(
                        upload_client.files.upload,
                        API_UPLOAD_TIMEOUT,
                        file=chunk_path
                    )
                    logging.info(f"[Parallel STT] Uploaded → {uploaded_file.name}")

                transcription = _call_with_timeout(
                    transcribe_chunk,
                    API_TRANSCRIBE_TIMEOUT,
                    upload_client, uploaded_file, config, qm=qm, api_key=active_key
                )

                # ── 【關鍵】立即存檔 Gemini 轉寫結果，不等 Whisper ──
                # Whisper 蒸餾是選配的訓練資料步驟，不影響主流程
                # 先存 .txt/.json，確保中斷也不遺失 Gemini 成果
                txt_output_path = os.path.splitext(chunk_path)[0] + ".txt"
                with open(txt_output_path, "w", encoding="utf-8") as tf:
                    tf.write(transcription or "")  # None-safe
                json_output_path = os.path.splitext(chunk_path)[0] + ".json"
                with open(json_output_path, "w", encoding="utf-8") as jf:
                    json.dump({
                        "task_id": task_id,
                        "filename": chunk_filename,
                        "part_no": chunk.get("part_no", chunk.get("chunk_id")),
                        "transcription": transcription,
                        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }, jf, ensure_ascii=False, indent=2)
                logging.info(f"[Parallel STT] 💾 Gemini 結果已落地（不等 Whisper）：{chunk_filename}")

                # ── 雙軌 ASR 蒸餾（WhisperPool 排隊，失敗不影響主流程）──
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

            else:  # local_whisper — 此路徑不應被觸發（STT 主力已鎖定為 Gemini）
                # ══ POLICY GUARD：絕不允許 Whisper 成為主力輸出 ══
                logging.critical(
                    f"[POLICY ERROR] stt_engine=local_whisper 路徑被意外觸發！"
                    f" chunk={chunk_filename}。STT 主力必須為 Gemini，此 chunk 標記失敗。"
                )
                raise RuntimeError(
                    "[POLICY] Whisper 不得作為 STT 主力。請確認 stt_engine='gemini'。"
                )


            # ── local_whisper 路徑：在此存檔（gemini 路徑已在 Whisper 之前提前存好）──
            if stt_engine != "gemini":
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

            # 非 429 錯誤：區分 503（暫時過載）和真正失敗
            if "503" in err_str or "UNAVAILABLE" in err_str or "Server disconnected" in err_str:
                # 503 = Gemini 伺服器超載，最多重試 6 次
                # 退避改短避免阻塞 Pipeline 數小時
                backoff_times = [5, 10, 15, 30, 30, 30]
                wait_503 = backoff_times[min(chunk["retry_count"], len(backoff_times)-1)]
                chunk["retry_count"] += 1
                logging.warning(
                    f"[Parallel STT] 503 暫時過載，退避 {wait_503}s 後重試 "
                    f"({chunk['retry_count']}/6)：{chunk_filename}"
                )
                with open(chunk_errors_log, "a", encoding="utf-8") as ef:
                    ef.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{task_id}][{chunk_filename}]: {e}\n")
                # 第 3 次 503 起：嘗試換金鑰（503 可能是區域性的，不同 key 可能打到不同伺服器）
                if chunk["retry_count"] == 3:
                    with key_lock:
                        current_key = current_key_ref[0]
                    try:
                        res = qm.handle_error(Exception("503"), current_key, 0)
                        new_key = res.get("new_key")
                        if new_key and new_key != current_key:
                            with key_lock:
                                current_key_ref[0] = new_key
                            uploaded_file = None   # 強制重傳至新 key
                            logging.info(f"[Parallel STT] 503×3 後換 key → {new_key[:8]}...")
                    except Exception:
                        pass
                if chunk["retry_count"] < 3:
                    time.sleep(wait_503)
                    continue
                # 超過 3 次 503 → 放棄此 chunk，task 會 reset 為 chunked 稍後重跑
            else:
                chunk["retry_count"] += 1


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


# ══════════════════════════════════════════════════════════════════
# 【2026-07-11 實測確認】金鑰池 69 個 API Key 的模型配額白名單：
#   ✅ gemini-3.5-flash        → 最高品質，法律逐字稿首選
#   ✅ gemini-flash-latest     → 3.5-flash 別名（自動指向最新）
#   ✅ gemini-3-flash-preview  → 備援，品質中等
#   ✅ gemini-2.5-flash        → 證實可用，為三級備援
#   ✅ gemini-3.1-flash-lite   → 極快但品質較低，笴駆備援
#   ❌ gemini-2.0-flash        → 429 limit:0（零配額，永久禁用）
#   ❌ gemini-2.0-flash-lite   → 429 limit:0（零配額，永久禁用）
# 模型路由全權委由 ModelRouter Agent（model_router.py）負責。
# ══════════════════════════════════════════════════════════════════
ALLOWED_MODELS = [
    "gemini-3.5-flash",        # 首選：最高品質
    "gemini-flash-latest",     # 3.5-flash 別名
    "gemini-3-flash-preview",  # 備援
    "gemini-2.5-flash",        # 三級備援
    "gemini-3.1-flash-lite",   # 笴駆備援
    "gemini-flash-lite-latest",# 笴駆備援別名
]

def _get_model_by_taiwan_time(config: dict) -> str:
    """選擇 Gemini 模型。實際路由已委由 ModelRouter，此函數僅作備用。"""
    api_section = config.get('api') or {}
    override = api_section.get('gemini_model_override')
    if override:
        if override not in ALLOWED_MODELS:
            logging.warning(f"[ModelRouter] ⚠️ override={override} 不在白名單 {ALLOWED_MODELS}，可能無配額！")
        return override
    return "gemini-3.5-flash"  # 首選最高品質模型



def transcribe_chunk(client, uploaded_file, config, qm=None, api_key=None) -> str:
    """呼叫 Gemini generateContent 將已上傳的音訊檔轉錄為繁體中文逐字稿。
    模型選擇全權委由 ModelRouter Agent 負責（見 model_router.py）。"""
    router = get_router()  # 取得進程級單例
    model = router.acquire()  # 自動選最佳可用模型

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
9. 請過濾口語贅字（嗯、啊、那個、然後、就是說），使文字流暢。
"""
    logging.info(f"[ModelRouter] 使用模型: {model} | chunk: {uploaded_file.name}")
    # ★ RPM 限速：throttle_key 保證 6s 間隔
    if qm is not None and api_key is not None:
        try:
            qm.throttle_key(api_key)
        except Exception:
            pass
    try:
        # ── Safety Settings（申訴承諾：明確設定安全門檻，符合 Google 服務條款）──
        # 法律逐字稿含刑法犯罪案例等學術內容，使用 BLOCK_ONLY_HIGH（只攔明確有害）
        # 而非 BLOCK_LOW_AND_ABOVE（過嚴，會攔學術法律內容）
        from google.genai import types as genai_types
        safety_settings = [
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ]
        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, prompt],
            config=genai_types.GenerateContentConfig(
                safety_settings=safety_settings,
                temperature=0.3,   # 降溫使法律術語辨識更嚴謹、不臆測
            )
        )
        router.report_success(model)  # 通報成功
        text = response.text
        # 防範 MALFORMED_RESPONSE / SAFETY / 空白回應：拋出讓 retry 邏輯接管
        if not text or not text.strip():
            candidates = response.candidates or []
            finish = str(getattr(candidates[0], 'finish_reason', 'UNKNOWN')) if candidates else 'NO_CANDIDATES'
            if 'SAFETY' in finish:
                raise ValueError(f"Safety filter triggered (finish_reason={finish})，換模型重試")
            raise ValueError(f"API 回傳空白內容 (finish_reason={finish})，觸發 retry")
        return text
    except Exception as e:
        router.report_error(model, e)  # 通報錯誤，自動計算冷卻
        raise  # 讓 process_single_chunk 的 retry 邏輯繼續接管



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
        
    # ══════════════════════════════════════════════════════════════
    # 【強制規定】STT 主力永遠使用 Gemini 雲端，絕不降備至本地 Whisper。
    # Whisper 僅在 process_chunk() 內作為「蒸餾輔助」背景執行，
    # 不得作為 .txt 主輸出的來源。
    # ══════════════════════════════════════════════════════════════
    stt_engine = "gemini"
    local_whisper_model = config.get("settings", {}).get("local_whisper_model", "medium")
    assert stt_engine == "gemini", "[POLICY] STT 主力必須為 Gemini 雲端，拒絕執行！"
            
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

    # 共享可變金鑰引用（執行緒間傳遞）
    current_key_ref = [current_key]

    pending_chunks = [c for c in chunks if c["status"] != "completed"]
    logging.info(f"[STT] 共 {len(pending_chunks)} 個 chunk 待處理，並列度 M={CHUNK_CONCURRENCY}")

    # per-task manifest 寫入鎖
    manifest_write_lock = threading.Lock()
    all_succeeded = True  # 修復：預設成功，任何 chunk 失敗時才改為 False
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

    if all_succeeded:
        manifest["status"] = "transcribed"
        manifest["steps"]["stt"] = "completed"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        with open(chunks_manifest_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        logging.info(f"STT Phase completed. Succeeded=True. Triggering Merge Agent...")
        merge_script = os.path.join(script_dir, "merge_transcript.py")
        cmd = [sys.executable, merge_script, "--task-id", task_id]
        subprocess.Popen(cmd, cwd=script_dir)
    else:
        # 失敗：只重置未完成的 chunk 為 pending，已完成的保留，不觸發 merge
        failed_count = 0
        for c in chunks:
            if c["status"] == "failed":
                c["status"] = "pending"
                c["retry_count"] = 0
                failed_count += 1
        manifest["status"] = "chunked"   # 退回佇列，讓 Dispatcher 重派
        manifest["steps"]["stt"] = "pending"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        with open(chunks_manifest_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        logging.warning(
            f"STT Phase partial ({failed_count} chunks 失敗). 重置為 chunked 等待重跑，已完成 chunk 進度保留。"
        )

    return all_succeeded

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stt_runner.py {task_id}")
        sys.exit(1)
    run_stt(sys.argv[1])
