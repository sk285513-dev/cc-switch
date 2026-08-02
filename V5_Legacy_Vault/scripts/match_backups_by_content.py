import os
import re
from pathlib import Path

list_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
md_dir = Path(r"A:\processed_md")

def check():
    if not os.path.exists(list_path): return
    with open(list_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    valid_items = []
    for line in lines:
        if line.startswith("|") and not "編號" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                valid_items.append({
                    "course": parts[2],
                    "video": parts[3],
                    "md_name": parts[4].replace('.srt', '.md')
                })

    # 1. Build a hash map of Backup folders based on their merged_summary.txt content
    backup_dirs = [Path(r"F:\chunks_backup"), Path(r"E:\chunks_backup"), Path(r"A:\chunks")]
    backup_signatures = {}
    
    for bdir in backup_dirs:
        if not bdir.exists(): continue
        for d in bdir.iterdir():
            if d.is_dir():
                summary_file = d / "merged_summary.txt"
                if summary_file.exists():
                    try:
                        with open(summary_file, "r", encoding="utf-8") as f:
                            content = f.read(1000)
                            # Find the first real text after headers
                            match = re.search(r'### 📖 章節主題 1.*?---(.*)', content, re.DOTALL)
                            if match:
                                text = match.group(1).strip()[:100] # First 100 chars
                                # Remove whitespaces for robust matching
                                text = re.sub(r'\s+', '', text)
                                if text:
                                    backup_signatures[text] = d.name
                    except:
                        pass

    print(f"Loaded {len(backup_signatures)} unique signatures from backup folders.")
    
    has_backup = []
    no_backup = []
    
    # 2. Match with MD files
    for item in valid_items:
        md_path = md_dir / item["md_name"]
        if not md_path.exists():
            no_backup.append(item)
            continue
            
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        match = re.search(r'## 🧠 智慧教材法理消化 \(RAG 摘要\).*?### 📖 章節主題 1.*?---(.*)', content, re.DOTALL)
        if match:
            text = match.group(1).strip()[:100]
            text = re.sub(r'\s+', '', text)
            
            # Check if this signature exists in backups
            found = False
            for sig, task_id in backup_signatures.items():
                if len(text) > 20 and len(sig) > 20 and (text.startswith(sig[:50]) or sig.startswith(text[:50])):
                    has_backup.append((item, task_id))
                    found = True
                    break
            if not found:
                no_backup.append(item)
        else:
            no_backup.append(item)

    print(f"\n--- 實體內容交叉比對結果 (Content-Based Matching) ---")
    print(f"總計健康課程: {len(valid_items)} 堂")
    print(f"✅ 成功配對到實體備份切片: {len(has_backup)} 堂")
    print(f"❌ 無本地備份 (舊版引擎處理): {len(no_backup)} 堂")
    
    # Check creation dates of the NO BACKUP files
    import datetime
    cutoff = datetime.datetime(2026, 7, 14)
    old_no_backup = 0
    for item in no_backup:
        p = md_dir / item["md_name"]
        if p.exists():
            if datetime.datetime.fromtimestamp(p.stat().st_ctime) < cutoff:
                old_no_backup += 1
                
    print(f"\n進一步分析無備份的 {len(no_backup)} 堂課：")
    print(f"其中 {old_no_backup} 堂確實是在 7/14 以前 (無備份機制時期) 建立的。")

if __name__ == '__main__':
    check()
