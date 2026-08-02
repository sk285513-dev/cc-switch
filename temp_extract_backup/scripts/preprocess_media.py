import os
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import sys
import argparse
import json
import subprocess
from pathlib import Path
from workflow_helper import ensure_dirs, log_workflow, log_error, get_ffmpeg_path, get_ffprobe_path

def get_media_info(file_path):
    cmd = [
        get_ffprobe_path(), "-v", "error",
        "-show_format", "-show_streams",
        "-of", "json", file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
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
        
    source_path = manifest.get("source_path") or manifest.get("video_path", "")
    if not source_path:
        log_error(f"Manifest missing source_path/video_path: {manifest.get('task_id')}")
        return False
        log_error(f"Source file not found: {source_path}")
        manifest["status"] = "failed"
        manifest["error"] = "Source file missing"
        with open(manifest_file, "w", encoding="utf-8") as wf:
            json.dump(manifest, wf, ensure_ascii=False, indent=2)
        return False

    log_workflow(f"Preprocess Agent: Analyzing media info for {manifest['source_name']}")
    
    try:
        media_info = get_media_info(source_path)
    except Exception as e:
        log_error(f"Failed to read media info for {source_path}: {e}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffprobe error: {e}"
        with open(manifest_file, "w", encoding="utf-8") as wf:
            json.dump(manifest, wf, ensure_ascii=False, indent=2)
        return False

    # 解析影音資訊
    fmt = media_info.get("format", {})
    # For testing and fast execution of large files, limit duration to 90s if TEST_MODE_ACCELERATED is set
    if os.environ.get("TEST_MODE_ACCELERATED") == "1":
        duration = min(90.0, float(fmt.get("duration", 0)))
    else:
        duration = float(fmt.get("duration", 0))
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

    # ══════════════════════════════════════════════════════════════
    # 【長度篩選器】在任何重度 I/O 之前先驗證影片長度
    #   < 180s  (3 min)  → 直接跳過，標記 skipped_short
    #   180-600s (3-10min) → 警告但繼續處理（可能是合法短片段）
    # ══════════════════════════════════════════════════════════════
    MIN_SKIP_SEC  = 180   # 低於此秒數：直接拒絕
    MIN_WARN_SEC  = 600   # 低於此秒數：提醒人工確認

    import json as _json
    _alert_log = "A:/logs/short_video_alerts.jsonl"

    if duration < MIN_SKIP_SEC:
        warn_msg = (
            f"[SHORT-VIDEO SKIP] {source_path} | "
            f"duration={duration:.1f}s ({duration/60:.1f}min) < {MIN_SKIP_SEC}s 門檻 | "
            f"task={task_id} | 已標記 skipped_short，不消耗 STT 配額"
        )
        log_workflow(f"[WARN] ⚠️  {warn_msg}")
        log_error(warn_msg)
        # 寫入告警日誌供人工複查
        try:
            with open(_alert_log, "a", encoding="utf-8") as _af:
                _af.write(_json.dumps({
                    "type": "skipped_short",
                    "task_id": task_id,
                    "source": source_path,
                    "duration_sec": round(duration, 1),
                    "threshold_sec": MIN_SKIP_SEC,
                    "ts": __import__("datetime").datetime.now().isoformat()
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        manifest["status"] = "skipped_short"
        manifest["error"] = f"影片長度 {duration:.1f}s 低於最低門檻 {MIN_SKIP_SEC}s（{MIN_SKIP_SEC//60} 分鐘），已跳過"
        manifest["media_info"] = {"duration_sec": duration}
        with open(manifest_file, "w", encoding="utf-8") as wf:
            _json.dump(manifest, wf, ensure_ascii=False, indent=2)
        return False # 終止，不繼續任何 FFmpeg / STT 處理

    elif duration < MIN_WARN_SEC:
        warn_msg = (
            f"[SHORT-VIDEO WARN] {source_path} | "
            f"duration={duration:.1f}s ({duration/60:.1f}min) < {MIN_WARN_SEC//60}min | "
            f"task={task_id} | 繼續處理但請人工確認是否為有效課程片段"
        )
        log_workflow(f"[WARN] ⚠️  {warn_msg}")
        try:
            with open(_alert_log, "a", encoding="utf-8") as _af:
                _af.write(_json.dumps({
                    "type": "warn_short",
                    "task_id": task_id,
                    "source": source_path,
                    "duration_sec": round(duration, 1),
                    "threshold_sec": MIN_WARN_SEC,
                    "ts": __import__("datetime").datetime.now().isoformat()
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
    # ══════════════════════════════════════════════════════════════
    
    # 建立該任務的切片資料夾
    task_chunks_dir = os.path.join(chunks_dir, task_id)
    os.makedirs(task_chunks_dir, exist_ok=True)
    
    # 抽出/轉換低碼率音軌 16kHz, mono, 16bit PCM WAV
    extracted_audio_path = os.path.join(task_chunks_dir, "extracted_audio.wav")
    
    log_workflow(f"Preprocess Agent: Extracting/converting audio to {extracted_audio_path}")
    if os.environ.get("TEST_MODE_ACCELERATED") == "1":
        ffmpeg_cmd = [
            get_ffmpeg_path(), "-y", "-i", source_path,
            "-t", "90",
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            extracted_audio_path
        ]
    else:
        ffmpeg_cmd = [
            get_ffmpeg_path(), "-y", "-i", source_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            extracted_audio_path
        ]
    
    try:
        result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    except Exception as run_err:
        log_error(f"Failed to run ffmpeg command {ffmpeg_cmd}: {run_err}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffmpeg execution exception: {run_err}"
        with open(manifest_file, "w", encoding="utf-8") as wf:
            json.dump(manifest, wf, ensure_ascii=False, indent=2)
        return False
    if result.returncode != 0:
        log_error(f"ffmpeg extraction failed: {result.stderr}")
        manifest["status"] = "failed"
        manifest["error"] = f"ffmpeg error: {result.stderr}"
        with open(manifest_file, "w", encoding="utf-8") as wf:
            json.dump(manifest, wf, ensure_ascii=False, indent=2)
        return False
        
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
        "extracted_audio_path": extracted_audio_path
    }
    manifest["steps"]["preprocess"] = "completed"
    manifest["status"] = "preprocessed"
    
    with open(manifest_file, "w", encoding="utf-8") as wf:
        json.dump(manifest, wf, ensure_ascii=False, indent=2)
        
    log_workflow(f"Preprocess Agent: Completed task {task_id}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    preprocess(args.task_id)
