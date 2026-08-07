# 實體硬碟檔案逐行 Diff 分析報告

> 本報告由 Python difflib 模組直接讀取您的硬碟檔案產生，絕無經過語言模型生成或幻覺，保證 100% 反映真實的原始碼變更。

## merge_transcript.py

`diff
--- Before (Golden Backup)
+++ After (Current Version)
@@ -1,13 +1,29 @@
-(from August 2nd/3rd Backup) ---
+(Current version) ---
 import os
 import sys
 from pathlib import Path
 sys.path.append(str(Path(__file__).resolve().parent.parent))
 try:
     if hasattr(sys.stdout, 'reconfigure'):
-        sys.stdout.reconfigure(encoding='utf-8-sig', errors='replace')
+        try:
+            if sys.stdout is not None:
+                try:
+                    if sys.stdout is not None:
+                        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
+                except Exception:
+                    pass
+        except Exception:
+            pass
     if hasattr(sys.stderr, 'reconfigure'):
-        sys.stderr.reconfigure(encoding='utf-8-sig', errors='replace')
+        try:
+            if sys.stderr is not None:
+                try:
+                    if sys.stderr is not None:
+                        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
+                except Exception:
+                    pass
+        except Exception:
+            pass
 except Exception:
     pass
 import argparse
@@ -15,7 +31,7 @@
 import difflib
 import requests
 import re
-from workflow_helper import ensure_dirs, load_config, log_workflow, log_error
+from workflow_helper import ensure_dirs, load_config, log_workflow, log_error, log_stage
 from llm_gateway import call_llm_with_resilience
 
 # ==========================================
@@ -52,7 +68,7 @@
         }
 
         with log_path.open("a", encoding="utf-8", errors="replace") as f:
-            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
+            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
     except Exception:
         pass
 
@@ -250,8 +266,28 @@
 
     if merge_engine == "vertexai":
         import os
+        import threading
         from google import genai
         from google.genai import types
+
+        def _call_with_timeout(func, timeout_sec, *args, **kwargs):
+            result = [None]
+            exception = [None]
+            def worker():
+                try:
+                    result[0] = func(*args, **kwargs)
+                except Exception as e:
+                    exception[0] = e
+            thread = threading.Thread(target=worker)
+            thread.daemon = True
+            thread.start()
+            thread.join(timeout_sec)
+            if thread.is_alive():
+                raise TimeoutError("vertex_timeout")
+            if exception[0]:
+                raise exception[0]
+            return result[0]
+
         v_project = config.get("settings", {}).get("vertexai_project")
         v_loc = config.get("settings", {}).get("vertexai_location", "us-central1")
         v_cred_path = config.get("settings", {}).get("vertexai_credentials_path", "")
@@ -274,9 +310,14 @@
         last_err = None
         timeout_like_errors = 0
 
+        # [DIAGNOSTIC] 診斷不洩密日誌
+        print(f"[DIAGNOSTIC] merge_engine={merge_engine}, auth_mode=vertex, model={v_model}, project={v_project}, location={v_loc}")
+
         for attempt in range(3):
             try:
-                response = client.models.generate_content(
+                response = _call_with_timeout(
+                    client.models.generate_content,
+                    timeout,
                     model=v_model,
                     contents=prompt,
                     config=types.GenerateContentConfig(
@@ -371,7 +412,14 @@
                 qm.throttle_key(api_key)
                 
             try:
+                # [DIAGNOSTIC] 診斷不洩密日誌
+                import hashlib
+                key_preview = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:6] if api_key else "None"
+                print(f"[DIAGNOSTIC] merge_engine={merge_engine}, auth_mode=aistudio, model={current_model}, key_sha256_prefix={key_preview}")
+                
                 response = requests.post(url, json=payload, timeout=timeout)
+                # [DIAGNOSTIC] HTTP Status 紀錄
+                print(f"[DIAGNOSTIC] HTTP Status: {response.status_code}")
                 if response.status_code == 200:
                     res_data = response.json()
                     try:
@@ -439,6 +487,12 @@
     with ManifestManager(chunks_manifest_file) as mm:
         chunks = mm.read() or []
 
+    source_name = manifest.get("source_name", task_id)
+    import time as _time_mod
+    _merge_start_t = _time_mod.time()
+    _merge_ok = 0
+    log_stage(task_id, "merge", "IN", extra={"source": source_name, "chunks": len(chunks)})
+
     qm = QuotaManager()
     api_key = None
     raw_chunks = []
@@ -733,14 +787,22 @@
         try:
             from model_router import get_router as _get_router
             current_model = _get_router().acquire()
-            summary_text = call_gemini_api(
-                PROMPT_SUMMARY.format(text=safe_cleaned_text),
-                current_model,
-                api_key,
-                qm,
+            _summary_result = call_llm_with_resilience(
+                stage="reduce",
+                task_id=task_id,
+                chunk_id="summary",
+                prompt=PROMPT_SUMMARY.format(text=safe_cleaned_text),
+                model_name=current_model,
+                api_key=api_key,
+                qm=qm,
+                timeout=120.0,
                 use_search_grounding=True,
-                timeout=120.0
             )
+            if _summary_result.ok and _summary_result.text:
+                summary_text = _summary_result.text
+            else:
+                log_error(f"Merge Agent: Summary LLM returned non-ok: {_summary_result.error_code}")
+                summary_text = "### 📖 全局章節大綱 (摘要生成遇限失敗)\n"
         except Exception as e:
             log_error(f"Merge Agent: Global summary failed: {e}. Fallback to template.")
             summary_text = "### 📖 全局章節大綱 (摘要生成遇限失敗)\n"
@@ -787,6 +849,8 @@
         return False
 
     finally:
+        _merge_elapsed = round(_time_mod.time() - _merge_start_t, 1)
+        log_stage(task_id, "merge", "OUT", ok=_merge_ok, elapsed=_merge_elapsed)
         try:
             if api_key:
                 qm.release_key(api_key)
`

## markdown_formatter.py

`diff
--- Before (Golden Backup)
+++ After (Current Version)
@@ -1,13 +1,29 @@
-(from August 2nd/3rd Backup) ---
+(Current version) ---
 import json
 import os
 import sys, io
 from pathlib import Path
 sys.path.append(str(Path(__file__).resolve().parent.parent))
 if hasattr(sys.stdout, 'reconfigure'):
-    sys.stdout.reconfigure(encoding='utf-8-sig', errors='replace')
+    try:
+        if sys.stdout is not None:
+            try:
+                if sys.stdout is not None:
+                    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
+            except Exception:
+                pass
+    except Exception:
+        pass
 if hasattr(sys.stderr, 'reconfigure'):
-    sys.stderr.reconfigure(encoding='utf-8-sig', errors='replace')
+    try:
+        if sys.stderr is not None:
+            try:
+                if sys.stderr is not None:
+                    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
+            except Exception:
+                pass
+    except Exception:
+        pass
 import sys
 import argparse
 import json
@@ -15,7 +31,7 @@
 import re
 import time
 from pathlib import Path
-from workflow_helper import ensure_dirs, load_config, log_workflow, log_error
+from workflow_helper import ensure_dirs, load_config, log_workflow, log_error, log_stage
 try:
     from quota_manager import QuotaManager
 except ImportError:
@@ -39,10 +55,16 @@
                 }
                 req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                 if qm: qm.throttle_key(api_key)
-                with urllib.request.urlopen(req, timeout=10) as response:
+                with urllib.request.urlopen(req, timeout=45) as response:
                     res_data = json.loads(response.read().decode("utf-8"))
                     prompt = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                 break # Success
+            except (urllib.error.URLError, TimeoutError) as e:
+                err_str = str(e)
+                if qm:
+                    res = qm.handle_error(e, api_key, consecutive_429)
+                    if res["sleep_time"] > 0: time.sleep(res["sleep_time"])
+                continue
             except Exception as e:
                 err_str = str(e)
                 if qm and ("429" in err_str or "quota" in err_str.lower() or "401" in err_str):
@@ -92,10 +114,16 @@
                 }
                 req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                 if qm: qm.throttle_key(api_key)
-                with urllib.request.urlopen(req, timeout=10) as response:
+                with urllib.request.urlopen(req, timeout=45) as response:
                     res_data = json.loads(response.read().decode("utf-8"))
                     prompt = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                 break # Success
+            except (urllib.error.URLError, TimeoutError) as e:
+                err_str = str(e)
+                if qm:
+                    res = qm.handle_error(e, api_key, consecutive_429)
+                    if res["sleep_time"] > 0: time.sleep(res["sleep_time"])
+                continue
             except Exception as e:
                 err_str = str(e)
                 if qm and ("429" in err_str or "quota" in err_str.lower() or "401" in err_str):
@@ -353,7 +381,7 @@
             "cot":         cot,
         }
         with open(out_path, "a", encoding="utf-8-sig") as f:
-            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
+            f.write(json.dumps(pair, ensure_ascii=True) + "\n")
         pairs_written += 1
 
         # 每 Chunk 一個訓練對（細粒度，品質更高）
@@ -375,7 +403,7 @@
                 "cot":         cot_chunk,
             }
             with open(out_path, "a", encoding="utf-8-sig") as f:
-                f.write(json.dumps(pair_chunk, ensure_ascii=False) + "\n")
+                f.write(json.dumps(pair_chunk, ensure_ascii=True) + "\n")
             pairs_written += 1
 
         log_workflow(f"Markdown Formatter: [Distill] {pairs_written} training pairs saved -> {out_path}")
@@ -400,445 +428,467 @@
             manifest = mm.read()
     with ManifestManager(chunks_manifest_file) as mm:
             chunks = mm.read()
-        
-    media_info = manifest.get("media_info", {})
-    source_name = manifest["source_name"]
-    source_stem = Path(source_name).stem
-    
-    full_txt_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
-    cleaned_txt_path = os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt")
-    summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
-    
-    if not os.path.exists(full_txt_path):
-        log_error(f"Merged transcript missing at {full_txt_path}")
-        return False
-        
-    with open(full_txt_path, "r", encoding="utf-8-sig") as f:
-        full_text = f.read()
-        
-    cleaned_text = ""
-    if os.path.exists(cleaned_txt_path):
-        with open(cleaned_txt_path, "r", encoding="utf-8-sig") as f:
-            cleaned_text = f.read()
-            
-    summary_text = ""
-    if os.path.exists(summary_path):
-        with open(summary_path, "r", encoding="utf-8-sig") as f:
-            summary_text = f.read()
-            
-    log_workflow("Markdown Formatter: Speculating legal subject and extracting index terms...")
-    spec_subject = speculate_legal_subject(full_text)
-    articles, interpretations, cases = extract_legal_indices(full_text)
-    
-    highlighted_summary = summary_text
-    keywords_highlight = ["爭點", "重點整理", "必考", "結論", "實務見解"]
-    for kw in keywords_highlight:
-        highlighted_summary = re.sub(f"({kw})", r"**【\1】**", highlighted_summary)
-        
-    duration_min = int(media_info.get("duration_sec", 0) // 60)
-    duration_sec = int(media_info.get("duration_sec", 0) % 60)
-    
-    # 執行影片板書追蹤並整合至逐字稿
-    cleaned_with_notes = cleaned_text if cleaned_text else full_text
-    
-    if manifest.get("source_path", "").lower().endswith(".mp4"):
+            
+    source_name = manifest.get("source_name", task_id)
+    log_stage(task_id, "formatter", "IN", extra={"source": source_name})
+    
+    import time as time_mod
+    start_t = time_mod.time()
+    ok_flag = 0
+    
+    try:
+        media_info = manifest.get("media_info", {})
+        source_name = manifest["source_name"]
+        source_stem = Path(source_name).stem
+    
+        full_txt_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
+        cleaned_txt_path = os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt")
+        summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
+    
+        if not os.path.exists(full_txt_path):
+            log_error(f"Merged transcript missing at {full_txt_path}")
+            return False
+        
+        with open(full_txt_path, "r", encoding="utf-8-sig") as f:
+            full_text = f.read()
+        
+        cleaned_text = ""
+        if os.path.exists(cleaned_txt_path):
+            with open(cleaned_txt_path, "r", encoding="utf-8-sig") as f:
+                cleaned_text = f.read()
+            
+        summary_text = ""
+        if os.path.exists(summary_path):
+            with open(summary_path, "r", encoding="utf-8-sig") as f:
+                summary_text = f.read()
+            
+        log_workflow("Markdown Formatter: Speculating legal subject and extracting index terms...")
+        spec_subject = speculate_legal_subject(full_text)
+        articles, interpretations, cases = extract_legal_indices(full_text)
+    
+        highlighted_summary = summary_text
+        keywords_highlight = ["爭點", "重點整理", "必考", "結論", "實務見解"]
+        for kw in keywords_highlight:
+            highlighted_summary = re.sub(f"({kw})", r"**【\1】**", highlighted_summary)
+        
+        duration_min = int(media_info.get("duration_sec", 0) // 60)
+        duration_sec = int(media_info.get("duration_sec", 0) % 60)
+    
+        # 執行影片板書追蹤並整合至逐字稿
+        cleaned_with_notes = cleaned_text if cleaned_text else full_text
+    
+        if manifest.get("source_path", "").lower().endswith(".mp4"):
+            try:
+                from visual_analyzer import VisualLegalAnalyzer
+                analyzer = VisualLegalAnalyzer()
+                parts = source_name.split("_")
+                class_name = parts[0] if len(parts) > 1 else "法律實務"
+                lesson_name = parts[1] if len(parts) > 2 else "第一堂"
+            
+                video_path = manifest["source_path"]
+                if os.path.exists(video_path):
+                    log_workflow(f"Markdown Formatter: Auto-tracking blackboard for video {source_name}...")
+                    analyzer.track_video_blackboard(video_path, class_name, lesson_name)
+                
+                    # 進行板書與逐字稿的時間軸交叉插補
+                    clean_video_name = analyzer._sanitize_filename(source_stem)
+                    cleaned_with_notes = interleave_blackboard_notes(cleaned_with_notes, clean_video_name, str(analyzer.obsidian_dir))
+                else:
+                    log_error(f"Markdown Formatter: Original video not found for blackboard tracking: {video_path}")
+            except Exception as vae:
+                log_error(f"Markdown Formatter: Failed to run blackboard tracking or interleave notes: {vae}")
+            
+        api_key_for_assets = None
+        qm = QuotaManager() if QuotaManager else None
+        if qm:
+            try:
+                api_key_for_assets = qm.acquire_key_exclusive()
+            except:
+                api_key_for_assets = os.environ.get("GEMINI_API_KEY")
+        else:
+            api_key_for_assets = os.environ.get("GEMINI_API_KEY")
+
+        # 自動生成講義封面圖片
+        cover_md = ""
         try:
-            from visual_analyzer import VisualLegalAnalyzer
-            analyzer = VisualLegalAnalyzer()
-            parts = source_name.split("_")
-            class_name = parts[0] if len(parts) > 1 else "法律實務"
-            lesson_name = parts[1] if len(parts) > 2 else "第一堂"
-            
-            video_path = manifest["source_path"]
-            if os.path.exists(video_path):
-                log_workflow(f"Markdown Formatter: Auto-tracking blackboard for video {source_name}...")
-                analyzer.track_video_blackboard(video_path, class_name, lesson_name)
-                
-                # 進行板書與逐字稿的時間軸交叉插補
-                clean_video_name = analyzer._sanitize_filename(source_stem)
-                cleaned_with_notes = interleave_blackboard_notes(cleaned_with_notes, clean_video_name, str(analyzer.obsidian_dir))
+            cover_filename = generate_cover_image(spec_subject, source_stem, processed_md_dir, api_key=api_key_for_assets)
+            if cover_filename:
+                cover_md = f"![課程封面](./{cover_filename})\n\n"
+                log_workflow(f"Markdown Formatter: Generated cover image {cover_filename}")
+        except Exception as e:
+            log_error(f"Markdown Formatter: Failed to generate cover image: {e}")
+
+        # 自動生成複雜概念短影片 (Fallback 為分鏡圖)
+        video_md = ""
+        try:
+            video_filename, matched_concept = generate_concept_video(summary_text, source_stem, processed_md_dir, api_key=api_key_for_assets)
+            if video_filename:
+                video_md = f"\n> [!TIP]\n> 🎬 **AI 影片解說 (生成中/降級保護)**：偵測到複雜法律概念「{matched_concept}」，為您產生視覺化白板分鏡圖。\n> ![分鏡圖](./{video_filename})\n\n"
+                log_workflow(f"Markdown Formatter: Generated concept video storyboard {video_filename} for '{matched_concept}'")
+        except Exception as e:
+            log_error(f"Markdown Formatter: Failed to generate concept video: {e}")
+
+        if qm and api_key_for_assets:
+            try:
+                qm.release_key(api_key_for_assets)
+            except:
+                pass
+
+        # 組合 Markdown 內容
+        md_content = f"""# 臺灣法律教材研讀：{source_stem}
+
+    {cover_md}## 📊 檔案元數據 (Metadata)
+    - **原始檔名**：{source_name}
+    - **分析日期**：{time.strftime("%Y-%m-%d %H:%M:%S")}
+    - **教材學科**：{spec_subject}
+    - **教材時長**：{duration_min} 分 {duration_sec} 秒
+    - **總切片數**：{manifest.get("chunks_count", 1)} 片
+    - **語言語系**：繁體中文 (台灣常規法律實務)
+
+    ## ⚖️ 關聯法規與實務見解索引
+    - **法規條文**：{", ".join(articles) if articles else "未偵測到明確條文"}
+    - **司法釋字**：{", ".join(interpretations) if interpretations else "未偵測到明確釋字"}
+    - **實務判決**：{", ".join(cases) if cases else "未偵測到明確裁判字號"}
+
+    ---
+
+    ## 🧠 智慧教材法理消化 (RAG 摘要)
+    {highlighted_summary}
+    {video_md}
+    ---
+
+    ## 🎙️ 去冗餘精校逐字稿 (Cleaned Transcript)
+    {cleaned_with_notes}
+    """
+
+        out_md_file = os.path.join(processed_md_dir, f"{source_stem}.md")
+        with open(out_md_file, "w", encoding="utf-8-sig") as wf:
+            wf.write(md_content)
+        log_workflow(f"Markdown Formatter: Saved final Markdown file to {out_md_file}")
+    
+        # 5. 時間軸字幕段落解析（修正版）
+        log_workflow("Markdown Formatter: Parsing time-aligned segments for SRT, VTT, and TXT...")
+        all_segments = []
+
+        for idx, chunk in enumerate(chunks):
+            chunk_path = chunk["path"]
+            stem = Path(chunk_path).stem
+            chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
+
+            if not os.path.exists(chunk_txt_file):
+                continue
+
+            with open(chunk_txt_file, "r", encoding="utf-8-sig") as rf:
+                chunk_content = rf.read().strip()
+
+            chunk_start = chunk["start_time"]   # 此 chunk 在原始影片的絕對起始秒數
+            chunk_end   = chunk["end_time"]
+
+            # ── 取得此分片的正確時間段落（加入絕對偏移）──
+            chunk_segs = parse_transcript_into_timed_segments(chunk_content, chunk_start)
+
+            # ── 近鄰去重：僅保留在 chunk 實際時間範圍內的段落 ──
+            # 不使用固定 ±15s 視窗（該邏輯錯誤過濾每個 chunk 開頭的合法內容）
+            # 改用：只要段落的絕對 start 落在 [chunk_start, chunk_end] 內即保留
+            for seg in chunk_segs:
+                if chunk_start <= seg["start"] <= chunk_end:
+                    all_segments.append(seg)
+
+        # ── Fallback：若 chunk txt 全部遺失，從 merged_full_transcript 估算時間軸 ──
+        if not all_segments and os.path.exists(full_txt_path):
+            log_workflow("Markdown Formatter: [Fallback] No chunk txt found, estimating SRT from merged transcript...")
+            total_dur = media_info.get("duration_sec", 0) or (chunks[-1]["end_time"] if chunks else 3600)
+            with open(full_txt_path, "r", encoding="utf-8-sig") as rf:
+                fb_text = rf.read()
+            # 先嘗試解析 merged_full 裡的 [MM:SS] 時間戳
+            fb_segs = parse_transcript_into_timed_segments(fb_text, 0)
+            # merged_full 的時間戳是各 chunk 的相對時間，需要根據章節重新分配絕對偏移
+            # 策略：把所有段落按章節分配到整個影片時長，均等縮放
+            if fb_segs:
+                last_ts = fb_segs[-1]["start"]
+                if last_ts > 0:
+                    scale = total_dur / (last_ts + 30)
+                    for seg in fb_segs:
+                        seg["start"] = seg["start"] * scale
+                        seg["end"]   = seg["end"]   * scale
+                all_segments = fb_segs
             else:
-                log_error(f"Markdown Formatter: Original video not found for blackboard tracking: {video_path}")
-        except Exception as vae:
-            log_error(f"Markdown Formatter: Failed to run blackboard tracking or interleave notes: {vae}")
-            
-    api_key_for_assets = None
-    qm = QuotaManager() if QuotaManager else None
-    if qm:
+                # 最後手段：把 merged_full 文字按字數均等切成句子，分配時間
+                sentences = [s.strip() for s in re.split(r"[。！？\n]+", fb_text) if len(s.strip()) > 5]
+                if sentences:
+                    slot = total_dur / len(sentences)
+                    for i, sent in enumerate(sentences):
+                        all_segments.append({
+                            "start": i * slot,
+                            "end":   (i + 1) * slot,
+                            "text":  sent[:80]
+                        })
+
+        # ── 依絕對時間排序 ──
+        all_segments.sort(key=lambda x: x["start"])
+
+        # ── 近鄰去重：移除與前一個段落起始時間差 < 1s 的重複段落 ──
+        deduped = []
+        prev_start = -999
+        for seg in all_segments:
+            if seg["start"] - prev_start >= 1.0:
+                deduped.append(seg)
+                prev_start = seg["start"]
+        all_segments = deduped
+
+        # ── 微調結束時間，確保不重疊 ──
+        for i in range(len(all_segments) - 1):
+            if all_segments[i]["end"] > all_segments[i+1]["start"]:
+                all_segments[i]["end"] = all_segments[i+1]["start"]
+            if all_segments[i]["end"] <= all_segments[i]["start"]:
+                all_segments[i]["end"] = all_segments[i]["start"] + 3.0
+        if all_segments:
+            if all_segments[-1]["end"] <= all_segments[-1]["start"]:
+                all_segments[-1]["end"] = all_segments[-1]["start"] + 3.0
+
+        log_workflow(f"Markdown Formatter: SRT 共 {len(all_segments)} 個字幕段落（已修正時間偏移）")
+
+        # 輸出 SRT
+        srt_lines = []
+        for s_idx, seg in enumerate(all_segments):
+            srt_lines.append(str(s_idx + 1))
+            srt_lines.append(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}")
+            srt_lines.append(seg["text"])
+            srt_lines.append("")
+        out_srt_file = os.path.join(processed_md_dir, f"{source_stem}.srt")
+        with open(out_srt_file, "w", encoding="utf-8-sig") as wf:
+            wf.write("\n".join(srt_lines))
+        log_workflow(f"Markdown Formatter: Saved SRT subtitle to {out_srt_file}")
+    
+        # 輸出 VTT
+        vtt_lines = ["WEBVTT", ""]
+        for s_idx, seg in enumerate(all_segments):
+            vtt_lines.append(str(s_idx + 1))
+            vtt_lines.append(f"{format_vtt_time(seg['start'])} --> {format_vtt_time(seg['end'])}")
+            vtt_lines.append(seg["text"])
+            vtt_lines.append("")
+        out_vtt_file = os.path.join(processed_md_dir, f"{source_stem}.vtt")
+        with open(out_vtt_file, "w", encoding="utf-8-sig") as wf:
+            wf.write("\n".join(vtt_lines))
+        log_workflow(f"Markdown Formatter: Saved VTT subtitle to {out_vtt_file}")
+    
+        # 輸出純文字 TXT
+        clean_txt = cleaned_text if cleaned_text else full_text
+        # 移除 Markdown 標題
+        clean_txt = re.sub(r"#+\s+.*?\n", "", clean_txt)
+        # 移除時間軸標記
+        clean_txt = re.sub(r"\[(?:(\d{1,2}):)?(\d{2}):(\d{2})\]", "", clean_txt)
+        # 整理空行
+        clean_txt = re.sub(r"\n\s*\n+", "\n\n", clean_txt).strip()
+    
+        out_txt_file = os.path.join(processed_md_dir, f"{source_stem}.txt")
+        with open(out_txt_file, "w", encoding="utf-8-sig") as wf:
+            wf.write(clean_txt)
+        log_workflow(f"Markdown Formatter: Saved pure TXT transcript to {out_txt_file}")
+    
+        # 6. 輸出 RAG 系統專用 JSON 索引
+        rag_index = {
+            "task_id": task_id,
+            "doc_id": task_id, # for Qdrant compatibility
+            "original_name": source_name,
+            "title": source_stem, # for Qdrant compatibility
+            "source_path": source_name, # for Qdrant compatibility
+            "processing_date": time.strftime("%Y-%m-%d %H:%M:%S"),
+            "duration_sec": media_info.get("duration_sec", 0),
+            "speculated_subject": spec_subject,
+            "inferred_subject": spec_subject, # for Qdrant compatibility
+            "indices": {
+                "articles": articles,
+                "interpretations": interpretations,
+                "cases": cases
+            },
+            "summary": summary_text,
+            "full_text_cleaned": clean_txt,
+            "cleaned_text": clean_txt, # for Qdrant compatibility
+            "segments": all_segments
+        }
+    
+        out_json_file = os.path.join(processed_md_dir, f"{source_stem}_index.json")
+        with ManifestManager(out_json_file) as mm:
+                mm.write(rag_index)
+        log_workflow(f"Markdown Formatter: Saved RAG JSON index to {out_json_file}")
+    
+        # 6.5. 自動備份檔案存回影片原始目錄
         try:
-            api_key_for_assets = qm.acquire_key_exclusive()
-        except:
-            api_key_for_assets = os.environ.get("GEMINI_API_KEY")
-    else:
-        api_key_for_assets = os.environ.get("GEMINI_API_KEY")
-
-    # 自動生成講義封面圖片
-    cover_md = ""
-    try:
-        cover_filename = generate_cover_image(spec_subject, source_stem, processed_md_dir, api_key=api_key_for_assets)
-        if cover_filename:
-            cover_md = f"![課程封面](./{cover_filename})\n\n"
-            log_workflow(f"Markdown Formatter: Generated cover image {cover_filename}")
-    except Exception as e:
-        log_error(f"Markdown Formatter: Failed to generate cover image: {e}")
-
-    # 自動生成複雜概念短影片 (Fallback 為分鏡圖)
-    video_md = ""
-    try:
-        video_filename, matched_concept = generate_concept_video(summary_text, source_stem, processed_md_dir, api_key=api_key_for_assets)
-        if video_filename:
-            video_md = f"\n> [!TIP]\n> 🎬 **AI 影片解說 (生成中/降級保護)**：偵測到複雜法律概念「{matched_concept}」，為您產生視覺化白板分鏡圖。\n> ![分鏡圖](./{video_filename})\n\n"
-            log_workflow(f"Markdown Formatter: Generated concept video storyboard {video_filename} for '{matched_concept}'")
-    except Exception as e:
-        log_error(f"Markdown Formatter: Failed to generate concept video: {e}")
-
-    if qm and api_key_for_assets:
+            source_path = manifest.get("source_path")
+            if source_path:
+                backup_dir = os.path.dirname(source_path)
+                if os.path.exists(backup_dir):
+                    import shutil
+                    for fpath in [out_md_file, out_srt_file, out_vtt_file, out_txt_file, out_json_file]:
+                        if os.path.exists(fpath):
+                            shutil.copy(fpath, backup_dir)
+                    log_workflow(f"Markdown Formatter: 成功將所有產出檔案備份至影片原目錄: {backup_dir}")
+                else:
+                    log_workflow(f"Markdown Formatter: 影片原目錄不存在，跳過備份: {backup_dir}", level="warning")
+        except Exception as e:
+            log_workflow(f"Markdown Formatter: 自動備份至影片原目錄失敗: {e}", level="warning")
+    
+        # 7. 寫入 ChromaDB RAG 資料庫
         try:
-            qm.release_key(api_key_for_assets)
-        except:
-            pass
-
-    # 組合 Markdown 內容
-    md_content = f"""# 臺灣法律教材研讀：{source_stem}
-
-{cover_md}## 📊 檔案元數據 (Metadata)
-- **原始檔名**：{source_name}
-- **分析日期**：{time.strftime("%Y-%m-%d %H:%M:%S")}
-- **教材學科**：{spec_subject}
-- **教材時長**：{duration_min} 分 {duration_sec} 秒
-- **總切片數**：{manifest.get("chunks_count", 1)} 片
-- **語言語系**：繁體中文 (台灣常規法律實務)
-
-## ⚖️ 關聯法規與實務見解索引
-- **法規條文**：{", ".join(articles) if articles else "未偵測到明確條文"}
-- **司法釋字**：{", ".join(interpretations) if interpretations else "未偵測到明確釋字"}
-- **實務判決**：{", ".join(cases) if cases else "未偵測到明確裁判字號"}
-
----
-
-## 🧠 智慧教材法理消化 (RAG 摘要)
-{highlighted_summary}
-{video_md}
----
-
-## 🎙️ 去冗餘精校逐字稿 (Cleaned Transcript)
-{cleaned_with_notes}
-"""
-
-    out_md_file = os.path.join(processed_md_dir, f"{source_stem}.md")
-    with open(out_md_file, "w", encoding="utf-8-sig") as wf:
-        wf.write(md_content)
-    log_workflow(f"Markdown Formatter: Saved final Markdown file to {out_md_file}")
-    
-    # 5. 時間軸字幕段落解析（修正版）
-    log_workflow("Markdown Formatter: Parsing time-aligned segments for SRT, VTT, and TXT...")
-    all_segments = []
-
-    for idx, chunk in enumerate(chunks):
-        chunk_path = chunk["path"]
-        stem = Path(chunk_path).stem
-        chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
-
-        if not os.path.exists(chunk_txt_file):
-            continue
-
-        with open(chunk_txt_file, "r", encoding="utf-8-sig") as rf:
-            chunk_content = rf.read().strip()
-
-        chunk_start = chunk["start_time"]   # 此 chunk 在原始影片的絕對起始秒數
-        chunk_end   = chunk["end_time"]
-
-        # ── 取得此分片的正確時間段落（加入絕對偏移）──
-        chunk_segs = parse_transcript_into_timed_segments(chunk_content, chunk_start)
-
-        # ── 近鄰去重：僅保留在 chunk 實際時間範圍內的段落 ──
-        # 不使用固定 ±15s 視窗（該邏輯錯誤過濾每個 chunk 開頭的合法內容）
-        # 改用：只要段落的絕對 start 落在 [chunk_start, chunk_end] 內即保留
-        for seg in chunk_segs:
-            if chunk_start <= seg["start"] <= chunk_end:
-                all_segments.append(seg)
-
-    # ── Fallback：若 chunk txt 全部遺失，從 merged_full_transcript 估算時間軸 ──
-    if not all_segments and os.path.exists(full_txt_path):
-        log_workflow("Markdown Formatter: [Fallback] No chunk txt found, estimating SRT from merged transcript...")
-        total_dur = media_info.get("duration_sec", 0) or (chunks[-1]["end_time"] if chunks else 3600)
-        with open(full_txt_path, "r", encoding="utf-8-sig") as rf:
-            fb_text = rf.read()
-        # 先嘗試解析 merged_full 裡的 [MM:SS] 時間戳
-        fb_segs = parse_transcript_into_timed_segments(fb_text, 0)
-        # merged_full 的時間戳是各 chunk 的相對時間，需要根據章節重新分配絕對偏移
-        # 策略：把所有段落按章節分配到整個影片時長，均等縮放
-        if fb_segs:
-            last_ts = fb_segs[-1]["start"]
-            if last_ts > 0:
-                scale = total_dur / (last_ts + 30)
-                for seg in fb_segs:
-                    seg["start"] = seg["start"] * scale
-                    seg["end"]   = seg["end"]   * scale
-            all_segments = fb_segs
-        else:
-            # 最後手段：把 merged_full 文字按字數均等切成句子，分配時間
-            sentences = [s.strip() for s in re.split(r"[。！？\n]+", fb_text) if len(s.strip()) > 5]
-            if sentences:
-                slot = total_dur / len(sentences)
-                for i, sent in enumerate(sentences):
-                    all_segments.append({
-                        "start": i * slot,
-                        "end":   (i + 1) * slot,
-                        "text":  sent[:80]
-                    })
-
-    # ── 依絕對時間排序 ──
-    all_segments.sort(key=lambda x: x["start"])
-
-    # ── 近鄰去重：移除與前一個段落起始時間差 < 1s 的重複段落 ──
-    deduped = []
-    prev_start = -999
-    for seg in all_segments:
-        if seg["start"] - prev_start >= 1.0:
-            deduped.append(seg)
-            prev_start = seg["start"]
-    all_segments = deduped
-
-    # ── 微調結束時間，確保不重疊 ──
-    for i in range(len(all_segments) - 1):
-        if all_segments[i]["end"] > all_segments[i+1]["start"]:
-            all_segments[i]["end"] = all_segments[i+1]["start"]
-        if all_segments[i]["end"] <= all_segments[i]["start"]:
-            all_segments[i]["end"] = all_segments[i]["start"] + 3.0
-    if all_segments:
-        if all_segments[-1]["end"] <= all_segments[-1]["start"]:
-            all_segments[-1]["end"] = all_segments[-1]["start"] + 3.0
-
-    log_workflow(f"Markdown Formatter: SRT 共 {len(all_segments)} 個字幕段落（已修正時間偏移）")
-
-    # 輸出 SRT
-    srt_lines = []
-    for s_idx, seg in enumerate(all_segments):
-        srt_lines.append(str(s_idx + 1))
-        srt_lines.append(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}")
-        srt_lines.append(seg["text"])
-        srt_lines.append("")
-    out_srt_file = os.path.join(processed_md_dir, f"{source_stem}.srt")
-    with open(out_srt_file, "w", encoding="utf-8-sig") as wf:
-        wf.write("\n".join(srt_lines))
-    log_workflow(f"Markdown Formatter: Saved SRT subtitle to {out_srt_file}")
-    
-    # 輸出 VTT
-    vtt_lines = ["WEBVTT", ""]
-    for s_idx, seg in enumerate(all_segments):
-        vtt_lines.append(str(s_idx + 1))
-        vtt_lines.append(f"{format_vtt_time(seg['start'])} --> {format_vtt_time(seg['end'])}")
-        vtt_lines.append(seg["text"])
-        vtt_lines.append("")
-    out_vtt_file = os.path.join(processed_md_dir, f"{source_stem}.vtt")
-    with open(out_vtt_file, "w", encoding="utf-8-sig") as wf:
-        wf.write("\n".join(vtt_lines))
-    log_workflow(f"Markdown Formatter: Saved VTT subtitle to {out_vtt_file}")
-    
-    # 輸出純文字 TXT
-    clean_txt = cleaned_text if cleaned_text else full_text
-    # 移除 Markdown 標題
-    clean_txt = re.sub(r"#+\s+.*?\n", "", clean_txt)
-    # 移除時間軸標記
-    clean_txt = re.sub(r"\[(?:(\d{1,2}):)?(\d{2}):(\d{2})\]", "", clean_txt)
-    # 整理空行
-    clean_txt = re.sub(r"\n\s*\n+", "\n\n", clean_txt).strip()
-    
-    out_txt_file = os.path.join(processed_md_dir, f"{source_stem}.txt")
-    with open(out_txt_file, "w", encoding="utf-8-sig") as wf:
-        wf.write(clean_txt)
-    log_workflow(f"Markdown Formatter: Saved pure TXT transcript to {out_txt_file}")
-    
-    # 6. 輸出 RAG 系統專用 JSON 索引
-    rag_index = {
-        "task_id": task_id,
-        "doc_id": task_id, # for Qdrant compatibility
-        "original_name": source_name,
-        "title": source_stem, # for Qdrant compatibility
-        "source_path": source_name, # for Qdrant compatibility
-        "processing_date": time.strftime("%Y-%m-%d %H:%M:%S"),
-        "duration_sec": media_info.get("duration_sec", 0),
-        "speculated_subject": spec_subject,
-        "inferred_subject": spec_subject, # for Qdrant compatibility
-        "indices": {
-            "articles": articles,
-            "interpretations": interpretations,
-            "cases": cases
-        },
-        "summary": summary_text,
-        "full_text_cleaned": clean_txt,
-        "cleaned_text": clean_txt, # for Qdrant compatibility
-        "segments": all_segments
-    }
-    
-    out_json_file = os.path.join(processed_md_dir, f"{source_stem}_index.json")
-    with ManifestManager(out_json_file) as mm:
-            mm.write(rag_index)
-    log_workflow(f"Markdown Formatter: Saved RAG JSON index to {out_json_file}")
-    
-    # 6.5. 自動備份檔案存回影片原始目錄
-    try:
-        source_path = manifest.get("source_path")
-        if source_path:
-            backup_dir = os.path.dirname(source_path)
-            if os.path.exists(backup_dir):
-                import shutil
-                for fpath in [out_md_file, out_srt_file, out_vtt_file, out_txt_file, out_json_file]:
-                    if os.path.exists(fpath):
-                        shutil.copy(fpath, backup_dir)
-                log_workflow(f"Markdown Formatter: 成功將所有產出檔案備份至影片原目錄: {backup_dir}")
-            else:
-                log_workflow(f"Markdown Formatter: 影片原目錄不存在，跳過備份: {backup_dir}", level="warning")
-    except Exception as e:
-        log_workflow(f"Markdown Formatter: 自動備份至影片原目錄失敗: {e}", level="warning")
-    
-    # 7. 寫入 ChromaDB RAG 資料庫
-    try:
-        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
-        from agent_core_pro import LocalLegalAgent
-        agent = LocalLegalAgent()
-        
-        # 寫入摘要
-        if summary_text:
-            safe_chroma_text = clean_txt[:150000]
-            doc_to_store = f"【自動吸收消化精華】\n{summary_text}\n\n【原始校對文本】\n{safe_chroma_text}"
-            doc_embedding = agent._get_embedding(doc_to_store)
-            if doc_embedding:
-                agent.intel_coll.add(
-                    ids=[f"auto_ref_{source_stem}_{int(time.time())}"],
-                    documents=[doc_to_store],
-                    embeddings=[doc_embedding],
-                    metadatas=[{
-                        "source": source_name,
-                        "mode": "背景長影音自動切片處理",
-                        "size_mb": round(os.path.getsize(full_txt_path) / (1024 * 1024), 2),
-                        "type": "summary",
-                        "class_name": spec_subject,
-                        "lesson_name": source_stem
-                    }]
-                )
-                log_workflow("Markdown Formatter: Successfully stored summary to ChromaDB.")
-
-        # 寫入時間軸分段 (RAG 段落索引)
-        if all_segments:
-            for g_idx in range(0, len(all_segments), 3):
-                group = all_segments[g_idx : g_idx + 3]
-                start_time = group[0]["start"]
-                end_time = group[-1]["end"]
-                
-                def format_ts(sec):
-                    m = int(sec // 60)
-                    s = int(sec % 60)
-                    return f"{m:02d}:{s:02d}"
-                
-                ts_range = f"{format_ts(start_time)} -> {format_ts(end_time)}"
-                chunk_text = "\n".join([seg["text"] for seg in group])
-                
-                doc_content = f"【教材影音片段 - {source_name}】\n時間軸：{ts_range}\n\n{chunk_text}"
-                doc_embedding = agent._get_embedding(doc_content)
+            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
+            from agent_core_pro import LocalLegalAgent
+            agent = LocalLegalAgent()
+        
+            # 寫入摘要
+            if summary_text:
+                safe_chroma_text = clean_txt[:150000]
+                doc_to_store = f"【自動吸收消化精華】\n{summary_text}\n\n【原始校對文本】\n{safe_chroma_text}"
+                doc_embedding = agent._get_embedding(doc_to_store)
                 if doc_embedding:
                     agent.intel_coll.add(
-                        ids=[f"chunk_audio_{source_stem}_{g_idx}_{int(time.time())}"],
-                        documents=[doc_content],
+                        ids=[f"auto_ref_{source_stem}_{int(time.time())}"],
+                        documents=[doc_to_store],
                         embeddings=[doc_embedding],
                         metadatas=[{
                             "source": source_name,
+                            "mode": "背景長影音自動切片處理",
+                            "size_mb": round(os.path.getsize(full_txt_path) / (1024 * 1024), 2),
+                            "type": "summary",
                             "class_name": spec_subject,
-                            "lesson_name": source_stem,
-                            "timestamp": ts_range,
-                            "type": "audio"
+                            "lesson_name": source_stem
                         }]
                     )
-            log_workflow(f"Markdown Formatter: Successfully stored audio segments to ChromaDB.")
-    except Exception as dbe:
-        log_error(f"Markdown Formatter: Failed to store to ChromaDB: {dbe}")
-        
-    # 8. 觸發 Qdrant 雙向量 RAG 資料庫寫入
-    try:
-        import subprocess
-        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
-        ingest_script = os.path.join(workspace_root, "src", "legal_rag", "ingest_documents.py")
-        deployed_script = "C:/LocalAI_Workstation/src/legal_rag/ingest_documents.py"
-        target_script = ingest_script if os.path.exists(ingest_script) else deployed_script
-        
-        if os.path.exists(target_script):
-            log_workflow(f"Markdown Formatter: Triggering Qdrant ingestion: {target_script}")
-            subprocess.Popen([sys.executable, target_script], cwd=os.path.dirname(target_script), creationflags=0x08000000)
-        else:
-            log_error(f"Markdown Formatter: Qdrant ingest script not found!")
-    except Exception as qe:
-        log_error(f"Markdown Formatter: Failed to trigger Qdrant ingestion: {qe}")
-
-    # ===== 執行 V5.1 Hard Gate 驗收標準 (檔案大小 vs 影片時長) =====
-    try:
-        duration_total_min = duration_min + duration_sec / 60.0
-        if duration_total_min > 5:  # 只針對 5 分鐘以上的課程進行驗證
-            srt_size_kb = os.path.getsize(out_txt_file) / 1024.0 if os.path.exists(out_txt_file) else 0
-            ratio = srt_size_kb / duration_total_min
-            
-            if ratio < 0.5:
-                log_error(f"Markdown Formatter: [Validation Failed] Transcript too short! {ratio:.2f} KB/min")
-                manifest["status"] = "failed_validation_too_short"
-                manifest["steps"]["formatter"] = "failed"
-                manifest["error"] = f"Validation failed: Transcript too short. Ratio: {ratio:.2f} KB/min (Duration: {duration_total_min:.1f} min, Size: {srt_size_kb:.1f} KB)"
-            elif ratio > 1.8:
-                log_error(f"Markdown Formatter: [Validation Failed] Transcript too long (Looping)! {ratio:.2f} KB/min")
-                manifest["status"] = "failed_validation_too_long"
-                manifest["steps"]["formatter"] = "failed"
-                manifest["error"] = f"Validation failed: Transcript too long. Ratio: {ratio:.2f} KB/min (Duration: {duration_total_min:.1f} min, Size: {srt_size_kb:.1f} KB)"
+                    log_workflow("Markdown Formatter: Successfully stored summary to ChromaDB.")
+
+            # 寫入時間軸分段 (RAG 段落索引)
+            if all_segments:
+                for g_idx in range(0, len(all_segments), 3):
+                    group = all_segments[g_idx : g_idx + 3]
+                    start_time = group[0]["start"]
+                    end_time = group[-1]["end"]
+                
+                    def format_ts(sec):
+                        m = int(sec // 60)
+                        s = int(sec % 60)
+                        return f"{m:02d}:{s:02d}"
+                
+                    ts_range = f"{format_ts(start_time)} -> {format_ts(end_time)}"
+                    chunk_text = "\n".join([seg["text"] for seg in group])
+                
+                    doc_content = f"【教材影音片段 - {source_name}】\n時間軸：{ts_range}\n\n{chunk_text}"
+                    doc_embedding = agent._get_embedding(doc_content)
+                    if doc_embedding:
+                        agent.intel_coll.add(
+                            ids=[f"chunk_audio_{source_stem}_{g_idx}_{int(time.time())}"],
+                            documents=[doc_content],
+                            embeddings=[doc_embedding],
+                            metadatas=[{
+                                "source": source_name,
+                                "class_name": spec_subject,
+                                "lesson_name": source_stem,
+                                "timestamp": ts_range,
+                                "type": "audio"
+                            }]
+                        )
+                log_workflow(f"Markdown Formatter: Successfully stored audio segments to ChromaDB.")
+        except Exception as dbe:
+            log_error(f"Markdown Formatter: Failed to store to ChromaDB: {dbe}")
+        
+        # 8. 觸發 Qdrant 雙向量 RAG 資料庫寫入
+        try:
+            import subprocess
+            workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
+            ingest_script = os.path.join(workspace_root, "src", "legal_rag", "ingest_documents.py")
+            deployed_script = "C:/LocalAI_Workstation/src/legal_rag/ingest_documents.py"
+            target_script = ingest_script if os.path.exists(ingest_script) else deployed_script
+        
+            if os.path.exists(target_script):
+                log_workflow(f"Markdown Formatter: Triggering Qdrant ingestion: {target_script}")
+                subprocess.Popen([sys.executable, target_script], cwd=os.path.dirname(target_script), creationflags=0x08000000)
             else:
-                log_workflow(f"Markdown Formatter: [Validation Passed] Healthy transcript ratio: {ratio:.2f} KB/min")
+                log_error(f"Markdown Formatter: Qdrant ingest script not found!")
+        except Exception as qe:
+            log_error(f"Markdown Formatter: Failed to trigger Qdrant ingestion: {qe}")
+
+        # ===== 執行 V5.1 Hard Gate 驗收標準 (檔案大小 vs 影片時長) =====
+        try:
+            duration_total_min = duration_min + duration_sec / 60.0
+            if duration_total_min > 5:  # 只針對 5 分鐘以上的課程進行驗證
+                srt_size_kb = os.path.getsize(out_txt_file) / 1024.0 if os.path.exists(out_txt_file) else 0
+                ratio = srt_size_kb / duration_total_min
+            
+                if ratio < 0.5:
+                    log_error(f"Markdown Formatter: [Validation Failed] Transcript too short! {ratio:.2f} KB/min")
+                    manifest["status"] = "failed_validation_too_short"
+                    manifest["steps"]["formatter"] = "failed"
+                    manifest["error"] = f"Validation failed: Transcript too short. Ratio: {ratio:.2f} KB/min (Duration: {duration_total_min:.1f} min, Size: {srt_size_kb:.1f} KB)"
+                elif ratio > 1.8:
+                    log_error(f"Markdown Formatter: [Validation Failed] Transcript too long (Looping)! {ratio:.2f} KB/min")
+                    manifest["status"] = "failed_validation_too_long"
+                    manifest["steps"]["formatter"] = "failed"
+                    manifest["error"] = f"Validation failed: Transcript too long. Ratio: {ratio:.2f} KB/min (Duration: {duration_total_min:.1f} min, Size: {srt_size_kb:.1f} KB)"
+                else:
+                    log_workflow(f"Markdown Formatter: [Validation Passed] Healthy transcript ratio: {ratio:.2f} KB/min")
+                    manifest["status"] = "completed"
+                    manifest["steps"]["formatter"] = "completed"
+            else:
+                # 課程太短，直接標記完成
                 manifest["status"] = "completed"
                 manifest["steps"]["formatter"] = "completed"
-        else:
-            # 課程太短，直接標記完成
+        except Exception as val_e:
+            log_error(f"Markdown Formatter: Validation logic error: {val_e}")
             manifest["status"] = "completed"
             manifest["steps"]["formatter"] = "completed"
-    except Exception as val_e:
-        log_error(f"Markdown Formatter: Validation logic error: {val_e}")
-        manifest["status"] = "completed"
-        manifest["steps"]["formatter"] = "completed"
-    # ==============================================================
-
-    manifest["output_markdown"] = out_md_file
-    manifest["output_srt"] = out_srt_file
-    manifest["output_vtt"] = out_vtt_file
-    manifest["output_txt"] = out_txt_file
-    manifest["output_json_index"] = out_json_file
-    
-    with ManifestManager(manifest_file) as mm:
+        # ==============================================================
+
+        manifest["output_markdown"] = out_md_file
+        manifest["output_srt"] = out_srt_file
+        manifest["output_vtt"] = out_vtt_file
+        manifest["output_txt"] = out_txt_file
+        manifest["output_json_index"] = out_json_file
+    
+        with ManifestManager(manifest_file) as mm:
+                mm.write(manifest)
+        
+        # 10. 蒸餾訓練資料採集（Whisper 原始 vs Gemini 精校 CoT 訓練對）
+        save_distillation_pair(task_id, source_name, spec_subject, full_text, cleaned_text, chunks)
+
+        # 11. 攔截並備份原始切片 (防止被系統無情刪除)
+        import shutil
+        try:
+            task_chunks_dir = f"A:/chunks/{task_id}"
+            if os.path.exists(task_chunks_dir):
+                target_drive = "F:/"
+                fallback_drive = "E:/"
+                backup_base = target_drive
+            
+                # 檢查 F 碟是否有超過 50GB 的剩餘空間
+                if os.path.exists(target_drive):
+                    free_bytes = shutil.disk_usage(target_drive).free
+                    if free_bytes < 50 * 1024 * 1024 * 1024:
+                        backup_base = fallback_drive
+            
+                final_backup_dir = os.path.join(backup_base, "chunks_backup", task_id)
+                os.makedirs(os.path.dirname(final_backup_dir), exist_ok=True)
+            
+                # 將整個資料夾搬移過去 (包含 .wav 與 .txt)
+                shutil.move(task_chunks_dir, final_backup_dir)
+                log_workflow(f"Markdown Formatter: 成功將原始切片搬移備份至 {final_backup_dir}")
+        except Exception as e:
+            log_error(f"Markdown Formatter: 備份切片失敗: {e}")
+
+        log_workflow(f"Markdown Formatter: Completed task {task_id}")
+        ok_flag = 1
+        return True
+        
+    except Exception as e:
+        log_error(f"Markdown Formatter: 發生嚴重崩潰: {str(e)}")
+        manifest["status"] = "failed"
+        manifest["steps"]["formatter"] = "failed"
+        manifest["error"] = f"Formatter crashed: {str(e)}"
+        with ManifestManager(manifest_file) as mm:
             mm.write(manifest)
-        
-    # 10. 蒸餾訓練資料採集（Whisper 原始 vs Gemini 精校 CoT 訓練對）
-    save_distillation_pair(task_id, source_name, spec_subject, full_text, cleaned_text, chunks)
-
-    # 11. 攔截並備份原始切片 (防止被系統無情刪除)
-    import shutil
-    try:
-        task_chunks_dir = f"A:/chunks/{task_id}"
-        if os.path.exists(task_chunks_dir):
-            target_drive = "F:/"
-            fallback_drive = "E:/"
-            backup_base = target_drive
-            
-            # 檢查 F 碟是否有超過 50GB 的剩餘空間
-            if os.path.exists(target_drive):
-                free_bytes = shutil.disk_usage(target_drive).free
-                if free_bytes < 50 * 1024 * 1024 * 1024:
-                    backup_base = fallback_drive
-            
-            final_backup_dir = os.path.join(backup_base, "chunks_backup", task_id)
-            os.makedirs(os.path.dirname(final_backup_dir), exist_ok=True)
-            
-            # 將整個資料夾搬移過去 (包含 .wav 與 .txt)
-            shutil.move(task_chunks_dir, final_backup_dir)
-            log_workflow(f"Markdown Formatter: 成功將原始切片搬移備份至 {final_backup_dir}")
-    except Exception as e:
-        log_error(f"Markdown Formatter: 備份切片失敗: {e}")
-
-    log_workflow(f"Markdown Formatter: Completed task {task_id}")
-    return True
+        return False
+        
+    finally:
+        elapsed = round(time_mod.time() - start_t, 1)
+        log_stage(task_id, "formatter", "OUT", ok=ok_flag, elapsed=elapsed)
 
 if __name__ == "__main__":
     parser = argparse.ArgumentParser()
`

## app_v6.py

這是一支全新建立或無法找到舊版備份的檔案，沒有 Before 狀態。

## app_v6_clean.py

這是一支全新建立或無法找到舊版備份的檔案，沒有 Before 狀態。

## progress_dashboard.py

`diff
--- Before (Golden Backup)
+++ After (Current Version)
@@ -1,4 +1,4 @@
-(from August 2nd/3rd Backup) ---
+(Current version) ---
 # [CRITICAL CROSS-FILE DEPENDENCY WARNING]
 # Upstream: kpi_monitor.py, User
 # Downstream: None
@@ -42,7 +42,6 @@
 from datetime import datetime, timedelta
 from pathlib import Path
 
-# [Block F] 終端機 Emoji 地雷拔除 (ASCII 化)
 # ── 嘗試載入 rich（彩色顯示），若無則降備純文字 ──
 try:
     from rich.console import Console
@@ -86,27 +85,34 @@
             # chunk 統計
             cm = str(mf).replace(".json","_chunks.json")
             n_chunks = done_chunks = 0
+            actual_dur = None
             if os.path.exists(cm):
-                chunks = None
-                for attempt in range(5):
-                    try:
-                        with open(cm, encoding="utf-8-sig") as f:
-                            chunks = json.load(f)
-                        if not isinstance(chunks, list):
-                            chunks = []
-                        break
-                    except (PermissionError, json.JSONDecodeError, OSError):
-                        time.sleep(0.2 * (attempt + 1))
-                    except Exception:
-                        chunks = []
-                        break
-
-                if chunks is not None:
-                    n_chunks = len(chunks)
-                    done_chunks = sum(
-                        1 for c in chunks
-                        if isinstance(c, dict) and c.get("status") == "completed"
-                    )
+                try:
+                    with open(cm, encoding="utf-8-sig") as f:
+                        chunks = json.load(f)
+                    n_chunks  = len(chunks)
+                    done_chunks = sum(1 for c in chunks if c.get("status")=="completed")
+                    if n_chunks > 0:
+                        last_chunk = chunks[-1]
+                        end_time = last_chunk.get("end_time")
+                        if end_time:
+                            # 處理字串格式如 "145:59" 或浮點數格式如 8759.399967
+                            if isinstance(end_time, (float, int)):
+                                actual_dur = f"~{int(end_time / 60)}min"
+                            else:
+                                parts = str(end_time).split(":")
+                                if len(parts) >= 2:
+                                    actual_dur = f"~{parts[0]}min"
+                                else:
+                                    actual_dur = str(end_time)
+                        else:
+                            import re
+                            fname = last_chunk.get("filename", "")
+                            m_match = re.search(r"_(\d+)[\-\:]\d+\.wav$", fname)
+                            if m_match:
+                                actual_dur = f"~{m_match.group(1)}min"
+                except Exception:
+                    pass
 
             # 跳過 mock（檢查 task_id 及課程名）
             raw_name = m.get("source_name","") or m.get("video_path","")
@@ -115,22 +121,22 @@
 
             # 流水線階段
             if status == "completed":
-                stage = "[OK] 完成"
+                stage = "✅ 完成"
             elif status == "failed":
-                stage = "[FAIL] 失敗"
+                stage = "❌ 失敗"
             elif steps.get("formatter") == "completed":
-                stage = "[OK] 完成"
+                stage = "✅ 完成"
                 status = "completed"
             elif steps.get("merge") == "completed":
-                stage = "[ACTIVE] Formatter"
+                stage = "🔄 Formatter"
             elif steps.get("stt") == "completed":
-                stage = "[ACTIVE] Merge"
+                stage = "🔄 Merge"
             elif done_chunks > 0:
-                stage = f"[STT] STT {done_chunks}/{n_chunks}"
+                stage = f"🎙️ STT {done_chunks}/{n_chunks}"
             elif n_chunks > 0:
-                stage = "[PENDING] STT 待開始"
+                stage = "⏳ STT 待開始"
             else:
-                stage = "[PREP] 預處理"
+                stage = "📂 預處理"
 
             tasks.append({
                 "task_id":     task_id,
@@ -142,6 +148,7 @@
                 "done_chunks": done_chunks,
                 "created":     created,
                 "completed":   completed,
+                "actual_dur":  actual_dur,
             })
         except Exception:
             pass
@@ -226,58 +233,8 @@
         f"[bold cyan]LexMind-Omni 處理進度儀表板[/]  [dim]{ts_str}[/]\n"
         f"[green]完成 {done}[/] / [yellow]進行中 {stt_act+merge_fmt}[/] / [dim]預處理 {preproc}[/] / 總計 {total}堂\n"
         f"實測速率：[bold yellow]{rate_str}[/]   ETA：[bold green]{eta_str}[/]",
-        title="[INFO] 進度總覽", border_style="bright_blue"
+        title="📊 進度總覽", border_style="bright_blue"
     ))
-
-    # ── 系統健康狀態 (Task 5: 活著但卡住 視圖) ──
-    try:
-        import subprocess as _sp, json as _js, os as _os
-        from pathlib import Path as _Path
-        _wf_res = _sp.run('wmic process get commandline', shell=True,
-                          capture_output=True, text=True, encoding='utf-8-sig', errors='ignore')
-        workflow_alive = 'run_workflow' in _wf_res.stdout
-
-        # 讀 kpi_monitor 快照取得停滯資訊
-        _kpi_state = _Path("C:/LocalAI_Workstation/config/kpi_state.json")
-        stagnant_cycles = 0
-        stalled_tasks_kpi = 0
-        if _kpi_state.exists():
-            _ks = _js.loads(_kpi_state.read_text(encoding="utf-8-sig", errors="replace"))
-            stagnant_cycles = _ks.get("stagnant_count", 0)
-
-        # 直接掃描 processing 超 15 分鐘的任務
-        import time as _t
-        _now_ts = _t.time()
-        _manifests = _Path("A:/manifests")
-        for _mf in _manifests.glob("task_*.json"):
-            if "_chunks" in _mf.name: continue
-            try:
-                _m = _js.loads(_mf.read_text(encoding="utf-8-sig", errors="replace"))
-                if _m.get("status") == "processing" and (_now_ts - _mf.stat().st_mtime) > 900:
-                    stalled_tasks_kpi += 1
-            except Exception: pass
-
-        if not workflow_alive:
-            health_color, health_icon, health_msg = "red", "[FAIL]", "Workflow Dead — 進程不存在！"
-        elif stalled_tasks_kpi > 0 or stagnant_cycles >= 2:
-            health_color = "yellow"
-            health_icon = "[WARN]"
-            parts = []
-            if stalled_tasks_kpi > 0:
-                parts.append(f"有 {stalled_tasks_kpi} 個任務卡住超過 15 分鐘")
-            if stagnant_cycles >= 2:
-                parts.append(f"最近 {stagnant_cycles} 輪 KPI 無新增 chunks (疑似產能停滯)")
-            health_msg = "Workflow 存活，但 " + "；".join(parts)
-        else:
-            health_color, health_icon, health_msg = "green", "[OK]", "Workflow 正常運作，無停滯"
-
-        console.print(Panel(
-            f"[bold {health_color}]{health_icon} {health_msg}[/]\n"
-            f"  Stalled tasks: [bold]{stalled_tasks_kpi}[/]   連續停滯輪數: [bold]{stagnant_cycles}[/]",
-            title="[HEALTH] 系統健康狀態", border_style=health_color
-        ))
-    except Exception as _he:
-        console.print(Panel(f"[dim]健康狀態讀取失敗: {_he}[/]", title="[HEALTH] 系統健康狀態", border_style="dim"))
 
     # ── 已完成任務表（含實際完成時間）──
     done_tasks = [t for t in tasks if t["status"] == "completed"]
@@ -295,9 +252,9 @@
     # 若數量少於 100，直接顯示「已完成課程 (共 X 堂)」
     # 若超過 100，才顯示「僅列出最近 100 堂，總計...」
     if display_count == done:
-        tbl_title = f"[OK] 已完成課程（共 {done} 堂）"
+        tbl_title = f"✅ 已完成課程（共 {done} 堂）"
     else:
-        tbl_title = f"[OK] 已完成課程（僅列出最近 {display_count} 堂，總計已完成 {done} 堂）"
+        tbl_title = f"✅ 已完成課程（僅列出最近 {display_count} 堂，總計已完成 {done} 堂）"
 
     tbl = Table(title=tbl_title, border_style="green", show_lines=True)
     tbl.add_column("完成時間",       style="dim",     width=17)
@@ -307,7 +264,10 @@
 
     for t, fmt_ts in sorted_done:
         ts_str2 = fmt_ts.strftime("%m-%d %H:%M:%S") if fmt_ts else "—"
-        dur = f"~{t['n_chunks']*12}min" if t["n_chunks"] else "純文字"
+        if t.get("actual_dur"):
+            dur = t["actual_dur"]
+        else:
+            dur = f"~{t['n_chunks']*12}min" if t["n_chunks"] else "純文字"
         tbl.add_row(ts_str2, t["name"][:38], str(t["n_chunks"]) if t["n_chunks"] else "TXT", dur)
 
     console.print(tbl)
@@ -315,13 +275,13 @@
     # ── 進行中任務表 ──
     active = [t for t in tasks if t["status"] not in ("completed","failed")]
     if active:
-        tbl2 = Table(title=f"[ACTIVE] 進行中任務（{len(active)} 個切片）",
+        tbl2 = Table(title=f"🔄 進行中任務（{len(active)} 個切片）",
                      border_style="yellow", show_lines=False)
         tbl2.add_column("階段",      style="bold", width=20)
         tbl2.add_column("課程名稱",  style="cyan", width=38)
         tbl2.add_column("進度",      style="green",width=12, justify="right")
 
-        stage_order = {"[ACTIVE] Formatter":0, "[ACTIVE] Merge":1, "[STT]":2, "[PENDING]":3, "[PREP]":4}
+        stage_order = {"🔄 Formatter":0, "🔄 Merge":1, "🎙️":2, "⏳":3, "📂":4}
         def sort_key(t):
             import sys
             import re
@@ -350,26 +310,24 @@
     # ── 即時切片狀態表 (Active Chunks) ──
     active_chunks = []
     for mf in MANIFESTS_DIR.glob("*_chunks.json"):
-        c_list = None
-        for attempt in range(5):
-            try:
-                with open(mf, encoding="utf-8-sig") as f:
-                    c_list = json.load(f)
-                break
-            except (PermissionError, json.JSONDecodeError, OSError):
-                time.sleep(0.2 * (attempt + 1))
-            except Exception:
-                c_list = []
-                break
-
-        if isinstance(c_list, list):
-            for c in c_list:
-                if isinstance(c, dict) and c.get("status") == "processing":
-                    started_at = c.get("started_at", time.time())
-                    active_chunks.append({"filename": c.get("filename"), "elapsed": time.time() - started_at})
+        try:
+            with open(mf, encoding="utf-8-sig") as f:
+                c_list = json.load(f)
+            
+            # 型別安全檢驗：確保資料結構為 List，防禦邊界情況
+            if isinstance(c_list, list):
+                for c in c_list:
+                    if isinstance(c, dict) and c.get("status") == "processing":
+                        started_at = c.get("started_at", time.time())
+                        active_chunks.append({"filename": c.get("filename"), "elapsed": time.time() - started_at})
+        except (PermissionError, json.JSONDecodeError):
+            # [EXPERT FIX] 攔截 Windows 讀取鎖衝突與覆寫瞬間的 JSON 解析錯誤
+            pass
+        except Exception:
+            pass
 
     if active_chunks:
-        tbl_chunks = Table(title=f"[CHUNKS] 即時處理中的切片 (共 {len(active_chunks)} 個)", border_style="bright_yellow")
+        tbl_chunks = Table(title=f"📡 即時處理中的切片 (共 {len(active_chunks)} 個)", border_style="bright_yellow")
         tbl_chunks.add_column("切片名稱", style="cyan")
         tbl_chunks.add_column("已執行時間", style="yellow", justify="right")
         for ac in active_chunks:
@@ -380,7 +338,7 @@
     # ── 吞吐量歷史（最近 10 個完成間隔）──
     sorted_fmt = sorted(fmt_events.items(), key=lambda x: x[1])
     if len(sorted_fmt) >= 3:
-        tbl3 = Table(title="[HEALTH] 最近完成速率記錄",
+        tbl3 = Table(title="⚡ 最近完成速率記錄",
                      border_style="blue", show_lines=False)
         tbl3.add_column("完成時間",   width=17, style="dim")
         tbl3.add_column("任務",       width=14, style="cyan")
@@ -409,7 +367,7 @@
                     t["n_chunks"], t["done_chunks"],
                     fmt_events.get(t["task_id"],"")
                 ])
-        console.print(f"\n[green][OK] 已匯出 CSV：{csv_path}[/]")
+        console.print(f"\n[green]✅ 已匯出 CSV：{csv_path}[/]")
 
 
 # ════════════════════════════════════════════
`

## sre_watchdog.py

`diff
--- Before (Golden Backup)
+++ After (Current Version)
@@ -1,4 +1,4 @@
-(from August 2nd/3rd Backup) ---
+(Current version) ---
 # [CRITICAL CROSS-FILE DEPENDENCY WARNING]
 # Upstream: System Scheduler
 # Downstream: auto_healer.py
@@ -29,7 +29,7 @@
     def check_workflow_alive():
         try:
             import subprocess
-            r = subprocess.run(["wmic","process","where","name=\"python.exe\" or name=\"pythonw.exe\"","get","ProcessId,CommandLine"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
+            r = subprocess.run(["wmic","process","where","name=\"python.exe\" or name=\"pythonw.exe\"","get","ProcessId,CommandLine"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30,creationflags=0x08000000)
             return "run_workflow" in r.stdout.lower().replace("\\","/")
         except Exception:
             return False
`

## kpi_monitor.py

`diff
--- Before (Golden Backup)
+++ After (Current Version)
@@ -1,4 +1,4 @@
-(from August 2nd/3rd Backup) ---
+(Current version) ---
 # [CRITICAL CROSS-FILE DEPENDENCY WARNING]
 # Upstream: kpi_runner.ps1
 # Downstream: None
@@ -60,7 +60,7 @@
 
 # ─── 路徑 ───────────────────────────────────────────────
 WORK_DIR    = Path("C:/LocalAI_Workstation")
-MANIFESTS   = Path("A:/manifests")
+MANIFESTS   = Path("A:/manifests_v6")
 LOG_PATH    = Path("A:/logs/workflow.log")
 KPI_STATE   = Path("A:/logs/kpi_state.json")   # 上次快照
 KPI_LOG     = Path("A:/logs/kpi_monitor.log")   # KPI 監控 log
@@ -209,7 +209,8 @@
              'name="python.exe" or name="pythonw.exe"',
              "get", "ProcessId,CommandLine"],
             capture_output=True, text=True,
-            encoding="utf-8", errors="replace", timeout=30
+            encoding="utf-8", errors="replace", timeout=30,
+            creationflags=0x08000000
         )
         return "run_workflow" in result.stdout.lower().replace("\\", "/")
     except Exception as e:
@@ -219,6 +220,15 @@
 
 def restart_workflow():
     log("[FIX] 重啟 run_workflow.py...")
+    
+    lock_file = MANIFESTS / "workflow.lock"
+    if lock_file.exists():
+        try:
+            lock_file.unlink()
+            log(f"[FIX] 已清理殘留鎖定檔 {lock_file}")
+        except Exception as e:
+            log(f"[WARN] 無法清理鎖定檔: {e}")
+
     # 【重要修復】將 timeout 放寬至 120 秒，避免 WMI 與 Start-Process 拖慢導致 kpi_monitor 崩潰
     subprocess.run(
         ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(RESTART_SCRIPT)],
@@ -300,7 +310,7 @@
     try:
         r = subprocess.run(
             ['wmic', 'process', 'where', 'name="pythonw.exe" or name="python.exe"', 'get', 'ProcessId,CommandLine'],
-            capture_output=True, text=True, encoding="utf-8-sig", errors="ignore"
+            capture_output=True, text=True, encoding="utf-8-sig", errors="ignore", creationflags=0x08000000
         )
         if r.stdout:
             lines = [l.strip() for l in r.stdout.splitlines() if l.strip() and "wmic" not in l]
`

