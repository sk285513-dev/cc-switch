import os
import yaml
from pathlib import Path

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
                "gemini_model_low_cost": "gemini-2.5-flash",
                "gemini_model_high_accuracy": "gemini-2.5-pro"
            },
            "settings": {
                "low_cost_mode": True,
                "chunk_limit_audio_sec": 1200,
                "chunk_limit_video_sec": 720,
                "overlap_sec": 30,
                "silence_detect_duration": 1.5,
                "silence_detect_noise_db": -35,
                "stt_max_retries": 3
            }
        }
        
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

def get_resolved_paths():
    config = load_config()
    paths = config.get("paths", {})
    root = paths.get("project_root", "D:\\LegalAI_Project")
    
    # If D:\ drive does not exist, fallback to C:\LegalAI_Project
    if root.startswith("D:\\") and not os.path.exists("D:\\"):
        root = root.replace("D:\\", "C:\\")
        
    resolved = {"project_root": root}
    for key in ["raw_data_dir", "processed_md_dir", "manifests_dir", "chunks_dir", "logs_dir"]:
        sub_dir = paths.get(key, "")
        resolved[key] = os.path.join(root, sub_dir)
        
    return resolved

def ensure_dirs():
    paths = get_resolved_paths()
    for key, path in paths.items():
        if key == "project_root":
            continue
        os.makedirs(path, exist_ok=True)
    return paths

def get_all_keys():
    import json
    config = load_config()
    keys = []
    
    # 1. 讀取 config.yaml 中的金鑰列表
    api_section = config.get("api", {})
    if "gemini_api_keys" in api_section and isinstance(api_section["gemini_api_keys"], list):
        for k in api_section["gemini_api_keys"]:
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
        with open(env_path, "r", encoding="utf-8") as f:
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
    import time
    keys = get_all_keys()
    if not keys:
        return ""
    if len(keys) == 1:
        return keys[0]
        
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths["manifests_dir"], "api_keys_state.json")
    
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
            
    # Read config/quota_state.json to sync status
    quota_exhausted = []
    quota_state_file = "config/quota_state.json"
    try:
        if os.path.exists(quota_state_file):
            with open(quota_state_file, "r", encoding="utf-8") as f:
                quota_state = json.load(f)
            quota_exhausted = quota_state.get("exhausted_keys", [])
    except Exception:
        pass

    # 尋找第一個未標記為耗盡，或者已冷卻完畢（超過 10 分鐘）的金鑰
    active_keys = []
    current_time = time.time()
    quota_state_changed = False
    for k in keys:
        k_state = state.get(k, {})
        status = k_state.get("status")
        exhausted_at = k_state.get("exhausted_at", 0)
        
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
            with open(quota_state_file, "w", encoding="utf-8") as f:
                json.dump({"exhausted_keys": quota_exhausted}, f, ensure_ascii=False, indent=2)
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
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
        
    return selected_key

def mark_key_exhausted(key):
    if not key:
        return
    import json
    import time
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths["manifests_dir"], "api_keys_state.json")
    
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
            
    state[key] = {
        "status": "exhausted",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "exhausted_at": time.time()
    }
    
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log_workflow(f"[Key Pool] 成功標記 API Key {key[:8]}...{key[-4:]} 為「暫時耗盡（進入10分鐘冷卻）」。", level="info")
    except Exception as e:
        print(f"Error saving key pool state: {e}")

    # 同步標記到 config/quota_state.json
    try:
        quota_state_file = "config/quota_state.json"
        quota_exhausted = []
        if os.path.exists(quota_state_file):
            with open(quota_state_file, "r", encoding="utf-8") as f:
                quota_state = json.load(f)
            quota_exhausted = quota_state.get("exhausted_keys", [])
        if key not in quota_exhausted:
            quota_exhausted.append(key)
            with open(quota_state_file, "w", encoding="utf-8") as f:
                json.dump({"exhausted_keys": quota_exhausted}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def reset_exhausted_keys():
    resolved_paths = get_resolved_paths()
    state_file = os.path.join(resolved_paths["manifests_dir"], "api_keys_state.json")
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
            log_workflow("[Key Pool] 成功重置金鑰池中所有金鑰之狀態。", level="info")
        except Exception as e:
            print(f"Error resetting key pool state: {e}")

    try:
        quota_state_file = "config/quota_state.json"
        if os.path.exists(quota_state_file):
            with open(quota_state_file, "w", encoding="utf-8") as f:
                json.dump({"exhausted_keys": []}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def log_workflow(message, level="info"):
    paths = ensure_dirs()
    log_file = os.path.join(paths["logs_dir"], "workflow.log")
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level.upper()}] {message}\n"
    print(log_line.strip())
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

def log_error(message):
    paths = ensure_dirs()
    log_file = os.path.join(paths["logs_dir"], "chunk_errors.log")
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [ERROR] {message}\n"
    print(log_line.strip())
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)
    
    # Also log to main workflow log
    log_workflow(message, level="error")

def get_ffmpeg_path():
    import shutil
    p = shutil.which("ffmpeg")
    if p:
        return p
    winget_paths = [
        r"C:\Users\temp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe",
        r"C:\Program Files (x85)\iMyFone\iMyFone D-Back\ffmpeg.exe",
        r"C:\Program Files (x86)\iMyFone\iMyFone D-Back\ffmpeg.exe"
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
