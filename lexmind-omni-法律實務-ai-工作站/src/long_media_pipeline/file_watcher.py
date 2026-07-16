import os
import sys
import time
import hashlib
import json
import logging
import yaml
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up base logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class LongMediaWatcherHandler(FileSystemEventHandler):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.raw_data_dir = config['paths']['raw_data_dir']
        self.manifests_dir = config['paths']['manifests_dir']
        self.workflow_log = config['logging']['workflow_log']
        self.supported_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mp3', '.wav', '.m4a', '.flac']
        
        # Ensure log directories exist
        os.makedirs(os.path.dirname(self.workflow_log), exist_ok=True)
        os.makedirs(self.manifests_dir, exist_ok=True)
        
        # Setup file log handler
        file_handler = logging.FileHandler(self.workflow_log, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logging.getLogger().addHandler(file_handler)
        
        logging.info(f"Watcher initialized. Monitoring folder: {self.raw_data_dir}")

    def on_created(self, event):
        if event.is_directory:
            return
        
        filepath = event.src_path
        filename = os.path.basename(filepath)
        _, ext = os.path.splitext(filename)
        
        if ext.lower() not in self.supported_extensions:
            return
        
        logging.info(f"Detected new media file: {filename}")
        
        # Wait a short duration to ensure file write is complete
        # (For large files, checking file size stability is safer)
        time.sleep(3)
        prev_size = -1
        while True:
            try:
                curr_size = os.path.getsize(filepath)
                if curr_size == prev_size:
                    break
                prev_size = curr_size
                time.sleep(2)
            except Exception as e:
                logging.error(f"Error checking file size for {filename}: {e}")
                return
        
        self.trigger_workflow(filepath, filename)

    def trigger_workflow(self, filepath, filename):
        # Generate task_id
        timestamp = int(time.time())
        hash_input = f"{filename}_{timestamp}".encode('utf-8')
        task_id = hashlib.md5(hash_input).hexdigest()[:12]
        
        logging.info(f"Starting workflow for task_id: {task_id} | File: {filename}")
        
        # Create initial manifest file
        manifest_path = os.path.join(self.manifests_dir, f"{task_id}.json")
        initial_manifest = {
            "task_id": task_id,
            "original_file": filepath,
            "filename": filename,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "steps": {
                "preprocess": "pending",
                "chunk_plan": "pending",
                "stt": "pending",
                "merge": "pending",
                "markdown": "pending"
            }
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(initial_manifest, f, ensure_ascii=False, indent=2)
            
        logging.info(f"Manifest created: {manifest_path}. Triggering Preprocess Agent...")
        
        # Run the preprocess script via subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        preprocess_script = os.path.join(script_dir, "preprocess_media.py")
        
        try:
            # We run it in a subprocess asynchronously to not block the watcher
            cmd = [sys.executable, preprocess_script, task_id]
            subprocess.Popen(cmd, cwd=script_dir)
            logging.info(f"Successfully spawned preprocessing subprocess for task {task_id}")
        except Exception as e:
            logging.error(f"Failed to spawn preprocess script for task {task_id}: {e}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    if not os.path.exists(config_path):
        logging.error(f"Config file not found at {config_path}!")
        sys.exit(1)
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    raw_data_dir = config['paths']['raw_data_dir']
    os.makedirs(raw_data_dir, exist_ok=True)
    
    event_handler = LongMediaWatcherHandler(config)
    observer = Observer()
    observer.schedule(event_handler, raw_data_dir, recursive=False)
    observer.start()
    
    logging.info("Watcher thread started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping watcher...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
