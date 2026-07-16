import os
import sys
import argparse
import json
import re
import time
from pathlib import Path
from workflow_helper import ensure_dirs, load_config, log_workflow, log_error

def interleave_blackboard_notes(transcript_text, clean_video_name, obsidian_dir):
    import glob
    pattern = os.path.join(obsidian_dir, f"校對_影音板書_{clean_video_name}_*.md")
    note_files = glob.glob(pattern)
    
    notes = []
    for f_path in note_files:
        filename = os.path.basename(f_path)
        parts = filename[:-3].split("_")
        if len(parts) >= 3:
            try:
                h = int(parts[-3])
                m = int(parts[-2])
                s = int(parts[-1])
                sec = h * 3600 + m * 60 + s
                
                with open(f_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                ts_str = f"{h:02d}_{m:02d}_{s:02d}"
                board_img = f"board_{clean_video_name}_{ts_str}.png"
                
                analysis_match = re.search(r"## 🧠 AI 智慧理解與知識庫演化註記\n(.*?)\n\n## 📊 可編輯之 Mermaid", content, re.DOTALL)
                analysis = analysis_match.group(1).strip() if analysis_match else ""
                
                mermaid_match = re.search(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
                mermaid = mermaid_match.group(1).strip() if mermaid_match else ""
                
                notes.append({
                    "sec": sec,
                    "hms": f"{h:02d}:{m:02d}:{s:02d}",
                    "image": board_img,
                    "analysis": analysis,
                    "mermaid": mermaid
                })
            except Exception as e:
                print(f"Error parsing note file {filename}: {e}")
                
    notes.sort(key=lambda x: x["sec"])
    if not notes:
        return transcript_text
        
    lines = transcript_text.split("\n")
    output_lines = []
    inserted_indices = set()
    
    for line in lines:
        ts_match = re.search(r"\[(?:(\d{1,2}):)?(\d{2}):(\d{2})\]", line)
        if ts_match:
            hr = int(ts_match.group(1)) if ts_match.group(1) else 0
            mn = int(ts_match.group(2))
            sc = int(ts_match.group(3))
            line_sec = hr * 3600 + mn * 60 + sc
            
            for idx, note in enumerate(notes):
                if idx not in inserted_indices and note["sec"] <= line_sec:
                    note_md = f"\n---\n📸 **【影片板書截圖 - 時間點 {note['hms']}】**\n![板書](../Obsidian_Vault/04_教材圖表校對/images/{note['image']})\n\n🧠 **【板書 AI 解讀與知識庫演化註記】**\n{note['analysis']}\n\n📊 **【板書 Mermaid 關係邏輯圖】**\n```mermaid\n{note['mermaid']}\n```\n---\n"
                    output_lines.append(note_md)
                    inserted_indices.add(idx)
                    
        output_lines.append(line)
        
    for idx, note in enumerate(notes):
        if idx not in inserted_indices:
            note_md = f"\n---\n📸 **【影片板書截圖 - 時間點 {note['hms']}】**\n![板書](../Obsidian_Vault/04_教材圖表校對/images/{note['image']})\n\n🧠 **【板書 AI 解讀與知識庫演化註記】**\n{note['analysis']}\n\n📊 **【板書 Mermaid 關係邏輯圖】**\n```mermaid\n{note['mermaid']}\n```\n---\n"
            output_lines.append(note_md)
            inserted_indices.add(idx)
            
    return "\n".join(output_lines)

def speculate_legal_subject(text):
    # 用分數權重猜測法律學科
    scores = {
        "民法": 0,
        "刑法": 0,
        "憲法": 0,
        "行政法": 0,
        "民事訴訟法": 0,
        "刑事訴訟法": 0
    }
    
    # 關鍵字對照表
    keywords = {
        "民法": ["民法", "契約", "意思表示", "不當得利", "無因管理", "侵權行為", "損害賠償", "物權", "債權", "抵押權", "繼承", "親屬", "消滅時效"],
        "刑法": ["刑法", "殺人", "傷害", "竊盜", "搶奪", "強盜", "詐欺", "背信", "故意", "過失", "阻卻違法", "正當防衛", "緊急避難", "有期徒刑"],
        "憲法": ["憲法", "基本權", "言論自由", "生存權", "平等權", "釋字", "大法官", "憲法法庭", "違憲", "合憲", "權力分立"],
        "行政法": ["行政法", "行政程序法", "行政處分", "訴願", "行政訴訟", "國家賠償", "行政罰", "公務員", "行政裁量"],
        "民事訴訟法": ["民事訴訟", "民訴", "起訴", "管轄", "訴訟標的", "訴之聲明", "當事人", "既判力", "執行力", "假扣押", "保全程序"],
        "刑事訴訟法": ["刑事訴訟", "刑訴", "羈押", "搜索", "扣押", "逮捕", "告訴", "不起訴", "公訴", "自訴", "自白", "傳聞法則", "證據能力"]
    }
    
    for subject, words in keywords.items():
        for word in words:
            matches = len(re.findall(re.escape(word), text))
            if matches > 0:
                scores[subject] += matches * (5 if word == subject else 1)
                
    best_subject = max(scores, key=scores.get)
    if scores[best_subject] == 0:
        return "通用/未分類"
    return best_subject

def extract_legal_indices(text):
    articles = set(re.findall(r"([一-龥]*法第[一二三四五六七八九十百千\d]+條(?:之[一二三四五六七八九十\d]+)?)", text))
    interpretations = set(re.findall(r"(釋字第[一二三四五六七八九十百千\d]+號)", text))
    case_pattern = r"(最高法院\s*\d+\s*年度?\s*[一-龥]+\s*字\s*第\s*\d+\s*號(?:\s*民事|\s*刑事)?判決)"
    cases = set(re.findall(case_pattern, text))
    
    return sorted(list(articles)), sorted(list(interpretations)), sorted(list(cases))

def parse_timestamp_to_seconds(m_match):
    hr = int(m_match.group(1)) if m_match.group(1) else 0
    mn = int(m_match.group(2))
    sc = int(m_match.group(3))
    return hr * 3600 + mn * 60 + sc

def parse_transcript_into_timed_segments(text, chunk_start_time):
    pattern = r"\[(?:(\d{1,2}):)?(\d{2}):(\d{2})\]"
    matches = list(re.finditer(pattern, text))
    
    segments = []
    if not matches:
        return [{"start": chunk_start_time, "text": text}]
        
    for i in range(len(matches)):
        m = matches[i]
        start_sec = parse_timestamp_to_seconds(m) + chunk_start_time
        
        start_idx = m.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
        seg_text = text[start_idx:end_idx].strip()
        
        # 清除段落中的 Markdown 標頭標記
        seg_text = re.sub(r"^#+\s+", "", seg_text)
        seg_text = re.sub(r"\s+", " ", seg_text)
        
        if seg_text:
            segments.append({
                "start": start_sec,
                "text": seg_text
            })
            
    for i in range(len(segments) - 1):
        segments[i]["end"] = segments[i+1]["start"]
    if segments:
        segments[-1]["end"] = segments[-1]["start"] + 10.0
        
    return segments

def format_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def format_vtt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def format_markdown(task_id):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    processed_md_dir = paths["processed_md_dir"]
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
        
    media_info = manifest.get("media_info", {})
    source_name = manifest["source_name"]
    source_stem = Path(source_name).stem
    
    full_txt_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
    cleaned_txt_path = os.path.join(task_chunks_dir, "merged_cleaned_transcript.txt")
    summary_path = os.path.join(task_chunks_dir, "merged_summary.txt")
    
    if not os.path.exists(full_txt_path):
        log_error(f"Merged transcript missing at {full_txt_path}")
        return False
        
    with open(full_txt_path, "r", encoding="utf-8") as f:
        full_text = f.read()
        
    cleaned_text = ""
    if os.path.exists(cleaned_txt_path):
        with open(cleaned_txt_path, "r", encoding="utf-8") as f:
            cleaned_text = f.read()
            
    summary_text = ""
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_text = f.read()
            
    log_workflow("Markdown Formatter: Speculating legal subject and extracting index terms...")
    spec_subject = speculate_legal_subject(full_text)
    articles, interpretations, cases = extract_legal_indices(full_text)
    
    highlighted_summary = summary_text
    keywords_highlight = ["爭點", "重點整理", "必考", "結論", "實務見解"]
    for kw in keywords_highlight:
        highlighted_summary = re.sub(f"({kw})", r"**【\1】**", highlighted_summary)
        
    duration_min = int(media_info.get("duration_sec", 0) // 60)
    duration_sec = int(media_info.get("duration_sec", 0) % 60)
    
    # 執行影片板書追蹤並整合至逐字稿
    cleaned_with_notes = cleaned_text if cleaned_text else full_text
    
    if manifest.get("source_path", "").lower().endswith(".mp4"):
        try:
            from visual_analyzer import VisualLegalAnalyzer
            analyzer = VisualLegalAnalyzer()
            parts = source_name.split("_")
            class_name = parts[0] if len(parts) > 1 else "法律實務"
            lesson_name = parts[1] if len(parts) > 2 else "第一堂"
            
            video_path = manifest["source_path"]
            if os.path.exists(video_path):
                log_workflow(f"Markdown Formatter: Auto-tracking blackboard for video {source_name}...")
                analyzer.track_video_blackboard(video_path, class_name, lesson_name)
                
                # 進行板書與逐字稿的時間軸交叉插補
                clean_video_name = analyzer._sanitize_filename(source_stem)
                cleaned_with_notes = interleave_blackboard_notes(cleaned_with_notes, clean_video_name, str(analyzer.obsidian_dir))
            else:
                log_error(f"Markdown Formatter: Original video not found for blackboard tracking: {video_path}")
        except Exception as vae:
            log_error(f"Markdown Formatter: Failed to run blackboard tracking or interleave notes: {vae}")
            
    # 組合 Markdown 內容
    md_content = f"""# 臺灣法律教材研讀：{source_stem}

## 📊 檔案元數據 (Metadata)
- **原始檔名**：{source_name}
- **分析日期**：{time.strftime("%Y-%m-%d %H:%M:%S")}
- **教材學科**：{spec_subject}
- **教材時長**：{duration_min} 分 {duration_sec} 秒
- **總切片數**：{manifest.get("chunks_count", 1)} 片
- **語言語系**：繁體中文 (台灣常規法律實務)

## ⚖️ 關聯法規與實務見解索引
- **法規條文**：{", ".join(articles) if articles else "未偵測到明確條文"}
- **司法釋字**：{", ".join(interpretations) if interpretations else "未偵測到明確釋字"}
- **實務判決**：{", ".join(cases) if cases else "未偵測到明確裁判字號"}

---

## 🧠 智慧教材法理消化 (RAG 摘要)
{highlighted_summary}

---

## 🎙️ 去冗餘精校逐字稿 (Cleaned Transcript)
{cleaned_with_notes}
"""

    out_md_file = os.path.join(processed_md_dir, f"{source_stem}.md")
    with open(out_md_file, "w", encoding="utf-8") as wf:
        wf.write(md_content)
    log_workflow(f"Markdown Formatter: Saved final Markdown file to {out_md_file}")
    
    # 5. 時間軸字幕段落解析與重疊去重
    log_workflow("Markdown Formatter: Parsing time-aligned segments for SRT, VTT, and TXT...")
    all_segments = []
    
    for idx, chunk in enumerate(chunks):
        chunk_path = chunk["path"]
        stem = Path(chunk_path).stem
        chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
        
        if not os.path.exists(chunk_txt_file):
            continue
            
        with open(chunk_txt_file, "r", encoding="utf-8") as rf:
            chunk_content = rf.read().strip()
            
        chunk_start = chunk["start_time"]
        chunk_end = chunk["end_time"]
        
        # 決定此分片的有效時間區間，以重疊處的中間點為界去重
        # 例如：前後重疊 30 秒，則前分片結束前 15 秒與後分片開始後 15 秒不納入
        window_start = chunk_start + 15.0 if idx > 0 else 0.0
        window_end = chunk_end - 15.0 if idx < len(chunks) - 1 else chunk_end
        
        chunk_segs = parse_transcript_into_timed_segments(chunk_content, chunk_start)
        for seg in chunk_segs:
            if window_start <= seg["start"] <= window_end:
                all_segments.append(seg)
                
    # 依時間排序並微調結束時間
    all_segments.sort(key=lambda x: x["start"])
    for i in range(len(all_segments) - 1):
        if all_segments[i]["end"] > all_segments[i+1]["start"]:
            all_segments[i]["end"] = all_segments[i+1]["start"]
        if all_segments[i]["end"] <= all_segments[i]["start"]:
            all_segments[i]["end"] = all_segments[i]["start"] + 2.0
            
    # 輸出 SRT
    srt_lines = []
    for s_idx, seg in enumerate(all_segments):
        srt_lines.append(str(s_idx + 1))
        srt_lines.append(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}")
        srt_lines.append(seg["text"])
        srt_lines.append("")
    out_srt_file = os.path.join(processed_md_dir, f"{source_stem}.srt")
    with open(out_srt_file, "w", encoding="utf-8") as wf:
        wf.write("\n".join(srt_lines))
    log_workflow(f"Markdown Formatter: Saved SRT subtitle to {out_srt_file}")
    
    # 輸出 VTT
    vtt_lines = ["WEBVTT", ""]
    for s_idx, seg in enumerate(all_segments):
        vtt_lines.append(str(s_idx + 1))
        vtt_lines.append(f"{format_vtt_time(seg['start'])} --> {format_vtt_time(seg['end'])}")
        vtt_lines.append(seg["text"])
        vtt_lines.append("")
    out_vtt_file = os.path.join(processed_md_dir, f"{source_stem}.vtt")
    with open(out_vtt_file, "w", encoding="utf-8") as wf:
        wf.write("\n".join(vtt_lines))
    log_workflow(f"Markdown Formatter: Saved VTT subtitle to {out_vtt_file}")
    
    # 輸出純文字 TXT
    clean_txt = cleaned_text if cleaned_text else full_text
    # 移除 Markdown 標題
    clean_txt = re.sub(r"#+\s+.*?\n", "", clean_txt)
    # 移除時間軸標記
    clean_txt = re.sub(r"\[(?:(\d{1,2}):)?(\d{2}):(\d{2})\]", "", clean_txt)
    # 整理空行
    clean_txt = re.sub(r"\n\s*\n+", "\n\n", clean_txt).strip()
    
    out_txt_file = os.path.join(processed_md_dir, f"{source_stem}.txt")
    with open(out_txt_file, "w", encoding="utf-8") as wf:
        wf.write(clean_txt)
    log_workflow(f"Markdown Formatter: Saved pure TXT transcript to {out_txt_file}")
    
    # 6. 輸出 RAG 系統專用 JSON 索引
    rag_index = {
        "task_id": task_id,
        "doc_id": task_id, # for Qdrant compatibility
        "original_name": source_name,
        "title": source_stem, # for Qdrant compatibility
        "source_path": source_name, # for Qdrant compatibility
        "processing_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_sec": media_info.get("duration_sec", 0),
        "speculated_subject": spec_subject,
        "inferred_subject": spec_subject, # for Qdrant compatibility
        "indices": {
            "articles": articles,
            "interpretations": interpretations,
            "cases": cases
        },
        "summary": summary_text,
        "full_text_cleaned": clean_txt,
        "cleaned_text": clean_txt, # for Qdrant compatibility
        "segments": all_segments
    }
    
    out_json_file = os.path.join(processed_md_dir, f"{source_stem}_index.json")
    with open(out_json_file, "w", encoding="utf-8") as wf:
        json.dump(rag_index, wf, ensure_ascii=False, indent=2)
    log_workflow(f"Markdown Formatter: Saved RAG JSON index to {out_json_file}")
    
    # 7. 寫入 ChromaDB RAG 資料庫
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from agent_core_pro import LocalLegalAgent
        agent = LocalLegalAgent()
        
        # 寫入摘要
        if summary_text:
            safe_chroma_text = clean_txt[:150000]
            doc_to_store = f"【自動吸收消化精華】\n{summary_text}\n\n【原始校對文本】\n{safe_chroma_text}"
            doc_embedding = agent._get_embedding(doc_to_store)
            if doc_embedding:
                agent.intel_coll.add(
                    ids=[f"auto_ref_{source_stem}_{int(time.time())}"],
                    documents=[doc_to_store],
                    embeddings=[doc_embedding],
                    metadatas=[{
                        "source": source_name,
                        "mode": "背景長影音自動切片處理",
                        "size_mb": round(os.path.getsize(full_txt_path) / (1024 * 1024), 2),
                        "type": "summary",
                        "class_name": spec_subject,
                        "lesson_name": source_stem
                    }]
                )
                log_workflow("Markdown Formatter: Successfully stored summary to ChromaDB.")

        # 寫入時間軸分段 (RAG 段落索引)
        if all_segments:
            for g_idx in range(0, len(all_segments), 3):
                group = all_segments[g_idx : g_idx + 3]
                start_time = group[0]["start"]
                end_time = group[-1]["end"]
                
                def format_ts(sec):
                    m = int(sec // 60)
                    s = int(sec % 60)
                    return f"{m:02d}:{s:02d}"
                
                ts_range = f"{format_ts(start_time)} -> {format_ts(end_time)}"
                chunk_text = "\n".join([seg["text"] for seg in group])
                
                doc_content = f"【教材影音片段 - {source_name}】\n時間軸：{ts_range}\n\n{chunk_text}"
                doc_embedding = agent._get_embedding(doc_content)
                if doc_embedding:
                    agent.intel_coll.add(
                        ids=[f"chunk_audio_{source_stem}_{g_idx}_{int(time.time())}"],
                        documents=[doc_content],
                        embeddings=[doc_embedding],
                        metadatas=[{
                            "source": source_name,
                            "class_name": spec_subject,
                            "lesson_name": source_stem,
                            "timestamp": ts_range,
                            "type": "audio"
                        }]
                    )
            log_workflow(f"Markdown Formatter: Successfully stored audio segments to ChromaDB.")
    except Exception as dbe:
        log_error(f"Markdown Formatter: Failed to store to ChromaDB: {dbe}")
        
    # 8. 觸發 Qdrant 雙向量 RAG 資料庫寫入
    try:
        import subprocess
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ingest_script = os.path.join(workspace_root, "src", "legal_rag", "ingest_documents.py")
        deployed_script = "C:/LocalAI_Workstation/src/legal_rag/ingest_documents.py"
        target_script = ingest_script if os.path.exists(ingest_script) else deployed_script
        
        if os.path.exists(target_script):
            log_workflow(f"Markdown Formatter: Triggering Qdrant ingestion: {target_script}")
            subprocess.Popen([sys.executable, target_script], cwd=os.path.dirname(target_script))
        else:
            log_error(f"Markdown Formatter: Qdrant ingest script not found!")
    except Exception as qe:
        log_error(f"Markdown Formatter: Failed to trigger Qdrant ingestion: {qe}")

    # 更新任務 Manifest
    manifest["steps"]["formatter"] = "completed"
    manifest["status"] = "completed"
    manifest["output_markdown"] = out_md_file
    manifest["output_srt"] = out_srt_file
    manifest["output_vtt"] = out_vtt_file
    manifest["output_txt"] = out_txt_file
    manifest["output_json_index"] = out_json_file
    
    with open(manifest_file, "w", encoding="utf-8") as wf:
        json.dump(manifest, wf, ensure_ascii=False, indent=2)
        
    log_workflow(f"Markdown Formatter: Completed task {task_id}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True, help="Task ID to process")
    args = parser.parse_args()
    format_markdown(args.task_id)
