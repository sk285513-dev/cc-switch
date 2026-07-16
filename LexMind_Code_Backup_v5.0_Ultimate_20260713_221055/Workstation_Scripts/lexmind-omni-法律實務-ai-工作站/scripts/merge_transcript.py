import os
import sys
import argparse
import json
import difflib
import requests
from pathlib import Path
from workflow_helper import ensure_dirs, load_config, get_gemini_key, log_workflow, log_error

PROMPT_CLEAN = """你是一個法學專業的文字編輯，請幫我將以下法律教材逐字稿進行「去冗餘與語氣詞修剪」，以利後續閱讀與檢索：
1. 刪除多餘的口頭禪與無意義語氣詞（例如：「那」、「然後」、「就是說」、「呃」、「阿」、「那那個」等）。
2. 修復語氣中斷與錯別字，使語句流暢通順，並將斷開的句子拼合。
3. ⚠️ 嚴格保留所有法律實務術語、法條名稱、條號、以及司法裁判字號，不可刪除或修改任何實質法律內容！
4. 請保持原本的段落結構與時間軸，只修飾文字流暢度。
5. 只輸出修飾後的繁體中文文本，不要有任何引言或解釋。

逐字稿內容：
{text}"""

PROMPT_SUMMARY = """你是一個臺灣法律專家，請分析以下教材逐字稿，提煉出結構化的「章節化大綱與爭點摘要」以利未來的 RAG 檢索：
1. 【核心爭點與法律概念】：列出本段教材講授或辯論的核心爭議點。
2. 【推理路徑與法理】：列出主要的論證邏輯與推理過程。
3. 【結論與實務見解】：列出結論，並整理文中涉及的所有重要法規條文（如民法第184條）、大法官釋字、最高法院判決字號。
4. 【章節大綱】：依據邏輯結構或時間軸，以 Markdown 的標題與條列式大綱呈現。

逐字稿內容：
{text}"""

def merge_overlap_char(text1, text2):
    chars1 = list(text1)
    chars2 = list(text2)
    
    if not chars1: return text2
    if not chars2: return text1
    
    # 擷取 text1 的尾端與 text2 的前端進行匹配 (各取最多 400 個字)
    suffix_len = min(400, len(chars1))
    suffix = chars1[-suffix_len:]
    
    prefix_len = min(400, len(chars2))
    prefix = chars2[:prefix_len]
    
    matcher = difflib.SequenceMatcher(None, suffix, prefix)
    match = matcher.find_longest_match(0, suffix_len, 0, prefix_len)
    
    # 若有超過 12 個連續字元匹配成功，則在此處拼接
    if match.size >= 12:
        cut_idx1 = len(chars1) - suffix_len + match.a
        part1 = "".join(chars1[:cut_idx1])
        part2 = "".join(chars2[match.b:])
        return part1 + part2
    else:
        # 找不到重疊匹配時，退回直接拼接
        return text1 + "\n\n" + text2

def call_gemini_api(prompt, model_name, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    response = requests.post(url, json=payload, timeout=300)
    if response.status_code != 200:
        raise RuntimeError(f"Gemini API error (HTTP {response.status_code}): {response.text}")
    res_data = response.json()
    try:
        return res_data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError("Invalid Gemini API response format")

def merge_workflow(task_id):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    chunks_dir = paths["chunks_dir"]
    task_chunks_dir = os.path.join(chunks_dir, task_id)
    
    manifest_file = os.path.join(manifests_dir, f"{task_id}.json")
    chunks_manifest_file = os.path.join(manifests_dir, f"{task_id}_chunks.json")
    
    if not os.path.exists(manifest_file) or not os.path.exists(chunks_manifest_file):
        log_error(f"Manifest or chunks manifest missing for {task_id}")
        return False
        
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(chunks_manifest_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    log_workflow(f"Merge Agent: Reading and concatenating {len(chunks)} chunks...")
    
    # 1. 逐一合併分片文字
    merged_text = ""
    for chunk in chunks:
        chunk_path = chunk["path"]
        stem = Path(chunk_path).stem
        chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
        
        if not os.path.exists(chunk_txt_file):
            log_error(f"Merge Agent: Chunk text file missing: {chunk_txt_file}")
            # 如果是 partial_success，我們依然繼續合併現有分片
            continue
            
        with open(chunk_txt_file, "r", encoding="utf-8") as rf:
            chunk_content = rf.read().strip()
            
        if not merged_text:
            merged_text = chunk_content
        else:
            merged_text = merge_overlap_char(merged_text, chunk_content)
            
    # 輸出版本 1：完整合併逐字稿
    out_full_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
    with open(out_full_path, "w", encoding="utf-8") as wf:
        wf.write(merged_text)
    log_workflow(f"Merge Agent: Saved full merged transcript to {out_full_path}")
    
    # 準備呼叫 Gemini 進行整理與摘要
    config = load_config()
    low_cost = config.get("settings", {}).get("low_cost_mode", True)
    model_name = config.get("api", {}).get("gemini_model_low_cost", "gemini-2.5-flash")
    if not low_cost:
        model_name = config.get("api", {}).get("gemini_model_high_accuracy", "gemini-2.5-pro")
        
    api_key = get_gemini_key()
    if not api_key:
        log_error("Merge Agent: Gemini API Key missing, skipping AI cleanup and summary.")
        manifest["steps"]["merge"] = "partial_success"
        manifest["status"] = "merged"
        with open(manifest_file, "w", encoding="utf-8") as wf:
            json.dump(manifest, wf, ensure_ascii=False, indent=2)
        return True

    # 支援最大 4 小時超長影音 (不進行小字數截斷，保留完整逐字稿)
    truncated_text = merged_text if len(merged_text) < 1000000 else merged_text[:1000000] + "\n\n... (字數已達百萬限制截斷) ..."

    # 輸出版本 2：去冗餘整理版本
    log_workflow("Merge Agent: Running AI transcript cleanup...")
    try:
        cleaned_text = call_gemini_api(PROMPT_CLEAN.format(text=truncated_text), model_name, api_key)
        out_cleaned_path = os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt")
        with open(out_cleaned_path, "w", encoding="utf-8") as wf:
            wf.write(cleaned_text)
        log_workflow(f"Merge Agent: Saved cleaned transcript to {out_cleaned_path}")
    except Exception as e:
        log_error(f"Merge Agent: AI cleanup failed: {e}")
        cleaned_text = merged_text # fallback
        
    # 輸出版本 3：章節化摘要版本
    log_workflow("Merge Agent: Running AI chaptered summary extraction...")
    try:
        summary_text = call_gemini_api(PROMPT_SUMMARY.format(text=truncated_text), model_name, api_key)
        out_summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
        with open(out_summary_path, "w", encoding="utf-8") as wf:
            wf.write(summary_text)
        log_workflow(f"Merge Agent: Saved chaptered summary to {out_summary_path}")
    except Exception as e:
        log_error(f"Merge Agent: AI summary failed: {e}")
        summary_text = "（摘要生成失敗）"
        
    # 更新任務 Manifest
    manifest["steps"]["merge"] = "completed"
    manifest["status"] = "merged"
    manifest["paths"] = {
        "merged_full_transcript": out_full_path,
        "merged_cleaned_transcript": os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt") if 'out_cleaned_path' in locals() else out_full_path,
        "merged_summary": os.path.join(task_chunks_dir, "merged_summary.txt") if 'out_summary_path' in locals() else ""
    }
    
    with open(manifest_file, "w", encoding="utf-8") as wf:
        json.dump(manifest, wf, ensure_ascii=False, indent=2)
        
    log_workflow(f"Merge Agent: Completed merge workflow for {task_id}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    merge_workflow(args.task_id)
