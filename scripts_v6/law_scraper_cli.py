# C:/LocalAI_Workstation/scripts/law_scraper_cli.py
# -*- coding: utf-8 -*-
import os
import json
import time
import datetime
import requests
from bs4 import BeautifulSoup

WORK_DIR = "C:/LocalAI_Workstation"
STATUS_FILE = os.path.join(WORK_DIR, "scraper_status.json")

def update_status(status, progress, message):
    """即時更新狀態 JSON 檔案，讓 Streamlit UI 能跨進程讀取進度"""
    data = {
        "status": status,
        "progress": progress,
        "message": message,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        os.makedirs(WORK_DIR, exist_ok=True)
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to update status file: {e}")

def save_to_obsidian(q_id, year, subject, title, options, ans, exp):
    clean_year = year.replace("/", "_").replace("\\", "_")
    clean_subject = subject.replace("/", "_").replace("\\", "_")
    folder_path = os.path.join(WORK_DIR, "Obsidian_Vault", "04_考古題庫", f"{clean_year}_{clean_subject}")
    os.makedirs(folder_path, exist_ok=True)
    
    options_md = "\n".join([f"- {opt}" for opt in options]) if options else "- 本題無獨立選項文本（請參閱題幹）。"
    md_content = f"""# 司律一試考題 - {year} {subject} [ID: {q_id}]

### ⚖️ 題幹本文
{title}

### 選擇題選項
{options_md}

### 標準答案
**【 {ans} 】**

### 詳解與法規核心關聯
{exp}

---
*本筆記由 LexMind-Omni 工作站外網排程自動抓取更新*
"""
    file_name = os.path.join(folder_path, f"Q_{q_id}.md")
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception as e:
        print(f"Failed to write Obsidian file: {e}")

import re

LAW_KEYWORDS = ["法律", "法規", "法庭", "訴訟", "案情", "教材", "民法", "刑法", "行政法", "家事", "司法", "考官", "律師", "刑事", "民事", "開庭", "法學", "判決", "起訴", "憲法", "條文", "契約", "侵權", "時效", "抗辯", "答辯", "裁判", "罪"]
HISTORY_FILE = "C:/LocalAI_Workstation/scraped_history.json"

TAIWAN_LEGAL_PATTERNS = [
    r"\d+\s*年\s*[^\d\s]+\s*字第\s*\d+\s*號",  # 裁判字號，例如 112年上字第10號
    r"第\s*\d+\s*條",                       # 法條，例如 第197條
    r"民法|刑法|民事訴訟法|刑事訴訟法|行政程序法|司法院|法院|最高法院|檢察署|檢察官|起訴書|判決書|裁定書|訴狀|聲請書|答辯狀"
]

def is_legal_text(text):
    """分析文本內容，利用正則表達式與關鍵字密度判定是否為法律相關內容"""
    if not text:
        return False
    # 1. 檢查台灣法律特有正則特徵
    for pattern in TAIWAN_LEGAL_PATTERNS:
        if re.search(pattern, text):
            return True
    # 2. 統計獨特法律關鍵字數量
    matched_kws = set()
    for kw in LAW_KEYWORDS:
        if kw in text:
            matched_kws.add(kw)
    # 若包含至少 2 個不同的法律關鍵字，則視為法律相關
    if len(matched_kws) >= 2:
        return True
    return False

def is_legal_source(url, html_content):
    """嚴格判斷資料來源（網址與網頁內容）是否為法律相關，杜絕爬取無關網站"""
    url_lower = url.lower()
    # 1. 如果網址本身明顯是法律相關網站，直接信任
    if any(kw in url_lower for kw in ["law", "twlaw", "judge", "court", "lexmind", "moj.gov.tw"]):
        return True
        
    # 2. 否則，網頁全文必須包含足夠的法律特徵（至少 2 個正則特徵或至少 5 個獨特法律關鍵字）
    matched_patterns = 0
    for pattern in TAIWAN_LEGAL_PATTERNS:
        if re.search(pattern, html_content):
            matched_patterns += 1
            
    matched_kws = set()
    for kw in LAW_KEYWORDS:
        if kw in html_content:
            matched_kws.add(kw)
            
    if matched_patterns >= 2 or len(matched_kws) >= 5:
        return True
    return False

def load_scraped_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_scraped_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save scraped history: {e}")

def run_independent_scraper():
    update_status("running", 5, "正在初始化爬蟲環境與目標網址...")
    target_url = "https://twlawbot.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        update_status("running", 15, "正在連線外部法律題庫網站並下載網頁內容...")
        response = requests.get(target_url, headers=headers, timeout=20)
        if response.status_code != 200:
            raise Exception(f"伺服器回應異常，狀態碼: {response.status_code}")
    except Exception as e:
        update_status("failed", 100, f"網路連線失敗: {str(e)}")
        raise Exception(f"網路連線失敗: {str(e)}")
        
    update_status("running", 30, "連線成功！正在驗證資料來源並進行 DOM 解析...")
    
    # 智慧資料來源檢測：判斷是否為法律相關的網頁內容
    if not is_legal_source(target_url, response.text):
        update_status("failed", 100, "該網站不包含足夠的法律相關內容，拒絕爬取。")
        raise Exception("❌ [來源拒絕] 該網站不包含足夠的法律相關內容，拒絕爬取。")
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 多重類名彈性匹配
    question_cards = soup.find_all(['article', 'div'], class_=['exam-card', 'question-item'])
    if not question_cards:
        update_status("failed", 100, "未能在網頁中定位到任何考題區塊，可能目標網站結構已更換。")
        raise Exception("未能在網頁中定位到任何考題區塊，可能目標網站結構已更換。")
        
    total_questions = len(question_cards)
    update_status("running", 40, f"成功識別 HTML 結構，共發現 {total_questions} 題新考題。開始清洗與寫入...")
    
    history = load_scraped_history()
    parsed_count = 0
    skipped_by_mem = 0
    skipped_by_non_legal = 0
    
    for idx, card in enumerate(question_cards):
        try:
            q_id = card.get('data-qid') or card.get('id') or f"hash_{idx}"
            
            year_tag = card.find(class_=['badge-year', 'exam-year'])
            subject_tag = card.find(class_=['badge-subject', 'exam-subject'])
            year = year_tag.text.strip() if year_tag else "未知年份"
            subject = subject_tag.text.strip() if subject_tag else "綜合學科"
            
            title_node = card.find(['div', 'h3', 'p'], class_=['question-title', 'stem', 'content'])
            if not title_node: 
                continue
            title_text = title_node.text.strip()
            
            options = []
            options_container = card.find(['ul', 'ol', 'div'], class_=['options-list', 'options-group'])
            if options_container:
                for opt in options_container.find_all(['li', 'div', 'label']):
                    opt_text = opt.text.strip()
                    if opt_text: 
                        options.append(opt_text)
            
            ans_node = card.find(class_=['correct-answer', 'ans-key'])
            answer = ans_node.get('data-ans') or ans_node.text.replace("正確答案：", "").strip() if ans_node else "未公布"
            
            exp_node = card.find(class_=['explanation-box', 'analysis-content', '詳解', 'explanation'])
            explanation = exp_node.text.strip() if exp_node else "暫無解析數據。"
            
            # 智能內容過濾：分析題幹/選項/詳解是否為法律相關，杜絕亂抓資料
            full_content = f"{subject} {title_text} {explanation} " + " ".join(options)
            if not is_legal_text(full_content):
                skipped_by_non_legal += 1
                continue
                
            # 智能記憶體防護：利用 SHA-256 雜湊比對題目內容，若完全一致則跳過；若內容有更新（如答案校正或詳解補充）則自動覆寫更新
            import hashlib
            content_hash = hashlib.sha256(full_content.encode('utf-8')).hexdigest()
            
            if q_id in history and history[q_id].get("content_hash") == content_hash:
                skipped_by_mem += 1
                continue
                
            # 寫入 Obsidian
            save_to_obsidian(q_id, year, subject, title_text, options, answer, explanation)
            
            # 寫入智慧記憶
            history[q_id] = {
                "scraped_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "year": year,
                "subject": subject,
                "content_hash": content_hash
            }
            save_scraped_history(history)
            parsed_count += 1
            
            current_progress = 40 + int((parsed_count / total_questions) * 55)
            update_status("running", current_progress, f"正在解析並同步：[{year} {subject}] 第 {parsed_count}/{total_questions} 題...")
            time.sleep(0.1)
        except Exception as item_error:
            print(f"解析第 {idx} 個考題區塊時發生單項錯誤: {item_error}")
            continue
            
    skipped_msg = f" (已跳過重複: {skipped_by_mem} 題，跳過非法律: {skipped_by_non_legal} 題)"
    update_status("completed", 100, f"同步成功！本次共新同步 {parsed_count} 題司法官、律師考古題。{skipped_msg}")

if __name__ == "__main__":
    try:
        run_independent_scraper()
    except Exception as e:
        update_status("failed", 100, f"排程執行發生致命崩潰: {str(e)}")

