import os
import sys
import argparse
import json
import difflib
import requests
import httpx
import re
import time
from pathlib import Path
from workflow_helper import ensure_dirs, load_config, log_workflow, log_error
from quota_manager import QuotaManager
from google import genai
import google.auth
from google.api_core import exceptions as google_exceptions
import concurrent.futures

def _call_with_timeout(func, timeout_sec, *args, **kwargs):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout_sec)
    except concurrent.futures.TimeoutError:
        print(f"[Timeout] Merge API call stuck for {timeout_sec}s, forcing exit.")
        executor.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError("Vertex API Deadlock Timeout in Merge")
    finally:
        executor.shutdown(wait=False)

PROMPT_GAP_REFINE = """你是一個法學專業的文字編輯，請幫我將以下法律教材「分片銜接處」的上下文進行語意精校與拼接修剪：
1. 修正同音錯字（如將「投地」修正為「土地」）。
2. 修復銜接點左右的語意中斷與重複字句，使兩端句子流暢、自然地拼合在一起。
3. 嚴格保留所有實質法律內容，不要加入任何引言、解釋或額外說明。
4. 輸出修飾後的流暢銜接段落即可。

待精校銜接處內容：
{text}"""

PROMPT_CLEAN = """你是一個法學專業的文字編輯，請幫我將以下法律教材逐字稿進行「去冗餘與語氣詞修剪」，以利後續閱讀與檢索：
1. 刪除多餘的口頭禪與無意義語氣詞（例如：「那」、「然後」、「就是說」、「呃」、「阿」、「那那個」等）。
2. 修復語氣中斷與同音錯別字，使語句流暢通順，並將斷開的句子拼合。
3. ⚠️ 修正常見的台灣法律口述同音錯字（例如：「投地登記」應修復為「土地登記」、「主登」應修復為「土登」、「各輪」或「課論」應修復為「各論」、「醫生師」或「地政師」應修復為「地政士」、「共耳」應修復為「共有人」、「優購權」或「又過去」應修復為「優先購買權」）。
4. ⚠️ 嚴格保留所有法律實務術語、法條名稱、條號、以及司法裁判字號，不可刪除或修改任何實質法律內容！
5. 請保持原本的段落結構與時間軸，只修飾文字流暢度。
6. 只輸出修飾後的繁體中文文本，不要有任何引言或解釋。

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

def apply_glossary_fix(text):
    glossary = {
        "common_errors": {
            "投地登記": "土地登記",
            "投地": "土地",
            "主登": "土登",
            "課論": "各論",
            "各輪": "各論",
            "醫生師": "地政士",
            "地政師": "地政士",
            "臨底": "身特",
            "病到徒法": "併到土法",
            "病徒法": "併土法",
            "共耳": "共有人",
            "少數共耳": "少數共有人",
            "優購權": "優先購買權",
            "又過去": "優先購買權",
            "優購": "優先購買",
            "假芳": "甲方", "假方": "甲方",
            "倚芳": "乙方", "倚方": "乙方", "以方": "乙方",
            "炳芳": "丙方", "丙芳": "丙方", "炳方": "丙方",
            "丁芳": "丁方", "形法": "刑法", "形訴": "刑訴",
            "英文考試的": "應考的", "英文考試": "應考",
            "英文的考課": "應考的考科", "英文考課": "應考考科",
            "一部分是公子的": "一部分是公職的", "一部分是公子": "一部分是公職",
            "英文無法": "英文文法", "迷法": "民法",
            "永殿券": "永佃權", "榮譽券": "農育權",
            "踏向權力": "他項權利", "直入券": "之物權",
            "一習慣": "依習慣", "考課": "考科"
        }
    }
    fixed_text = text
    for wrong, right in glossary.get("common_errors", {}).items():
        fixed_text = re.sub(wrong, right, fixed_text)
    return fixed_text

LAST_CALL_TIMES = {}

def call_gemini_api(prompt, model_name, qm, current_key_ref, config=None):
    api_key = current_key_ref[0]
    global LAST_CALL_TIMES
    # 用於雲端免費大模型級聯降備（Cascade）的備選名單
    models_to_try = [model_name]
    fallback_candidates = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-3.5-flash",
        "gemini-3.1-pro-preview",
        "gemini-pro-latest"
    ]
    for m in fallback_candidates:
        if m not in models_to_try:
            models_to_try.append(m)
            
    last_err = None
    for current_model in models_to_try:
        # 強制速率限制以保護免費 API 限制
        now = time.time()
        last_time = LAST_CALL_TIMES.get(current_model, 0)
        required_interval = 30.0 if "pro" in current_model else 5.0
        elapsed = now - last_time
        if elapsed < required_interval:
            wait_time = required_interval - elapsed
            print(f"[Rate Limiter] Sleeping {wait_time:.1f} seconds to respect rate limit for {current_model}...")
            time.sleep(wait_time)
            
        LAST_CALL_TIMES[current_model] = time.time()

        # 對於每個模型，嘗試最多 3 次，並在 429 時採取退避重試
        attempt = 0
        rpm_retry_count = 0
        while attempt < 3:
            # 建立 Client (判斷是否為 Vertex ADC 通道)
            v_project = config.get("settings", {}).get("vertexai_project") if config else None
            try:
                if v_project:
                    v_loc = config.get("settings", {}).get("vertexai_location", "us-central1")
                    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
                    client = genai.Client(vertexai=True, project=v_project, location=v_loc, credentials=credentials)
                else:
                    client = genai.Client(api_key=api_key)
                    
                response = _call_with_timeout(
                    client.models.generate_content,
                    120,
                    model=current_model,
                    contents=prompt
                )
                res = response.text
                if not v_project:
                    qm.report_success(current_key_ref[0])
                return res
                
            except Exception as e:
                err_str = str(e)
                # 若為 ADC 模式，通常拋出 google_exceptions.ResourceExhausted
                # 若為 API_KEY 模式，可能包含 429 錯誤訊息
                is_timeout = isinstance(e, TimeoutError)
                is_429 = isinstance(e, google_exceptions.ResourceExhausted) or getattr(e, 'code', None) == 429 or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
                
                if is_429 or is_timeout:
                    print(f"[Gemini API] Model {current_model} returned {('Timeout' if is_timeout else '429')}. Error: {err_str}")
                    
                    # 雙 Regex 保險檢索 API 建議的避退秒數
                    wait_sec = None
                    msg_match = re.search(r'Please retry in (\d+\.?\d*)s', err_str)
                    if msg_match:
                        wait_sec = float(msg_match.group(1)) + 2.0
                    else:
                        delay_match = re.search(r'"retryDelay":\s*"(\d+)s"', err_str)
                        if delay_match:
                            wait_sec = float(delay_match.group(1)) + 2.0
                            
                    # 如果已原地重試過仍受限，或是每日限額超限，則輪替下一把金鑰
                    print(f"API Key {api_key[:8]}...{api_key[-4:]} 速率/每日額度限制，由 QuotaManager 接管處理...")
                    e_429 = Exception("429: " + err_str)
                    res = qm.handle_error(e_429, api_key, consecutive_429_count=1)
                    if res["sleep_time"] > 0:
                        time.sleep(res["sleep_time"])
                    if res["new_key"]:
                        current_key_ref[0] = res["new_key"]
                        api_key = res["new_key"]
                        print(f"已更換為新金鑰: {api_key[:8]}...{api_key[-4:]}。")
                        rpm_retry_count = 0
                        continue
                    else:
                        print("金鑰池中已無其他可用金鑰，跳過當前模型。")
                        last_err = RuntimeError(f"Daily quota exhausted for {current_model}")
                        break
                else:
                    raise RuntimeError(f"API Error: {err_str}")
            # 此區塊已被上方 ADC 雙軌重構取代，移除多餘的 exception handle 區塊
                
                print(f"[Gemini API] Error calling model {current_model}: {e}")
                last_err = e
                attempt += 1
                time.sleep(5)
                
    raise last_err or RuntimeError("All Gemini models failed")

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
        
    # 準備呼叫 Gemini 進行邊界精校與摘要
    config = load_config()
    # 強制將 merge/summary 首選大模型設為 gemini-2.5-flash，利用 cooled-down 金鑰池與快速輪替直接衝關
    model_name = "gemini-2.5-flash"
    qm = QuotaManager()
    api_key = qm.acquire_key_exclusive()
    current_key_ref = [api_key]

    log_workflow(f"Merge Agent: Reading and concatenating {len(chunks)} chunks...")
    
    # 1. 逐一合併分片文字，並對銜接邊界進行上下文精校
    merged_text = ""
    for idx, chunk in enumerate(chunks):
        chunk_path = chunk["path"]
        stem = Path(chunk_path).stem
        chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
        
        if not os.path.exists(chunk_txt_file):
            log_error(f"Merge Agent: Chunk text file missing: {chunk_txt_file}")
            continue
            
        with open(chunk_txt_file, "r", encoding="utf-8") as rf:
            chunk_content = rf.read().strip()
            
        if not merged_text:
            merged_text = chunk_content
        else:
            # 進行邊界上下文縫隙抽取與雲端精校
            chars1 = list(merged_text)
            chars2 = list(chunk_content)
            
            suffix_len = min(400, len(chars1))
            suffix = chars1[-suffix_len:]
            prefix_len = min(400, len(chars2))
            prefix = chars2[:prefix_len]
            
            matcher = difflib.SequenceMatcher(None, suffix, prefix)
            match = matcher.find_longest_match(0, suffix_len, 0, prefix_len)
            
            if match.size >= 12:
                cut_idx1 = len(chars1) - suffix_len + match.a
                part1 = "".join(chars1[:cut_idx1])
                part2 = "".join(chars2[match.b:])
                
                # 抽取銜接邊界 (前片尾 400 字 + 後片頭 400 字)
                gap_left = part1[-400:] if len(part1) >= 400 else part1
                gap_right = part2[:400] if len(part2) >= 400 else part2
                raw_gap = gap_left + " [銜接點] " + gap_right
                
                if api_key:
                    log_workflow(f"Merge Agent: 正在執行邊界縫隙 {idx}/{len(chunks)-1} 上下文語意精校...")
                    try:
                        refined_gap = call_gemini_api(PROMPT_GAP_REFINE.format(text=raw_gap), model_name, qm, current_key_ref, config)
                        refined_gap = refined_gap.replace("[銜接點]", "").strip()
                        # 用精校後的文字替換原邊界
                        part1_base = part1[:-len(gap_left)] if len(part1) >= len(gap_left) else ""
                        part2_base = part2[len(gap_right):] if len(part2) >= len(gap_right) else ""
                        merged_text = part1_base + refined_gap + part2_base
                    except Exception as ge:
                        log_error(f"Merge Agent: 邊界縫隙 {idx} 精校失敗: {ge}. fallback to direct merge.")
                        merged_text = part1 + part2
                else:
                    merged_text = part1 + part2
            else:
                merged_text = merged_text + "\n\n" + chunk_content
            
    # 雙層防禦：在寫入檔案與發送大模型前套用本地術語修正
    merged_text = apply_glossary_fix(merged_text)

    # 輸出版本 1：完整合併逐字稿
    out_full_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
    with open(out_full_path, "w", encoding="utf-8") as wf:
        wf.write(merged_text)
    log_workflow(f"Merge Agent: Saved full merged transcript to {out_full_path}")
    
    # 輸出版本 2：去冗餘整理版本 (直接使用本地去重拼接的合併本，防止大模型 output 截斷)
    cleaned_text = merged_text
    out_cleaned_path = os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt")
    with open(out_cleaned_path, "w", encoding="utf-8") as wf:
        wf.write(cleaned_text)
    log_workflow(f"Merge Agent: Saved cleaned transcript to {out_cleaned_path}")
        
    # 輸出版本 3：章節化摘要版本 (對 15 個 Chunks 分別生成摘要，並在本地拼接)
    log_workflow("Merge Agent: Running Chunk-wise chaptered summary extraction...")
    summary_blocks = []
    
    for idx, chunk in enumerate(chunks):
        chunk_path = chunk["path"]
        stem = Path(chunk_path).stem
        chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
        
        if not os.path.exists(chunk_txt_file):
            continue
            
        with open(chunk_txt_file, "r", encoding="utf-8") as rf:
            chunk_content = rf.read().strip()
            
        # 取得 Chunk 對應的開始時間
        start_sec = chunk["start_time"]
        m = int(start_sec // 60)
        s = int(start_sec % 60)
        ts_str = f"[{m:02d}:{s:02d}]"
        
        if api_key:
            log_workflow(f"Merge Agent: Processing summary for Chunk {idx+1}/{len(chunks)} ({ts_str})...")
            try:
                block_summary = call_gemini_api(PROMPT_SUMMARY.format(text=chunk_content), model_name, qm, current_key_ref, config)
                summary_blocks.append(f"### 📖 章節主題 {idx+1} {ts_str}\n\n{block_summary}\n")
            except Exception as e:
                log_error(f"Merge Agent: Summary for Chunk {idx+1} failed: {e}. Fallback to template.")
                summary_blocks.append(f"### 📖 章節主題 {idx+1} {ts_str} (摘要生成遇限失敗)\n")
        else:
            summary_blocks.append(f"### 📖 章節主題 {idx+1} {ts_str} (無 API 金鑰跳過)\n")
            
    summary_text = "\n".join(summary_blocks)
    out_summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
    with open(out_summary_path, "w", encoding="utf-8") as wf:
        wf.write(summary_text)
    log_workflow(f"Merge Agent: Saved chaptered summary to {out_summary_path}")
        
    # 更新任務 Manifest
    manifest["steps"]["merge"] = "completed"
    manifest["status"] = "merged"
    manifest["paths"] = {
        "merged_full_transcript": out_full_path,
        "merged_cleaned_transcript": out_cleaned_path,
        "merged_summary": out_summary_path
    }
    
    with open(manifest_file, "w", encoding="utf-8") as wf:
        json.dump(manifest, wf, ensure_ascii=False, indent=2)
        
    if current_key_ref[0]:
        qm.release_key(current_key_ref[0])
        
    log_workflow(f"Merge Agent: Completed merge workflow for {task_id}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    merge_workflow(args.task_id)
