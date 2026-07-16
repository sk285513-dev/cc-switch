import os
import sys
import json
import logging
import yaml
import time
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types

def init_gemini_client(config):
    # Load dotenv from potential paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    potential_dotenv_paths = [
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "..", ".env"),
        os.path.join(script_dir, "..", "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
        "c:\\Users\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\.env"
    ]
    
    for path in potential_dotenv_paths:
        if os.path.exists(path):
            load_dotenv(path)
            
    api_key = os.environ.get(config['gemini']['api_key_env_var'])
    if not api_key:
        # Fallback to direct key check in standard .env path
        raise Exception(f"Gemini API Key not found! Please set the {config['gemini']['api_key_env_var']} environment variable.")
        
    client = genai.Client(api_key=api_key)
    return client

def transcribe_chunk(client, chunk_path, config, chunk_filename):
    model = config['gemini']['model_name']
    
    prompt = """你是一位專業的台灣法律課程與講座的逐字稿整理助理。
請將提供的音檔進行精確的繁體中文語音轉錄，並遵守以下規定：
【重要：完整性與精確性要求】
此檔案為極為關鍵的法律教學教材，是後續所有 AI 專案與智能庫的智慧基礎。請務必做到「一字不漏、完全轉錄」！
嚴禁任何摘要、縮寫、省略、或簡化發言的行為。請完整保留講師的所有口語說明、舉例與課堂細節。
1. 輸出格式一律為繁體中文（台灣習慣用詞）。
2. 保留台灣法律專業術語（例如：不當得利、消滅時效、除斥期間、借名登記、侵權行為、公法上請求權等）。
3. 完整保留所有提到的法律法條名稱與條號，例如「民法第一百八十四條」、「民法第197條」、「民法第126條」、「行政程序法第131條」，若口述簡寫如「民法一八四」請轉錄為完整的「民法第一百八十四條」。
4. 保留釋字字號（例如：釋字第474號）與法院判決字號（例如：最高法院109年度台上字第X號）之標準格式。
5. 聽不清楚或不確定之處不可憑空預測，一律以 [待確認] 標記。
6. 請適度保留時間戳記（例如 [01:23] 或 [15:45]），方便對照原始影音。
7. 當辨識到章節、科目、主題、結論或堂數切換時，請自動插入適當的 Markdown 標題（#、##、###）。
8. 若辨識到「爭點」、「重點整理」、「必考」、「結論」、「實務見解」等關鍵語音字樣，請自動在該段落前加上特殊的 Markdown 加粗重點標記（如：**【爭點】**、**【實務見解】**）。
"""

    logging.info(f"Uploading file {chunk_filename} to Gemini Files API...")
    uploaded_file = client.files.upload(file=chunk_path)
    logging.info(f"File uploaded. Name: {uploaded_file.name}. Starting generation...")
    
    try:
        # Wait a few seconds for processing if it's large (audio files are usually quick)
        time.sleep(2)
        
        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, prompt]
        )
        
        text_result = response.text
        return text_result
    finally:
        # Always delete the uploaded file to clean up cloud storage
        try:
            logging.info(f"Cleaning up cloud file: {uploaded_file.name}")
            client.files.delete(name=uploaded_file.name)
        except Exception as e:
            logging.warning(f"Failed to delete cloud file {uploaded_file.name}: {e}")

def run_stt(task_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    manifests_dir = config['paths']['manifests_dir']
    workflow_log = config['logging']['workflow_log']
    chunk_errors_log = config['logging']['chunk_errors_log']
    
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
        
    chunks = manifest.get('chunks', [])
    if not chunks:
        logging.error(f"No chunks found in manifest for task {task_id}")
        return
        
    try:
        client = init_gemini_client(config)
    except Exception as e:
        logging.error(str(e))
        manifest['status'] = 'failed'
        manifest['error'] = str(e)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        return
        
    all_succeeded = True
    for chunk in chunks:
        if chunk['status'] == 'completed':
            continue
            
        chunk_path = chunk['path']
        chunk_filename = chunk['filename']
        retry_limit = 3
        
        logging.info(f"Processing chunk: {chunk_filename}")
        
        while chunk['retry_count'] < retry_limit:
            try:
                transcription = transcribe_chunk(client, chunk_path, config, chunk_filename)
                
                # Save transcription text
                txt_output_path = chunk_path + ".txt"
                with open(txt_output_path, 'w', encoding='utf-8') as tf:
                    tf.write(transcription)
                    
                # Save transcription JSON
                json_output_path = chunk_path + ".json"
                with open(json_output_path, 'w', encoding='utf-8') as jf:
                    json.dump({
                        "task_id": task_id,
                        "filename": chunk_filename,
                        "part_no": chunk['part_no'],
                        "transcription": transcription,
                        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }, jf, ensure_ascii=False, indent=2)
                    
                chunk['status'] = 'completed'
                logging.info(f"Successfully processed chunk: {chunk_filename}")
                break
            except Exception as e:
                chunk['retry_count'] += 1
                err_msg = f"Error transcribing chunk {chunk_filename} (Attempt {chunk['retry_count']}/{retry_limit}): {e}"
                logging.error(err_msg)
                
                # Write to error log
                with open(chunk_errors_log, 'a', encoding='utf-8') as ef:
                    ef.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [TASK {task_id}] [CHUNK {chunk_filename}]: {e}\n")
                    
                time.sleep(5) # Cooldown before retry
                
        if chunk['status'] != 'completed':
            chunk['status'] = 'failed'
            all_succeeded = False
            
    # Update manifest
    if all_succeeded:
        manifest['status'] = 'transcribed'
        manifest['steps']['stt'] = 'completed'
    else:
        manifest['status'] = 'partial_success'
        manifest['steps']['stt'] = 'failed'
        
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        
    logging.info(f"STT Phase completed. Succeeded={all_succeeded}. Triggering Merge Agent...")
    
    # Trigger Merge Transcript script
    merge_script = os.path.join(script_dir, "merge_transcript.py")
    cmd = [sys.executable, merge_script, task_id]
    subprocess.Popen(cmd, cwd=script_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stt_runner.py {task_id}")
        sys.exit(1)
    run_stt(sys.argv[1])
