import os
import sys
import json
import logging
import yaml
import subprocess

def run_cmd(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    if result.returncode != 0:
        raise Exception(f"Command failed. Error: {result.stderr}")
    return result.stdout

def detect_silence(ffmpeg_path, audio_path, noise=-30, duration=1.5):
    # Runs ffmpeg silencedetect and returns a list of silence intervals
    cmd = f'"{ffmpeg_path}" -i "{audio_path}" -af silencedetect=noise={noise}dB:d={duration} -f null -'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    
    silences = []
    current_start = None
    
    for line in result.stderr.splitlines():
        if "silence_start:" in line:
            parts = line.split("silence_start:")
            try:
                current_start = float(parts[1].strip().split()[0])
            except:
                pass
        elif "silence_end:" in line:
            parts = line.split("silence_end:")
            try:
                end_val = float(parts[1].strip().split()[0])
                if current_start is not None:
                    silences.append({
                        "start": current_start,
                        "end": end_val,
                        "duration": end_val - current_start
                    })
                    current_start = None
            except:
                pass
    return silences

def format_time_str(seconds):
    # Convert seconds to mm-ss string
    total_sec = int(round(seconds))
    m = total_sec // 60
    s = total_sec % 60
    return f"{m:02d}-{s:02d}"

def plan_and_cut(task_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    manifests_dir = config['paths']['manifests_dir']
    chunks_dir = config['paths']['chunks_dir']
    workflow_log = config['logging']['workflow_log']
    ffmpeg_path = config['ffmpeg']['path']
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(workflow_log, encoding='utf-8')
        ]
    )
    
    logging.info(f"--- Chunk Planning Task {task_id} ---")
    manifest_path = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_path):
        logging.error(f"Manifest not found for task {task_id}")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    media_info = manifest.get('media_info', {})
    total_duration = media_info.get('duration', 0.0)
    has_video = media_info.get('has_video', False)
    extracted_audio = media_info.get('extracted_audio_path')
    
    if not extracted_audio or not os.path.exists(extracted_audio):
        logging.error(f"Extracted audio path not found in manifest or file missing!")
        return
        
    # Read chunking params
    overlap = config['chunking']['overlap_seconds']
    silence_cfg = config['chunking']['silence_detect']
    
    if has_video:
        max_chunk_len = config['chunking']['video_max_duration_seconds']
    else:
        max_chunk_len = config['chunking']['audio_max_duration_seconds']
        
    logging.info(f"Detecting silence intervals using noise={silence_cfg['noise_db']}dB, duration={silence_cfg['duration_seconds']}s...")
    silences = detect_silence(ffmpeg_path, extracted_audio, silence_cfg['noise_db'], silence_cfg['duration_seconds'])
    logging.info(f"Found {len(silences)} silence points.")
    
    # Run planning algorithm
    chunks_planned = []
    start = 0.0
    part_no = 1
    
    # Clean the source filename for naming chunk files
    base_source_name = os.path.splitext(manifest['filename'])[0]
    # Replace spaces and special characters
    safe_base_name = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in base_source_name])
    
    task_chunks_dir = os.path.join(chunks_dir, task_id)
    os.makedirs(task_chunks_dir, exist_ok=True)
    
    while start < total_duration:
        target_end = start + max_chunk_len
        if target_end >= total_duration:
            chunks_planned.append((start, total_duration, part_no))
            break
            
        # Search window for silence [target_end - 60s, target_end]
        window_start = target_end - 60
        window_end = target_end
        
        valid_silences = [s for s in silences if s['start'] >= window_start and s['start'] <= window_end]
        
        if valid_silences:
            # Sort by proximity to target_end
            valid_silences.sort(key=lambda s: abs(s['start'] - target_end))
            # Split at the midpoint of the silence duration
            best_silence = valid_silences[0]
            split_point = best_silence['start'] + (best_silence['duration'] / 2.0)
        else:
            split_point = target_end
            
        chunks_planned.append((start, split_point, part_no))
        
        # Advance with overlap
        start = split_point - overlap
        part_no += 1
        
    # Cut chunks using ffmpeg
    chunks_records = []
    for c_start, c_end, p_no in chunks_planned:
        duration_to_cut = c_end - c_start
        start_str = format_time_str(c_start)
        end_str = format_time_str(c_end)
        
        chunk_filename = f"{safe_base_name}__part_{p_no:03d}__{start_str}_{end_str}.mp3"
        chunk_path = os.path.join(task_chunks_dir, chunk_filename)
        
        logging.info(f"Cutting chunk {p_no:03d} (Duration={duration_to_cut:.2f}s, Interval={start_str} to {end_str})...")
        
        # Cut audio segment
        cut_cmd = f'"{ffmpeg_path}" -y -ss {c_start} -i "{extracted_audio}" -to {duration_to_cut} -c copy "{chunk_path}"'
        run_cmd(cut_cmd)
        
        chunks_records.append({
            "part_no": p_no,
            "start_time": c_start,
            "end_time": c_end,
            "filename": chunk_filename,
            "path": chunk_path,
            "status": "pending",
            "retry_count": 0
        })
        
    # Save back to manifest
    manifest['chunks'] = chunks_records
    manifest['status'] = 'chunked'
    manifest['steps']['chunk_plan'] = 'completed'
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        
    logging.info(f"Chunking completed for task {task_id}. Total chunks generated: {len(chunks_records)}. Triggering STT Runner Agent...")
    
    # Trigger STT runner script
    stt_script = os.path.join(script_dir, "stt_runner.py")
    cmd = [sys.executable, stt_script, task_id]
    subprocess.Popen(cmd, cwd=script_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chunk_planner.py {task_id}")
        sys.exit(1)
    plan_and_cut(sys.argv[1])
