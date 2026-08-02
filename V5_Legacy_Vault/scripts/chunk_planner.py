import os
import sys
import argparse
import json
import subprocess
from pathlib import Path
from workflow_helper import ensure_dirs, load_config, log_workflow, log_error, get_ffmpeg_path

def find_silences(wav_path, noise_db=-35, duration=1.5):
    cmd = [
        get_ffmpeg_path(), "-i", wav_path,
        "-af", f"silencedetect=noise={noise_db}dB:d={duration}",
        "-f", "null", "-"
    ]
    # ffmpeg silencedetect logs to stderr
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
        text=True, encoding="utf-8", errors="ignore",
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    )
    silences = []
    for line in result.stderr.split("\n"):
        if "silence_start:" in line:
            parts = line.split("silence_start:")
            if len(parts) > 1:
                try:
                    silences.append(float(parts[1].split()[0]))
                except ValueError:
                    pass
    return sorted(silences)

def seconds_to_str(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m:02d}-{s:02d}"

def plan_chunks(task_id):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    chunks_dir = paths["chunks_dir"]
    
    manifest_file = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_file):
        log_error(f"Manifest not found: {manifest_file}")
        return False
        
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    media_info = manifest.get("media_info", {})
    extracted_audio = media_info.get("extracted_audio_path")
    if not extracted_audio or not os.path.exists(extracted_audio):
        log_error(f"Extracted audio path missing or invalid: {extracted_audio}")
        return False
        
    total_duration = media_info.get("duration_sec", 0)
    has_video = media_info.get("has_video", False)
    
    # 讀取切片時長限制
    config = load_config()
    settings = config.get("settings", {})
    overlap = settings.get("overlap_sec", 30)
    noise_db = settings.get("silence_detect_noise_db", -35)
    silence_duration = settings.get("silence_detect_duration", 1.5)
    
    if has_video:
        limit = settings.get("chunk_limit_video_sec", 360) # 6 mins
    else:
        limit = settings.get("chunk_limit_audio_sec", 360) # 6 mins
        
    log_workflow(f"Chunk Planner: Detecting silences (threshold={noise_db}dB, duration={silence_duration}s)...")
    silences = find_silences(extracted_audio, noise_db, silence_duration)
    log_workflow(f"Detected {len(silences)} silence points.")
    
    chunks_plan = []
    start_time = 0.0
    part_idx = 1
    
    while start_time < total_duration:
        target_end = start_time + limit
        if target_end >= total_duration:
            end_time = total_duration
            chunks_plan.append((start_time, end_time))
            break
            
        # 尋找靠近 target_end 的靜音點，偏好 [target_end - 120, target_end] 區間
        found_cut = None
        for s in reversed(silences):
            if target_end - 120 <= s <= target_end:
                found_cut = s
                break
                
        # 擴大尋找範圍至 [target_end - 240, target_end]
        if found_cut is None:
            for s in reversed(silences):
                if target_end - 240 <= s <= target_end:
                    found_cut = s
                    break
                    
        if found_cut is not None:
            end_time = found_cut
            log_workflow(f"Chunk Planner: Found silence cut point at {end_time:.2f}s for Part {part_idx}")
        else:
            end_time = target_end
            log_workflow(f"Chunk Planner: No silence found near {target_end:.2f}s. Force cutting Part {part_idx}")
            
        chunks_plan.append((start_time, end_time))
        start_time = end_time - overlap
        part_idx += 1
        
    # 執行切片輸出並儲存分片清單
    task_chunks_dir = os.path.join(chunks_dir, task_id)
    os.makedirs(task_chunks_dir, exist_ok=True)
    
    source_stem = Path(manifest["source_name"]).stem
    # 清理檔名，避免特殊字元
    clean_stem = "".join([c if c.isalnum() or c in ('_', '-') else '_' for c in source_stem])
    
    chunks_list = []
    for idx, (s_time, e_time) in enumerate(chunks_plan):
        p_idx = idx + 1
        s_str = seconds_to_str(s_time)
        e_str = seconds_to_str(e_time)
        
        chunk_name = f"chunk_{p_idx:03d}__{s_str}_{e_str}"
        chunk_file_path = os.path.join(task_chunks_dir, f"{chunk_name}.wav")
        
        log_workflow(f"Chunk Planner: Generating chunk {p_idx}/{len(chunks_plan)}: {chunk_name}.wav ({s_time:.1f}s -> {e_time:.1f}s)")
        
        # 使用 ffmpeg 進行切片
        cut_cmd = [
            get_ffmpeg_path(), "-y", "-ss", str(s_time), "-to", str(e_time),
            "-i", extracted_audio, "-c", "copy", chunk_file_path
        ]
        try:
            res = subprocess.run(
                cut_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                text=True, encoding="utf-8", errors="ignore",
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
            )
        except Exception as run_err:
            log_error(f"Failed to run ffmpeg cut command {cut_cmd}: {run_err}")
            manifest["status"] = "failed"
            manifest["error"] = f"ffmpeg execution exception: {run_err}"
            with open(manifest_file, "w", encoding="utf-8") as wf:
                json.dump(manifest, wf, ensure_ascii=False, indent=2)
            return False
        if res.returncode != 0:
            log_error(f"Failed to generate chunk {chunk_name}: {res.stderr}")
            manifest["status"] = "failed"
            manifest["error"] = f"Chunk cut failed: {res.stderr}"
            with open(manifest_file, "w", encoding="utf-8") as wf:
                json.dump(manifest, wf, ensure_ascii=False, indent=2)
            return False
            
        chunks_list.append({
            "chunk_id": f"part_{p_idx:03d}",
            "filename": f"{chunk_name}.wav",
            "start_time": s_time,
            "end_time": e_time,
            "status": "pending",
            "path": chunk_file_path,
            "retry_count": 0
        })
        
    # 儲存 Chunks Manifest
    chunks_manifest_file = os.path.join(manifests_dir, f"{task_id}_chunks.json")
    with open(chunks_manifest_file, "w", encoding="utf-8") as wf:
        json.dump(chunks_list, wf, ensure_ascii=False, indent=2)
        
    # 更新主 Manifest
    manifest["chunks_count"] = len(chunks_plan)
    manifest["steps"]["chunk_planner"] = "completed"
    manifest["status"] = "chunked"
    with open(manifest_file, "w", encoding="utf-8") as wf:
        json.dump(manifest, wf, ensure_ascii=False, indent=2)
        
    log_workflow(f"Chunk Planner: Completed task {task_id}. Planned {len(chunks_plan)} chunks.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    plan_chunks(args.task_id)
