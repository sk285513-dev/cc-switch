import os
import sys
import json
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
import yaml
import subprocess
import re
from dotenv import load_dotenv
from google import genai

def init_gemini_client(config):
    # Load dotenv from potential paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    potential_dotenv_paths = [
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "..", ".env"),
        os.path.join(script_dir, "..", "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
        "c:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\.env"
    ]
    
    for path in potential_dotenv_paths:
        if os.path.exists(path):
            load_dotenv(path)
            
    api_key = os.environ.get(config['gemini']['api_key_env_var'])
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def merge_texts_with_overlap(text1, text2, overlap_len=300):
    if not text1:
        return text2
    if not text2:
        return text1
        
    t1_suffix = text1[-overlap_len:] if len(text1) > overlap_len else text1
    t2_prefix = text2[:overlap_len] if len(text2) > overlap_len else text2
    
    # Strip spaces for matching
    t1_norm = re.sub(r'\s+', '', t1_suffix)
    t2_norm = re.sub(r'\s+', '', t2_prefix)
    
    best_match_idx = -1
    best_match_len = 0
    min_match_len = 8
    
    # Simple sliding window search
    for i in range(len(t1_suffix) - min_match_len, -1, -1):
        sub = t1_suffix[i:]
        idx = t2_prefix.find(sub)
        if idx != -1:
            match_len = len(sub)
            if match_len > best_match_len:
                best_match_len = match_len
                best_match_idx = idx
                
    if best_match_idx != -1:
        cut_point = best_match_idx + best_match_len
        return text1 + text2[cut_point:]
    else:
        # Fallback to character normalized sliding window if exact match failed
        for l in range(min(50, len(t1_norm)), min_match_len - 1, -1):
            sub_norm = t1_norm[-l:]
            idx_norm = t2_norm.find(sub_norm)
            if idx_norm != -1:
                # Approximate split point in original text2
                ratio = len(text2) / len(t2_norm) if len(t2_norm) > 0 else 1
                approx_idx = int(idx_norm * ratio)
                approx_len = int(l * ratio)
                return text1 + text2[approx_idx + approx_len:]
                
        return text1 + "\n\n" + text2

def clean_verbal_redundancies(text):
    # Rule-based clean up of common oral redundancies in traditional Chinese
    redundancies = [
        r"那那個", r"那個", r"就是說", r"然後呢", r"所以呢", r"那我們", r"這個", 
        r"這樣的一個", r"呃", r"啊", r"吧", r"對不對", r"這樣子", r"嘿"
    ]
    cleaned = text
    for pattern in redundancies:
        cleaned = re.sub(pattern, "", cleaned)
    # Clean multiple spaces or empty lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned

def generate_chapter_summary(client, full_text, config):
    if not client:
        return "（無法調用 Gemini API 生成章節摘要，請檢查金鑰）"
        
    model = config['gemini']['model_name']
    prompt = """請根據這段台灣法律教學或講座的完整逐字稿，整理出一份章節化摘要。
摘要必須符合以下格式：
1. 提取核心章節大綱（使用 Markdown 標題，如 ## 第一章：不當得利與請求權）。
2. 在每個章節下方，列出：
   - **核心內容簡述**：2-3 句摘要。
   - **涉及法條與釋字**：列出該章節提到之法條條號與大法官解釋字號。
   - **爭點與實務見解**：列出討論的法律爭點與法院實務裁判之核心論述。
3. 繁體中文輸出，語氣專業嚴謹。
"""
    try:
        # If the text is extremely long, take the first 40k characters to prevent model context limits
        truncated_text = full_text[:40000]
        if len(full_text) > 40000:
            truncated_text += "\n\n(後面內容已截斷...)"
            
        response = client.models.generate_content(
            model=model,
            contents=[truncated_text, prompt]
        )
        return response.text
    except Exception as e:
        return f"（生成章節摘要失敗: {e}）"

def merge_workflow(task_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    manifests_dir = config['paths']['manifests_dir']
    workflow_log = config['logging']['workflow_log']
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            ConcurrentRotatingFileHandler(workflow_log, mode=\"a\", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        ]
    )
    
    logging.info(f"--- Merging Transcripts Task {task_id} ---")
    manifest_path = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_path):
        logging.error(f"Manifest not found for task {task_id}")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    chunks = manifest.get('chunks', [])
    if not chunks:
        logging.error("No chunks to merge!")
        return
        
    # Read and merge sequentially
    merged_text = ""
    for chunk in sorted(chunks, key=lambda c: c['part_no']):
        txt_path = chunk['path'] + ".txt"
        if not os.path.exists(txt_path):
            logging.warning(f"Chunk transcript not found: {txt_path}. Skipping.")
            continue
            
        with open(txt_path, 'r', encoding='utf-8') as cf:
            chunk_text = cf.read()
            
        merged_text = merge_texts_with_overlap(merged_text, chunk_text)
        
    # Generate the 3 versions
    # 1. Full Transcript
    full_transcript = merged_text
    
    # 2. Cleaned Transcript
    logging.info("Cleaning redundancies for cleaned version...")
    cleaned_transcript = clean_verbal_redundancies(full_transcript)
    
    # 3. Chapter Summary
    logging.info("Generating chapter summary using Gemini...")
    client = None
    try:
        client = init_gemini_client(config)
    except Exception as e:
        logging.warning(f"Could not initialize Gemini client for summary: {e}")
        
    chapter_summary = generate_chapter_summary(client, full_transcript, config)
    
    # Save files to chunks dir
    task_chunks_dir = os.path.join(config['paths']['chunks_dir'], task_id)
    os.makedirs(task_chunks_dir, exist_ok=True)
    
    full_path = os.path.join(task_chunks_dir, "merged_full.txt")
    cleaned_path = os.path.join(task_chunks_dir, "merged_cleaned.txt")
    summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(full_transcript)
    with open(cleaned_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_transcript)
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(chapter_summary)
        
    logging.info(f"Merged transcripts generated at: {task_chunks_dir}")
    
    # Update manifest
    manifest['merged_paths'] = {
        "full": full_path,
        "cleaned": cleaned_path,
        "summary": summary_path
    }
    manifest['steps']['merge'] = 'completed'
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        
    logging.info(f"Merge completed for task {task_id}. Triggering Markdown Formatter Agent...")
    
    # Trigger markdown formatter script
    formatter_script = os.path.join(script_dir, "markdown_formatter.py")
    cmd = [sys.executable, formatter_script, task_id]
    subprocess.Popen(cmd, cwd=script_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python merge_transcript.py {task_id}")
        sys.exit(1)
    merge_workflow(sys.argv[1])
