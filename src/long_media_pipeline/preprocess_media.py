import os
import sys
import json
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
import yaml
import subprocess

def run_cmd(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    if result.returncode != 0:
        raise Exception(f"Command failed with code {result.returncode}. Error: {result.stderr}")
    return result.stdout

def preprocess(task_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    manifests_dir = config['paths']['manifests_dir']
    chunks_dir = config['paths']['chunks_dir']
    workflow_log = config['logging']['workflow_log']
    ffmpeg_path = config['ffmpeg']['path']
    ffprobe_path = config['ffmpeg']['ffprobe_path']
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            ConcurrentRotatingFileHandler(workflow_log, mode=\"a\", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        ]
    )
    
    logging.info(f"--- Preprocessing Task {task_id} ---")
    manifest_path = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_path):
        logging.error(f"Manifest not found for task {task_id} at {manifest_path}")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    media_file = manifest['original_file']
    if not os.path.exists(media_file):
        logging.error(f"Media file not found: {media_file}")
        manifest['status'] = 'failed'
        manifest['error'] = 'Original file not found'
        with open(manifest_path, 'w', encoding='utf-8') as wf:
            json.dump(manifest, wf, ensure_ascii=False, indent=2)
        return

    try:
        # Run ffprobe
        probe_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration,bit_rate -show_entries stream=codec_name,codec_type,channels,width,height -of json "{media_file}"'
        probe_output = run_cmd(probe_cmd)
        probe_data = json.loads(probe_output)
        
        streams = probe_data.get('streams', [])
        format_info = probe_data.get('format', {})
        
        has_video = any(s.get('codec_type') == 'video' for s in streams)
        has_audio = any(s.get('codec_type') == 'audio' for s in streams)
        duration = float(format_info.get('duration', 0.0))
        
        resolution = ""
        for s in streams:
            if s.get('codec_type') == 'video':
                w = s.get('width')
                h = s.get('height')
                if w and h:
                    resolution = f"{w}x{h}"
                    break
                    
        audio_channels = 0
        for s in streams:
            if s.get('codec_type') == 'audio':
                audio_channels = int(s.get('channels', 0))
                break
                
        logging.info(f"Media Info: Duration={duration}s, HasVideo={has_video}, HasAudio={has_audio}, Resolution={resolution}, Channels={audio_channels}")
        
        # Determine paths
        task_chunks_dir = os.path.join(chunks_dir, task_id)
        os.makedirs(task_chunks_dir, exist_ok=True)
        extracted_audio_path = os.path.join(task_chunks_dir, "extracted_audio.mp3")
        
        # Extract low bitrate audio for STT
        if has_audio:
            logging.info("Extracting mono low-bitrate audio (16kHz, 32kbps)...")
            extract_cmd = f'"{ffmpeg_path}" -y -i "{media_file}" -vn -acodec libmp3lame -ac 1 -ar 16000 -ab 32k "{extracted_audio_path}"'
            run_cmd(extract_cmd)
            logging.info(f"Extracted audio saved to: {extracted_audio_path}")
        else:
            raise Exception("The media file has no audio streams!")
            
        # Update manifest
        manifest['media_info'] = {
            "duration": duration,
            "has_video": has_video,
            "has_audio": has_audio,
            "resolution": resolution,
            "audio_channels": audio_channels,
            "extracted_audio_path": extracted_audio_path
        }
        manifest['status'] = 'preprocessed'
        manifest['steps']['preprocess'] = 'completed'
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            
        logging.info(f"Preprocessing completed for task {task_id}. Triggering Chunk Planner Agent...")
        
        # Trigger chunk planner script
        chunk_script = os.path.join(script_dir, "chunk_planner.py")
        cmd = [sys.executable, chunk_script, task_id]
        subprocess.Popen(cmd, cwd=script_dir)
        
    except Exception as e:
        logging.error(f"Preprocessing failed for task {task_id}: {e}")
        manifest['status'] = 'failed'
        manifest['steps']['preprocess'] = 'failed'
        manifest['error'] = str(e)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python preprocess_media.py {task_id}")
        sys.exit(1)
    preprocess(sys.argv[1])
