# [CRITICAL CROSS-FILE DEPENDENCY WARNING]
# Upstream: run_workflow.py, stt_runner.py, merge_transcript.py, markdown_formatter.py
# Shared State: config.yaml, api_keys_state.json, config/quota_state.json, logs
#
# [LexMind V6 Ironclad Compliance]
# - Rule 3 : 本檔案以 UTF-8-SIG 儲存
# - Rule 4 : 所有讀檔一律 errors="replace"
# - Rule 5 : 字典取值一律使用 .get()
# - Rule 7 : 不在 import 階段執行 sys.stdout.reconfigure（WinError 10106 防護）
# - Rule 11: 所有 JSON 寫入 ensure_ascii=True
# - Rule 12: log_error 將多行 Exception Block 合併為單行後一次寫入

import os
import sys
import time
import random
import threading
import yaml
from pathlib import Path

_io_write_lock = threading.Lock()


def safe_reconfigure_stdio():
    """
    [Rule 7] 只允許由「主入口」明確呼叫，不得於 import 階段執行。
    pythonw.exe 之下 sys.stdout / sys.stderr 可能為 None，直接呼叫會崩潰。
    """
    for stream_name in ("stdout", "stderr"):
        try:
            stream = getattr(sys, stream_name, None)
            if stream is None:
                continue
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _safe_print(text):
    """pythonw.exe 之下 stdout 可能為 None；print 失敗不得拖垮工作流。"""
    try:
        if getattr(sys, "stdout", None) is not None:
            print(text)
    except Exception:
        pass


def atomic_json_dump(data, filepath):
    """
    [Rule 11] ensure_ascii=True（禁止編碼炸彈）
    純淨 utf-8（無 BOM，黃金基準步驟四）+ flush + fsync + os.replace 原子替換
    PermissionError 指數退避 + 隨機抖動重試（Windows Defender / 索引服務防護）
    """
    import json
    filepath = str(filepath)
    tmp_path = f"{filepath}.{os.getpid()}.{threading.get_ident()}.tmp"
    replaced = False
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=True, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass

        max_retries = 30
        for i in range(max_retries):
            try:
                os.replace(tmp_path, filepath)
                replaced = True
                return
            except PermissionError:
                if i == max_retries - 1:
                    raise
                sleep_time = (0.1 * (1.2 ** i)) + random.uniform(0.01, 0.05)
                time.sleep(min(sleep_time, 2.0))
    finally:
        # [V3] .tmp 檔案清道夫：任何失敗路徑都不得留下殘骸
        if not replaced and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _safe_json_load(filepath, default=None):
    """[Rule 4] 讀檔加 errors='replace'，解析失敗回傳 default，不拋例外。"""
    import json
    try:
        if not os.path.exists(filepath):
            return default
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            return json.load(f)
    except Exception:
        return default


def load_config():
    # Load config.yaml from workspace root
    script_dir = Path(__file__).parent.resolve()
    workspace_root = script_dir.parent
    config_path = workspace_root / "config.yaml"

    if not config_path.exists():
        config_path = script_dir / "config.yaml"

    if not config_path.exists():
        # Fallback to current working directory
        config_path = Path("config.yaml").resolve()

    if not config_path.exists():
        # Create a default dict if config file is not found
        return {
            "paths": {
                "project_root": "D:\\LegalAI_Project",
                "raw_data_dir": "raw_data",
                "processed_md_dir": "processed_md",
                "manifests_dir": "manifests",
                "chunks_dir": "chunks",
                "logs_dir": "logs"
            },
            "api": {
                "gemini_api_key": "AUTO_LOAD_FROM_ENV",
                "gemini_model_low_cost": "gemini-3.5-flash",
                "gemini_model_high_accuracy": "gemini-flash-latest",
            },
            "settings": {
                "low_cost_mode": True,
                "chunk_limit_audio_sec": 1200,
                "chunk_limit_video_sec": 360,
                "overlap_sec": 30,
                "silence_detect_duration": 1.5,
                "silence_detect_noise_db": -35,
                "stt_max_retries": 3
            }
        }

    try:
        with open(config_path, "r", encoding="utf-8-sig", errors="replace") as f:
            config = yaml.safe_load(f)
    except Exception:
        config = None
    return config if isinstance(config, dict) else {}


def get_engine_setting(config, key, default=None):
    """
    [統一配置讀取層] 消除 config.get("settings", {}).get(...) 與
    config.get(...) 混用造成的引擎誤判（例如 Vertex 被誤認為 Gemini）。
    查找順序：settings -> api -> 頂層 -> default
    """
    if not isinstance(config, dict):
        return default
    settings = config.get("settings", {}) or {}
    if isinstance(settings, dict) and key in settings and settings.get(key) is not None:
        return settings.get(key)
    api_section = config.get("api", {}) or {}
    if isinstance(api_section, dict) and key in api_section and api_section.get(key) is not None:
        return api_section.get(key)
    if key in config and config.get(key) is not None:
        return config.get(key)
    return default


def get_resolved_paths():
    config = load_config()
    paths = config.get("paths", {}) or {}
    root = paths.get("project_root", "D:\\LegalAI_Project")

    # If D:\ drive does not exist, fallback to C:\LegalAI_Project
    if root.startswith("D:\\") and not os.path.exists("D:\\"):
        root = root.replace("D:\\", "C:\\")

    v6_env = os.environ.get("LEXMIND_ENV", "v5_prod")
    suffix = "_v6" if v6_env == "v6_canary" else ""

    resolved = {"project_root": root}
    for key in ["raw_data_dir", "processed_md_dir", "manifests_dir", "chunks_dir", "logs_dir"]:
        sub_dir = paths.get(key, "")
        base_path = os.path.join(root, sub_dir)
        resolved[key] = base_path + suffix if suffix else base_path

    return resolved


def ensure_dirs():
    paths = get_resolved_paths()
    for key, path in paths.items():
        if key == "project_root":
            continue
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
    return paths


def get_all_keys():
    config = load_config()
    keys = []

    # 1. 讀取 config.yaml 中的金鑰列表
    api_section = config.get("api", {}) or {}
    key_list = api_section.get("gemini_api_keys")
    if isinstance(key_list, list):
        for k in key_list:
            if k and isinstance(k, str):
                keys.append(k.strip())

    # 2. 讀取 config.yaml 中的單一金鑰
    single_key = api_section.get("gemini_api_key")
    if single_key and single_key != "AUTO_LOAD_FROM_ENV" and single_key not in keys:
        keys.append(single_key.strip())

    # 3. 讀取 .env
    script_dir = Path(__file__).parent.resolve()
    workspace_root = script_dir.parent
    env_path = workspace_root / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str.startswith("GEMINI_API_KEYS="):
                        val = line_str.split("=", 1)[1].strip()
                        for k in val.split(","):
                            k_clean = k.strip()
                            if k_clean and k_clean not in keys:
                                keys.append(k_clean)
                    elif line_str.startswith("GEMINI_API_KEY="):
                        val = line_str.split("=", 1)[1].strip()
                        if val and val not in keys:
                            keys.append(val)
        except Exception:
            pass

    # 4. 讀取環境變數
    env_keys_str = os.environ.get("GEMINI_API_KEYS")
    if env_keys_str:
        for k in env_keys_str.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in keys:
                keys.append(k_clean)
    env_single = os.environ.get("GEMINI_API_KEY")
    if env_single and env_single not in keys:
        keys.append(env_single)

    return [k for k in keys if k]


def get_gemini_key():
    import json
    keys = get_all_keys()
    if not keys:
        return ""
    if len(keys) == 1:
        return keys[0]

    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths.get("manifests_dir", "."), "api_keys_state.json")

    state = _safe_json_load(state_file, default={}) or {}
    if not isinstance(state, dict):
        state = {}

    # Read config/quota_state.json to sync status
    quota_state_file = "config/quota_state.json"
    quota_state = _safe_json_load(quota_state_file, default={}) or {}
    if not isinstance(quota_state, dict):
        quota_state = {}
    quota_exhausted = quota_state.get("exhausted_keys", []) or []

    # 尋找第一個未標記為耗盡，或者已冷卻完畢（超過 10 分鐘）的金鑰
    active_keys = []
    current_time = time.time()
    quota_state_changed = False
    for k in keys:
        k_state = state.get(k, {}) or {}
        status = k_state.get("status")
        exhausted_at = k_state.get("exhausted_at", 0) or 0

        # 10 分鐘自動解禁
        if status == "exhausted" and (current_time - exhausted_at > 600):
            status = "active"
            if k in quota_exhausted:
                quota_exhausted.remove(k)
                quota_state_changed = True

        if status != "exhausted" and k not in quota_exhausted:
            active_keys.append(k)

    if quota_state_changed:
        try:
            atomic_json_dump({"exhausted_keys": quota_exhausted}, quota_state_file)
        except Exception:
            pass

    if not active_keys:
        # 如果全部金鑰都耗盡了，安全起見自動重設狀態檔案，重新循環嘗試
        log_workflow("[Key Pool] 金鑰池內所有金鑰皆已標記為耗盡。正在重設狀態重新循環...", level="warning")
        reset_exhausted_keys()
        return keys[0]

    # 實作 Round-Robin 輪詢：尋找 last_used_key，並挑選它的下一個金鑰
    last_key = state.get("last_used_key")
    next_index = 0
    if last_key in active_keys:
        try:
            next_index = (active_keys.index(last_key) + 1) % len(active_keys)
        except ValueError:
            next_index = 0

    selected_key = active_keys[next_index]

    # 記錄最後使用的金鑰
    state["last_used_key"] = selected_key
    try:
        atomic_json_dump(state, state_file)
    except Exception:
        pass

    return selected_key


def mark_key_exhausted(key):
    if not key:
        return
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths.get("manifests_dir", "."), "api_keys_state.json")

    state = _safe_json_load(state_file, default={}) or {}
    if not isinstance(state, dict):
        state = {}

    state[key] = {
        "status": "exhausted",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "exhausted_at": time.time()
    }

    try:
        atomic_json_dump(state, state_file)
        log_workflow(
            f"[Key Pool] 成功標記 API Key {key[:8]}...{key[-4:]} 為「暫時耗盡（進入10分鐘冷卻）」。",
            level="info"
        )
    except Exception as e:
        _safe_print(f"Error saving key pool state: {e}")

    # 同步標記到 config/quota_state.json
    try:
        quota_state_file = "config/quota_state.json"
        quota_state = _safe_json_load(quota_state_file, default={}) or {}
        if not isinstance(quota_state, dict):
            quota_state = {}
        quota_exhausted = quota_state.get("exhausted_keys", []) or []
        if key not in quota_exhausted:
            quota_exhausted.append(key)
            atomic_json_dump({"exhausted_keys": quota_exhausted}, quota_state_file)
    except Exception:
        pass


def reset_exhausted_keys():
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths.get("manifests_dir", "."), "api_keys_state.json")
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
            log_workflow("[Key Pool] 成功重置金鑰池中所有金鑰之狀態。", level="info")
        except Exception as e:
            _safe_print(f"Error resetting key pool state: {e}")

    try:
        quota_state_file = "config/quota_state.json"
        if os.path.exists(quota_state_file):
            atomic_json_dump({"exhausted_keys": []}, quota_state_file)
    except Exception:
        pass


def log_workflow(message, level="info"):
    """
    [Rule 1/2] 訊息不得包含 Emoji，終端提示僅限純 ASCII 符號 + 中文。
    [Rule 12] 多行訊息合併為單行寫入，避免 Traceback 被切割。
    """
    paths = ensure_dirs()
    log_file = os.path.join(paths.get("logs_dir", "."), "workflow.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    flat_message = str(message).replace("\r\n", " | ").replace("\n", " | ")
    log_line = f"[{timestamp}] [{level.upper()}] {flat_message}\n"
    _safe_print(log_line.strip())
    try:
        with _io_write_lock:
            with open(log_file, "a", encoding="utf-8", errors="replace") as f:
                f.write(log_line)
    except Exception:
        pass


def log_error(message):
    """
    [Rule 12] Exception Block 先合併為單行再一次寫入（Buffer 機制）。
    """
    paths = ensure_dirs()
    log_file = os.path.join(paths.get("logs_dir", "."), "chunk_errors.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    flat_message = str(message).replace("\r\n", " | ").replace("\n", " | ")
    log_line = f"[{timestamp}] [ERROR] {flat_message}\n"
    _safe_print(log_line.strip())
    try:
        with _io_write_lock:
            with open(log_file, "a", encoding="utf-8", errors="replace") as f:
                f.write(log_line)
    except Exception:
        pass

    # Also log to main workflow log
    log_workflow(flat_message, level="error")


def log_stage(task_id, stage, direction, ok=None, elapsed=None, extra=None):
    """
    [架構斷點系統] 統一格式的工作流階段 IN/OUT 斷點。

    設計初衷：每個生產流階段（preprocess / chunk_planner / stt / merge / formatter）
    進入與離開都留下一條單行、純 ASCII 鍵值、機器可查的紀錄：
      [STAGE] dir=IN  task=task_xxx stage=stt
      [STAGE] dir=OUT task=task_xxx stage=stt ok=1 elapsed=123.4s

    偵錯鐵律：任何卡住的任務 = 「最後一條 dir=IN 且沒有對應 dir=OUT」，
    直接指出卡在哪個階段（配合 extra 可精確到哪一個 chunk）。

    同時寫入：
      1. workflow.log（經 log_workflow，便於主日誌串讀）
      2. logs_dir/stage_trace.log（專用斷點檔，查詢面最小）
    """
    parts = ["[STAGE]", f"dir={direction}", f"task={task_id}", f"stage={stage}"]
    if ok is not None:
        parts.append(f"ok={1 if ok else 0}")
    if elapsed is not None:
        try:
            parts.append(f"elapsed={float(elapsed):.1f}s")
        except (TypeError, ValueError):
            pass
    if isinstance(extra, dict):
        for k, v in extra.items():
            flat_v = str(v).replace("\r\n", " ").replace("\n", " ").replace(" ", "_")[:120]
            parts.append(f"{k}={flat_v}")
    message = " ".join(parts)

    # 1. 主日誌
    log_workflow(message, level="info")

    # 2. 專用斷點檔（單行、可 grep、可 tail）
    try:
        paths = ensure_dirs()
        trace_file = os.path.join(paths.get("logs_dir", "."), "stage_trace.log")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with _io_write_lock:
            with open(trace_file, "a", encoding="utf-8", errors="replace") as f:
                f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def get_ffmpeg_path():
    import shutil
    p = shutil.which("ffmpeg")
    if p:
        return p
    winget_paths = [
        r"C:\Users\temp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\iMyFone\iMyFone D-Back\ffmpeg.exe",
    ]
    for wp in winget_paths:
        if os.path.exists(wp):
            return wp
    return "ffmpeg"


def get_ffprobe_path():
    import shutil
    p = shutil.which("ffprobe")
    if p:
        return p
    winget_paths = [
        r"C:\Users\temp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.exe"
    ]
    for wp in winget_paths:
        if os.path.exists(wp):
            return wp
    return "ffprobe"
