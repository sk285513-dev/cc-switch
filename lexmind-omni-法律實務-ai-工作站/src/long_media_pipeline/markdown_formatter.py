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
        ingest_script = "C:/LocalAI_Workstation/src/legal_rag/ingest_documents.py"
        if os.path.exists(ingest_script):
            logging.info(f"Auto-triggering ingestion into Qdrant: {ingest_script}")
            subprocess.Popen([sys.executable, ingest_script])
    except Exception as e:
        logging.error(f"Failed to auto-trigger ingestion: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python markdown_formatter.py {task_id}")
        sys.exit(1)
    format_markdown(sys.argv[1])
