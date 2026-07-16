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

def get_gemini_key():
    config = load_config()
    key = config.get("api", {}).get("gemini_api_key", "AUTO_LOAD_FROM_ENV")
    if key == "AUTO_LOAD_FROM_ENV" or not key:
        script_dir = Path(__file__).parent.resolve()
        workspace_root = script_dir.parent
        env_path = workspace_root / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip()
        # Fallback to os.environ
        return os.environ.get("GEMINI_API_KEY", "")
    return key

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
