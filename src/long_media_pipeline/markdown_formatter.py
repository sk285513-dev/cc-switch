import os
import sys
import json
import logging
import yaml
import time
import re

def infer_legal_subject(text):
    scores = {
        "憲法": len(re.findall(r"(憲法|釋字|基本權|違憲|合憲|權力分立|大法官|憲法法庭)", text)),
        "民法": len(re.findall(r"(民法|侵權|不當得利|契約|物權|債權|消滅時效|借名登記|意思表示)", text)),
        "刑法": len(re.findall(r"(刑法|犯罪|構成要件|違法性|有責性|故意|過失|殺人|竊盜|強盜|阻卻違法)", text)),
        "行政法": len(re.findall(r"(行政法|行政程序法|行政處分|公法|訴願|行政訴訟|國家賠償)", text)),
        "民訴": len(re.findall(r"(民事訴訟|起訴|管轄|訴訟標的|當事人|爭點整理|民訴)", text)),
        "刑訴": len(re.findall(r"(刑事訴訟|羈押|搜索|傳喚|公訴|自訴|刑訴|告發|告訴)", text))
    }
    
    # Return the one with highest score, fallback to 民法
    best_subject = max(scores, key=scores.get)
    if scores[best_subject] == 0:
        return "民法" # Default fallback
    return best_subject

def extract_laws(text):
    # Match patterns like 民法第184條, 刑法第二十七條, 行政程序法第一百三十一條, etc.
    pattern = r"((?:民法|刑法|行政程序法|勞動基準法|民事訴訟法|刑事訴訟法)第[一二三四五六七八九十百零\d\s]+條)"
    matches = re.findall(pattern, text)
    # Deduplicate and return list
    return sorted(list(set(matches)))

def extract_precedents(text):
    # Match patterns like 釋字第474號, 109年度台上字第123號
    interpretations = re.findall(r"(釋字第\d+號)", text)
    judgments = re.findall(r"(\d+年度(?:台上|台抗|建上|上|訴|字)第\d+號)", text)
    
    precedents = list(set(interpretations + judgments))
    return sorted(precedents)

def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}小時{m}分{s}秒"
    return f"{m}分{s}秒"

def format_markdown(task_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    manifests_dir = config['paths']['manifests_dir']
    processed_md_dir = config['paths']['processed_md_dir']
    workflow_log = config['logging']['workflow_log']
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(workflow_log, encoding='utf-8')
        ]
    )
    
    logging.info(f"--- Markdown Formatting Task {task_id} ---")
    manifest_path = os.path.join(manifests_dir, f"{task_id}.json")
    if not os.path.exists(manifest_path):
        logging.error(f"Manifest not found for task {task_id}")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    merged_paths = manifest.get('merged_paths', {})
    full_path = merged_paths.get('full')
    cleaned_path = merged_paths.get('cleaned')
    summary_path = merged_paths.get('summary')
    
    if not full_path or not os.path.exists(full_path):
        logging.error("Merged transcript files missing!")
        return
        
    # Read files
    with open(full_path, 'r', encoding='utf-8') as f:
        full_text = f.read()
    with open(cleaned_path, 'r', encoding='utf-8') as f:
        cleaned_text = f.read()
    with open(summary_path, 'r', encoding='utf-8') as f:
        summary_text = f.read()
        
    # Infer metadata
    duration_sec = manifest['media_info']['duration']
    subject = infer_legal_subject(full_text)
    laws = extract_laws(full_text)
    precedents = extract_precedents(full_text)
    
    # Make safe file name
    base_source_name = os.path.splitext(manifest['filename'])[0]
    safe_base_name = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in base_source_name])
    
    os.makedirs(processed_md_dir, exist_ok=True)
    md_output_path = os.path.join(processed_md_dir, f"{safe_base_name}.md")
    json_output_path = os.path.join(processed_md_dir, f"{safe_base_name}.json")
    
    # Write Markdown file
    md_content = f"""---
title: "{manifest['filename']}"
task_id: "{task_id}"
date: "{time.strftime('%Y-%m-%d')}"
duration: "{format_duration(duration_sec)}"
chunks_count: {len(manifest['chunks'])}
language: "繁體中文"
inferred_subject: "{subject}"
key_laws: {json.dumps(laws, ensure_ascii=False)}
key_precedents: {json.dumps(precedents, ensure_ascii=False)}
---

# 法律課程逐字稿報告：{base_source_name}

## 📊 檔案基本資訊
- **原始檔名**：{manifest['filename']}
- **處理日期**：{time.strftime('%Y-%m-%d %H:%M:%S')}
- **總時長**：{format_duration(duration_sec)}
- **切片段數**：{len(manifest['chunks'])} 段
- **法律科目**：{subject}

## ⚖️ 關鍵法條索引
{", ".join([f"`{law}`" for law in laws]) if laws else "（無偵測到法條或法規）"}

## 判決與釋字索引
{", ".join([f"`{prec}`" for prec in precedents]) if precedents else "（無偵測到判例、釋字或裁定）"}

---

## 📌 課程大綱與章節摘要
{summary_text}

---

## 📝 完整整理後逐字稿 (去冗餘版)
{cleaned_text}
"""
    
    with open(md_output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    # Write JSON file
    index_data = {
        "doc_id": task_id,
        "title": base_source_name,
        "source_path": manifest['original_file'],
        "duration": duration_sec,
        "inferred_subject": subject,
        "laws": laws,
        "precedents": precedents,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary_text,
        "full_text": full_text,
        "cleaned_text": cleaned_text
    }
    
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
        
    logging.info(f"Final Markdown exported to: {md_output_path}")
    logging.info(f"Final JSON index exported to: {json_output_path}")
    
    # 7. 寫入 ChromaDB RAG 資料庫
    try:
        # Resolve script path to import agent_core_pro
        parent_dir = os.path.dirname(script_dir) # src/
        workspace_root = os.path.dirname(parent_dir)
        scripts_path = os.path.join(workspace_root, "scripts")
        if scripts_path not in sys.path:
            sys.path.append(scripts_path)
            
        from agent_core_pro import LocalLegalAgent
        agent = LocalLegalAgent()
        
        # 寫入摘要
        if summary_text:
            safe_chroma_text = full_text[:150000]
            doc_to_store = f"【自動吸收消化精華】\n{summary_text}\n\n【原始校對文本】\n{safe_chroma_text}"
            doc_embedding = agent._get_embedding(doc_to_store)
            if doc_embedding:
                agent.intel_coll.add(
                    ids=[f"auto_ref_{safe_base_name}_{int(time.time())}"],
                    documents=[doc_to_store],
                    embeddings=[doc_embedding],
                    metadatas=[{
                        "source": manifest['filename'],
                        "mode": "背景長影音自動切片處理",
                        "size_mb": round(os.path.getsize(full_path) / (1024 * 1024), 2),
                        "type": "summary",
                        "class_name": subject,
                        "lesson_name": safe_base_name
                    }]
                )
                logging.info("Successfully stored summary to ChromaDB.")

        # 寫入時間軸分段 (Read all_segments from chunks)
        all_segments = []
        chunks_manifest_file = os.path.join(manifests_dir, f"{task_id}_chunks.json")
        if os.path.exists(chunks_manifest_file):
            with open(chunks_manifest_file, "r", encoding="utf-8") as cf:
                chunks = json.load(cf)
            
            task_chunks_dir = os.path.join(config['paths']['chunks_dir'], task_id)
            
            # Helper to parse transcript into timed segments
            def parse_transcript_into_timed_segments(text, chunk_start_time):
                pattern = r"\[(?:(\d{1,2}):)?(\d{2}):(\d{2})\]"
                matches = list(re.finditer(pattern, text))
                segments = []
                if not matches:
                    return [{"start": chunk_start_time, "end": chunk_start_time + 10.0, "text": text}]
                for i in range(len(matches)):
                    m = matches[i]
                    hr = int(m.group(1)) if m.group(1) else 0
                    mn = int(m.group(2))
                    sc = int(m.group(3))
                    start_sec = hr * 3600 + mn * 60 + sc + chunk_start_time
                    start_idx = m.end()
                    end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
                    seg_text = text[start_idx:end_idx].strip()
                    seg_text = re.sub(r"^#+\s+", "", seg_text)
                    seg_text = re.sub(r"\s+", " ", seg_text)
                    if seg_text:
                        segments.append({"start": start_sec, "text": seg_text})
                for i in range(len(segments) - 1):
                    segments[i]["end"] = segments[i+1]["start"]
                if segments:
                    segments[-1]["end"] = segments[-1]["start"] + 10.0
                return segments

            for idx, chunk in enumerate(chunks):
                chunk_path = chunk["path"]
                stem = Path(chunk_path).stem
                chunk_txt_file = os.path.join(task_chunks_dir, f"{stem}.txt")
                if os.path.exists(chunk_txt_file):
                    with open(chunk_txt_file, "r", encoding="utf-8") as rf:
                        chunk_content = rf.read().strip()
                    chunk_start = chunk["start_time"]
                    chunk_end = chunk["end_time"]
                    window_start = chunk_start + 15.0 if idx > 0 else 0.0
                    window_end = chunk_end - 15.0 if idx < len(chunks) - 1 else chunk_end
                    chunk_segs = parse_transcript_into_timed_segments(chunk_content, chunk_start)
                    for seg in chunk_segs:
                        if window_start <= seg["start"] <= window_end:
                            all_segments.append(seg)
                            
            all_segments.sort(key=lambda x: x["start"])
            for i in range(len(all_segments) - 1):
                if all_segments[i]["end"] > all_segments[i+1]["start"]:
                    all_segments[i]["end"] = all_segments[i+1]["start"]
                if all_segments[i]["end"] <= all_segments[i]["start"]:
                    all_segments[i]["end"] = all_segments[i]["start"] + 2.0

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
                
                doc_content = f"【教材影音片段 - {manifest['filename']}】\n時間軸：{ts_range}\n\n{chunk_text}"
                doc_embedding = agent._get_embedding(doc_content)
                if doc_embedding:
                    agent.intel_coll.add(
                        ids=[f"chunk_audio_{safe_base_name}_{g_idx}_{int(time.time())}"],
                        documents=[doc_content],
                        embeddings=[doc_embedding],
                        metadatas=[{
                            "source": manifest['filename'],
                            "class_name": subject,
                            "lesson_name": safe_base_name,
                            "timestamp": ts_range,
                            "type": "audio"
                        }]
                    )
            logging.info("Successfully stored audio segments to ChromaDB.")
    except Exception as dbe:
        logging.error(f"Failed to store to ChromaDB: {dbe}")

    # Update manifest to completed
    manifest['status'] = 'completed'
    manifest['steps']['markdown'] = 'completed'
    manifest['final_outputs'] = {
        "markdown": md_output_path,
        "json": json_output_path
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        
    logging.info(f"★ Workflow fully completed successfully for task {task_id}! ★")
    
    # Auto-trigger ingestion into Qdrant
    try:
        import subprocess
        parent_dir = os.path.dirname(script_dir) # src/
        workspace_root = os.path.dirname(parent_dir)
        ingest_script = os.path.join(workspace_root, "src", "legal_rag", "ingest_documents.py")
        deployed_script = "C:/LocalAI_Workstation/src/legal_rag/ingest_documents.py"
        target_script = ingest_script if os.path.exists(ingest_script) else deployed_script
        
        if os.path.exists(target_script):
            logging.info(f"Auto-triggering ingestion into Qdrant: {target_script}")
            subprocess.Popen([sys.executable, target_script], cwd=os.path.dirname(target_script))
        else:
            logging.error(f"Qdrant ingest script not found!")
    except Exception as e:
        logging.error(f"Failed to auto-trigger ingestion: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python markdown_formatter.py {task_id}")
        sys.exit(1)
    format_markdown(sys.argv[1])
