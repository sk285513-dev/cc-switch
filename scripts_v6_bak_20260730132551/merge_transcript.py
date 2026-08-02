import os
import sys, io
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8-sig', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8-sig', errors='replace')
except Exception:
    pass
import sys
import argparse
import json
from manifest_manager import ManifestManager, update_manifest
import difflib
import requests
import re
import time
from pathlib import Path
from workflow_helper import ensure_dirs, load_config, log_workflow, log_error

# ==========================================
# 【機制二十六】混合架構：Whisper 本地兜底與 Gemini 雲端提效
# 目的：雙軌並行及銜接精校，將分片進行上下文比對與拼接校正。
# ==========================================
try:
    from quota_manager import QuotaManager
except ImportError:
    from quota_manager import QuotaManager

PROMPT_GAP_REFINE = """你是一個法學專業的文字編輯，請幫我將以下法律教材「分片銜接處」的上下文進行語意精校與拼接修剪：
1. 修正同音錯字（如將「投地」修正為「土地」）。
2. 修復銜接點左右的語意中斷與重複字句，使兩端句子流暢、自然地拼合在一起。
3. 嚴格保留所有實質法律內容，不要加入任何引言、解釋或額外說明。
4. 輸出修飾後的流暢銜接段落即可。

待精校銜接處內容：
{text}"""

PROMPT_CLEAN = """# Role
你是一位具備頂尖法律、商業與各領域專業素養的「首席字幕精校專家」與「語音辨識修復大師」。你擁有極強的語境推理能力，能看穿語音辨識系統（Speech-to-Text）的所有盲點。

# Goal
你的任務是接收一段充滿辨識錯誤、語意不通順、或因發音相近而產生「空耳誤判」的原始逐字稿（可能是 .srt 或帶有 [00:00] 時間標籤）。請在「完全不變動時間戳記」的前提下，將其精修為一份專業、流暢、術語精準且符合閱讀邏輯的「完整精校版檔案」。

# Strict Rules (核心修訂原則)
1. **格式與時間軸絕對恆定**：請嚴格保持原始編號與時間戳記格式。時間軸數字絕對不能有任何變動，亦不能合併或刪除字幕編號區塊。
2. **修正語音辨識錯誤（空耳）**：語音辨識系統常因音近而誤判專業術語。請根據「領域背景」與「前後文邏輯」，將語意不通的文字修正為正確的專業詞彙、法條、或學者姓名。
3. **口語贅詞流暢化**：在不影響時間軸對齊的前提下，適度刪除或精簡語音中無意義的贅字（如：「好」、「那」、「這個這個」、「然後」、「對」），提高字幕的可讀性。
4. **修復系統死當/鬼打牆區段**：若逐字稿中出現因系統錯誤而導致的連續重複字句（例如同一句話連續卡住重複十幾次），請「不要照抄」。你必須展現高超的邏輯推理能力，依據前後文的脈絡，將該受損區段重構為通順、合理的專業內容，並補回對應的時間軸內。
5. **絕對禁止截斷與摘要**：我需要的是「完整的逐字稿精校」，你必須將我提供給你的所有字幕編號從頭到尾完整處理並輸出。絕對不能在中途寫出「（以下省略）」、「（其餘相同）」或只提供摘要。

# Context & Reference (本次任務背景資訊)
* 內容領域/主題：台灣法律實務、國家考試司法官與律師相關教材
* 關鍵專有名詞參考：常見台灣法律口述同音錯字（如：「投地登記」->「土地登記」、「主登」->「土登」、「醫生師」->「地政士」、「優購權」->「優先購買權」、「消滅實效」->「消滅時效」）
* 法條與字號格式標準化：如「民法第197條」、「釋字第474號解釋」。必須依課程主題劃分 Markdown 標題階層（#、##），在關鍵段落加上重點粗體（如：**【爭點】**）。

# Input Data
以下是需要你精修的原始逐字稿：
---
{text}
---

# Output Format
請直接輸出精校後的字幕代碼區塊，不要有任何引言或解釋。
"""

PROMPT_SUMMARY = """你是一個臺灣法律專家，請分析以下教材逐字稿，提煉出結構化的「章節化大綱與爭點摘要」以利未來的 RAG 檢索：
1. 【核心爭點與法律概念】：列出本段教材講授或辯論的核心爭議點。
2. 【推理路徑與法理】：列出主要的論證邏輯與推理過程。
3. 【結論與實務見解】：列出結論，並整理文中涉及的所有重要法規條文（如民法第184條）、釋字、最高法院判決字號。（請利用 Google Search 能力核實法條為現行最新版）
4. 【章節大綱】：依據邏輯結構或時間軸，以 Markdown 的標題與條列式大綱呈現。
5. 【地理與空間資訊解析 (Maps Grounding)】：若本節涉及土地法規之實體地段（如特定市地重劃區、區段徵收案、建案或特定地標），請務必調用 Google Search 查詢該地段的實際背景，並簡要描述其空間關係與現狀。若無相關則填無。
6. 【Gemini 智能考前測驗】：請根據教材內容，以台灣國家考試（律師、司法官、地政士）的命題標準，自動生成 3~5 題混合題型（包含選擇題與實例/申論題）的「考前衝刺測驗題」，並附上精簡的解答與解析。請使用 `## 📝 Gemini 智能考前測驗` 作為此段落的標題。
7. 【影片關鍵時刻導航 (Key Moments)】：請針對長影片提煉「微章節 (細顆粒度)」的導航目錄。只要遇到主題切換、實例題開始、或重要圖表/板書解說，就標註一個時間點或段落錨點（約 15~20 個）。若文本中缺乏精確時間碼，請依段落比例或順序標示。請使用 `## ⏱️ 影片關鍵時刻導航 (Key Moments)` 作為此段落的標題，並將其放在摘要區塊的最上方。

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

def call_gemini_api(prompt, model_name, api_key, qm, use_search_grounding=False):
    """
    統一包裝器：透過 ModelRouter Agent 調用 Gemini，若為 Vertex AI 則直走企業通道。
    model_name 參數保留以相容舊介面，實際模型由 Router 决定。
    """
    import requests
    import time
    from workflow_helper import load_config
    config = load_config()
    # 獨立判斷 Merge 引擎，預設走 AI Studio (gemini) 以避免誤觸企業通道
    merge_engine = config.get("settings", {}).get("merge_engine", "gemini")

    from model_router import get_router
    router = get_router()

    if merge_engine == "vertexai":
        import os
        from google import genai
        from google.genai import types
        v_project = config.get("settings", {}).get("vertexai_project")
        v_loc = config.get("settings", {}).get("vertexai_location", "us-central1")
        v_cred_path = config.get("settings", {}).get("vertexai_credentials_path", "")
        if v_cred_path:
            full_cred_path = os.path.normpath(os.path.join(config.get("paths", {}).get("project_root", "C:\\LocalAI_Workstation"), v_cred_path))
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = full_cred_path
        
        # Vertex AI client
        client = genai.Client(vertexai=True, project=v_project, location=v_loc)
        # 強制使用高品質 Pro 模型 (Vertex AI 企業通道專用，執行最終精校)
        v_model = config.get("api", {}).get("gemini_model_high_accuracy", "gemini-2.5-flash")
        
        tool_objs = [{"google_search": {}}] if use_search_grounding else None
        
        last_err = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=v_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        tools=tool_objs
                    )
                )
                if not response.text:
                    raise ValueError("API returned empty text")
                router.report_success(v_model)
                return response.text
            except Exception as e:
                router.report_error(v_model, e)
                err_str = str(e).lower()
                last_err = e
                if "429" in err_str or "quota" in err_str:
                    print(f"[Vertex AI] 429 Quota limit hit, backing off 30s... (Attempt {attempt+1}/3)")
                    time.sleep(30)
                else:
                    print(f"[Vertex AI] Error: {e}, backing off 5s...")
                    time.sleep(5)
        raise last_err or RuntimeError(f"Vertex AI call failed after 3 attempts.")

    # ---------------- 原有 Gemini AI Studio 邏輯 ----------------

    def _do_call(current_model: str) -> str:
        nonlocal api_key
        last_err = None
        # RPM 限速
        now = time.time()
        last_time = LAST_CALL_TIMES.get(current_model, 0)
        required_interval = 30.0 if "pro" in current_model else 5.0
        elapsed = now - last_time
        if elapsed < required_interval:
            wait_time = required_interval - elapsed
            print(f"[Rate Limiter] Sleeping {wait_time:.1f} seconds to respect rate limit for {current_model}...")
            time.sleep(wait_time)
            
        LAST_CALL_TIMES[current_model] = time.time()

        # 對於每個模型，嘗試最多 3 次一般性錯誤，並在 429 時採用 QuotaManager 進行 Jitter 退避重試
        qm = None
        try:
            from quota_manager import QuotaManager
            qm = QuotaManager()
        except ImportError:
            pass

        attempt = 0
        consecutive_429 = 0
        last_err = None
        
        while True:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if use_search_grounding:
                payload["tools"] = [{"googleSearch": {}}]
            
            # 使用 QuotaManager 進行 RPM 節流防禦 (5s / 6RPM)
            if qm:
                qm.throttle_key(api_key)
                
            try:
                response = requests.post(url, json=payload, timeout=120)
                if response.status_code == 200:
                    res_data = response.json()
                    try:
                        return res_data["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError):
                        raise RuntimeError("Invalid Gemini API response format")
                elif response.status_code == 429:
                    raise Exception(f"429 Too Many Requests: {response.text}")
                elif response.status_code == 401:
                    raise Exception(f"401 Unauthorized: {response.text}")
                else:
                    raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
            except Exception as e:
                err_str = str(e)
                # 檢查連線或呼叫異常是否是因為金鑰額度限制
                if qm and ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower() or "401" in err_str):
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        consecutive_429 += 1
                        
                    res = qm.handle_error(e, api_key, consecutive_429, exclusive=True)
                    
                    if res["project_cooldown"]:
                        consecutive_429 = 0
                        
                    if res["sleep_time"] > 0:
                        print(f"[Gemini API Retry] {api_key[:8]}... 觸發 Jitter 避退，睡眠 {res['sleep_time']:.1f} 秒...")
                        time.sleep(res["sleep_time"])
                        
                    if res["new_key"] and res["new_key"] != api_key:
                        api_key = res["new_key"]
                        consecutive_429 = 0
                        print(f"已更換為新金鑰: {api_key[:8]}...{api_key[-4:]}")
                        
                    # 額度限制異常不增加一般性錯誤 attempt 計數，繼續重試
                    continue 
                
                print(f"[Gemini API] Error calling model {current_model}: {e}")
                router.report_error(current_model, e)
                last_err = e
                attempt += 1
                if attempt >= 3:
                    raise last_err or RuntimeError(f"All attempts for {current_model} failed")
                time.sleep(5)
        
    # 根據需求，直接呼叫或輪替
    res = _do_call(model_name)
    router.report_success(model_name)
    return res

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
        
    with ManifestManager(manifest_file) as mm:
            manifest = mm.read()
    with ManifestManager(chunks_manifest_file) as mm:
            chunks = mm.read()
        
    # 準備呼叫 Gemini 進行邊界精校與摘要
    config = load_config()
    qm = QuotaManager()
    try:
        api_key = qm.acquire_key_exclusive()
    except Exception as e:
        log_error(f"Merge Agent: 無法取得排他性 API 金鑰 ({e})，任務將保留，稍後重試。")
        return False

    try:
        log_workflow(f"Merge Agent: Reading and concatenating {len(chunks)} chunks...")

        # ══ 守門員：TXT 完成率必須 ≥ 85% 才允許合併 ══
        total_chunks = len(chunks)
        done_txt = 0
        for _chk in chunks:
            _stem = Path(_chk["path"]).stem
            _txt  = os.path.join(task_chunks_dir, f"{_stem}.txt")
            if os.path.exists(_txt):
                done_txt += 1
        completion_rate = done_txt / total_chunks if total_chunks > 0 else 0

        if completion_rate < 0.85:
            log_error(
                f"Merge Agent: [GUARD] STT 完成率不足！"
                f"{done_txt}/{total_chunks} = {completion_rate*100:.0f}% < 85%，"
                f"拒絕合併，重置任務為 chunked 等待重跑 STT"
            )
            # 重置 manifest：status=chunked, stt=pending, 清除 merge/formatter
            manifest["status"] = "chunked"
            manifest["steps"]["stt"] = "pending"
            manifest["steps"].pop("merge",     None)
            manifest["steps"].pop("formatter", None)
            with ManifestManager(manifest_file) as mm:
                mm.write(manifest)
            qm.release_key(api_key)
            return False   # 中止，等 STT 補完再來

        log_workflow(f"Merge Agent: STT 完成率 {done_txt}/{total_chunks} = {completion_rate*100:.0f}% >= 85%，開始合併")

    except Exception as guard_err:
        log_error(f"Merge Agent: 守門員階段異常: {guard_err}")
        qm.release_key(api_key)
        return False

    try:
        # 1. Map 階段：逐一載入分片文字，並獨立進行「全文去冗餘與格式化」 (PROMPT_CLEAN)
        merged_full_text = ""     # 保留最原始串接版本 (不呼叫 Gemini)
        merged_cleaned_text = ""  # 經過精校且邊界修復的版本

        for idx, chunk in enumerate(chunks):
            chunk_path = chunk["path"]
            stem = Path(chunk_path).stem
            chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")

            if not os.path.exists(chunk_txt_file):
                log_error(f"Merge Agent: Chunk text file missing: {chunk_txt_file}")
                continue

            with open(chunk_txt_file, "r", encoding="utf-8-sig") as rf:
                chunk_content = rf.read().strip()

            # [Baseline] 原始文字合併
            if not merged_full_text:
                merged_full_text = chunk_content
            else:
                merged_full_text = merged_full_text + "\n\n" + chunk_content

            # [Map] 對此 Chunk 進行去冗餘與排版
            cleaned_chunk = chunk_content
            if api_key:
                log_workflow(f"Merge Agent: 正在執行切片 {idx+1}/{len(chunks)} 的去冗餘與排版 (Map)...")
                try:
                    from model_router import get_router as _get_router
                    current_model = _get_router().acquire()
                    cleaned_chunk = call_gemini_api(PROMPT_CLEAN.format(text=chunk_content), current_model, api_key, qm)
                except Exception as ce:
                    log_error(f"Merge Agent: 切片 {idx+1} 去冗餘失敗: {ce}. fallback to raw chunk.")

            # [Reduce] 邊界修復與縫合
            if not merged_cleaned_text:
                merged_cleaned_text = cleaned_chunk
            else:
                chars1 = list(merged_cleaned_text)
                chars2 = list(cleaned_chunk)

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

                    gap_left = part1[-400:] if len(part1) >= 400 else part1
                    gap_right = part2[:400] if len(part2) >= 400 else part2
                    raw_gap = gap_left + " [銜接點] " + gap_right

                    if api_key:
                        log_workflow(f"Merge Agent: 正在執行縫隙 {idx}/{len(chunks)-1} 邊界平滑化 (Reduce)...")
                        try:
                            from model_router import get_router as _get_router
                            current_model = _get_router().acquire()
                            refined_gap = call_gemini_api(PROMPT_GAP_REFINE.format(text=raw_gap), current_model, api_key, qm)
                            refined_gap = refined_gap.replace("[銜接點]", "").strip()
                            part1_base = part1[:-len(gap_left)] if len(part1) >= len(gap_left) else ""
                            part2_base = part2[len(gap_right):] if len(part2) >= len(gap_right) else ""
                            merged_cleaned_text = part1_base + refined_gap + part2_base
                        except Exception as ge:
                            log_error(f"Merge Agent: 邊界縫隙 {idx} 精校失敗: {ge}. fallback to direct merge.")
                            merged_cleaned_text = part1 + part2
                    else:
                        merged_cleaned_text = part1 + part2
                else:
                    merged_cleaned_text = merged_cleaned_text + "\n\n" + cleaned_chunk

        # 雙層防禦：在寫入檔案與發送大模型前套用本地術語修正
        merged_full_text = apply_glossary_fix(merged_full_text)
        merged_cleaned_text = apply_glossary_fix(merged_cleaned_text)

        # 輸出版本 1：完整合併逐字稿
        out_full_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
        with open(out_full_path, "w", encoding="utf-8-sig") as wf:
            wf.write(merged_full_text)
        log_workflow(f"Merge Agent: Saved full merged transcript to {out_full_path}")

        # 輸出版本 2：去冗餘整理版本
        out_cleaned_path = os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt")
        with open(out_cleaned_path, "w", encoding="utf-8-sig") as wf:
            wf.write(merged_cleaned_text)
        log_workflow(f"Merge Agent: Saved cleaned transcript to {out_cleaned_path}")

        # 輸出版本 3：章節化摘要版本 (全局摘要)
        log_workflow("Merge Agent: Running Global chaptered summary extraction (1,000,000 chars limit)...")

        # 保護機制：強制截斷於 1,000,000 字
        safe_cleaned_text = merged_cleaned_text[:1000000]

        if api_key:
            try:
                from model_router import get_router as _get_router
                current_model = _get_router().acquire()
                summary_text = call_gemini_api(PROMPT_SUMMARY.format(text=safe_cleaned_text), current_model, api_key, qm, use_search_grounding=True)
            except Exception as e:
                log_error(f"Merge Agent: Global summary failed: {e}. Fallback to template.")
                summary_text = "### 📖 全局章節大綱 (摘要生成遇限失敗)\n"
        else:
            summary_text = "### 📖 全局章節大綱 (無 API 金鑰跳過)\n"

        out_summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
        with open(out_summary_path, "w", encoding="utf-8-sig") as wf:
            wf.write(summary_text)
        log_workflow(f"Merge Agent: Saved global chaptered summary to {out_summary_path}")

        # 更新任務 Manifest
        manifest["steps"]["merge"] = "completed"
        manifest["status"] = "merged"
        manifest["paths"] = {
            "merged_full_transcript": out_full_path,
            "merged_cleaned_transcript": out_cleaned_path,
            "merged_summary": out_summary_path
        }

        with ManifestManager(manifest_file) as mm:
            mm.write(manifest)

        log_workflow(f"Merge Agent: Completed merge workflow for {task_id}")
        qm.release_key(api_key)
        return True

    except Exception as e:
        log_error(f"Merge Agent: Unexpected error: {e}")
        qm.release_key(api_key)
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    merge_workflow(args.task_id)
