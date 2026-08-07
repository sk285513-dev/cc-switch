# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 2: 核心加工管線 (Core Pipeline)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 2】。
# 修改此檔案時，必須確保多執行緒併發 (Concurrency) 及跨進程 JSON 狀態寫入的安全。
# 任何資料輸出格式的變動，都會直接導致 Group 5 (UI) 與 Group 8 (KPI) 癱瘓！
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import os
import sys
import argparse
import json
import subprocess
from pathlib import Path
from workflow_helper import ensure_dirs, log_workflow, log_error, get_ffmpeg_path, get_ffprobe_path
from workflow_helper import ensure_dirs, log_workflow, log_error, get_ffmpeg_path, get_ffprobe_path

def get_safe_env():
    # 【資安修補】安全繼承白名單環境變數，防止子進程外洩敏感金鑰
    whitelist = {"PATH", "SystemRoot", "USERPROFILE", "SystemDrive", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"}
    return {k: v for k, v in os.environ.items() if k in whitelist}

def atomic_write_json(file_path, data):
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as wf:
        json.dump(data, wf, ensure_ascii=False, indent=2)
    os.replace(tmp_path, file_path)
def get_media_info(file_path):
    cmd = [
        get_ffprobe_path(), "-v", "error",
        "-show_format", "-show_streams",
        "-of", "json", file_path
    ]
    # 【資安修補】安全繼承白名單環境變數
    safe_env = get_safe_env()
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore", env=safe_env, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)

def preprocess(task_id):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    chunks_dir = paths["chunks_dir"]
    
    manifest_file = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_file):
        log_error(f"Manifest file not found: {manifest_file}")
        return False
        
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    source_path = manifest["source_path"]
    if not os.path.exists(source_path):
        log_error(f"Source file not found: {source_path}")
        manifest["status"] = "failed"
        manifest["error"] = "Source file missing"
        atomic_write_json(manifest_file, manifest)
        return False

    log_workflow(f"Preprocess Agent: Analyzing media info for {manifest['source_name']}")
    
    try:
        media_info = get_media_info(source_path)
    except Exception as e:
        log_error(f"Failed to read media info for {source_path}: {e}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffprobe error: {e}"
        atomic_write_json(manifest_file, manifest)
        return False

    # 解析影音資訊
    fmt = media_info.get("format", {})
    try:
        if os.environ.get("TEST_MODE_ACCELERATED") == "1":
            duration = min(90.0, float(fmt.get("duration", 0)))
        else:
            duration = float(fmt.get("duration", 0))
    except (ValueError, TypeError):
        duration = 0.0
    bitrate = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else 0
    size_bytes = int(fmt.get("size", 0))
    
    has_video = False
    has_audio = False
    resolution = "N/A"
    audio_codec = "N/A"
    channels = 0
    sample_rate = 0
    
    for stream in media_info.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            has_video = True
            width = stream.get("width")
            height = stream.get("height")
            if width and height:
                resolution = f"{width}x{height}"
        elif codec_type == "audio":
            has_audio = True
            audio_codec = stream.get("codec_name", "N/A")
            channels = int(stream.get("channels", 0)) if stream.get("channels") else 0
            sample_rate = int(stream.get("sample_rate", 0)) if stream.get("sample_rate") else 0

    log_workflow(f"Media Info: Video={has_video} ({resolution}), Audio={has_audio} ({audio_codec}), Duration={duration:.1f}s")
    
    # 建立該任務的切片資料夾
    task_chunks_dir = os.path.join(chunks_dir, task_id)
    os.makedirs(task_chunks_dir, exist_ok=True)
    
    chunk_pattern = os.path.join(task_chunks_dir, "chunk_%03d.wav")
    
    log_workflow(f"Preprocess Agent: Extracting and segmenting audio to {chunk_pattern}")
    if os.environ.get("TEST_MODE_ACCELERATED") == "1":
        ffmpeg_cmd = [
            get_ffmpeg_path(), "-y", "-i", source_path,
            "-t", "90",
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-f", "segment", "-segment_time", "600",
            chunk_pattern
        ]
    else:
        ffmpeg_cmd = [
            get_ffmpeg_path(), "-y", "-i", source_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-f", "segment", "-segment_time", "600",
            chunk_pattern
        ]
    
    try:
        # 【資安修補】安全繼承白名單環境變數
        safe_env = get_safe_env()
        result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore", env=safe_env, timeout=1200)
    except Exception as run_err:
        log_error(f"Failed to run ffmpeg command {ffmpeg_cmd}: {run_err}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffmpeg execution exception: {run_err}"
        atomic_write_json(manifest_file, manifest)
        return False
    if result.returncode != 0:
        log_error(f"ffmpeg extraction failed: {result.stderr}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffmpeg error: {result.stderr}"
        atomic_write_json(manifest_file, manifest)
        return False
        
    import glob
    chunks = []
    chunk_files = sorted(glob.glob(os.path.join(task_chunks_dir, "chunk_*.wav")))
    for idx, cf in enumerate(chunk_files):
        chunks.append({
            "chunk_index": idx,
            "filename": os.path.basename(cf),
            "path": cf,
            "start_time": idx * 600.0,
            "end_time": (idx + 1) * 600.0 if idx < len(chunk_files) - 1 else duration,
            "status": "pending",
            "retry_count": 0
        })
        
    chunks_manifest_file = os.path.join(manifests_dir, f"{task_id}_chunks.json")
    atomic_write_json(chunks_manifest_file, chunks)
        
    manifest["chunks_count"] = len(chunks)

    # 更新 Manifest 資訊
    manifest["media_info"] = {
        "duration_sec": duration,
        "size_bytes": size_bytes,
        "has_video": has_video,
        "has_audio": has_audio,
        "resolution": resolution,
        "audio_codec": audio_codec,
        "audio_channels": channels,
        "audio_sample_rate": sample_rate,
        "extracted_audio_path": chunk_files[0] if chunk_files else ""
    }
    manifest["steps"]["preprocess"] = "completed"
    manifest["status"] = "preprocessed"
    
    atomic_write_json(manifest_file, manifest)
        
    log_workflow(f"Preprocess Agent: Completed task {task_id}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    preprocess(args.task_id)

