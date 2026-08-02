import os
import sys
from pathlib import Path

# 將路徑加入以便引用模組
sys.path.append('C:\\LocalAI_Workstation\\scripts')
from auto_ingest_bot import get_processed_stems

def generate_processed_list():
    print("正在整理雲端已完成處理之課程清單...")
    
    stems_cache = get_processed_stems()
    
    processed_files = []
    
    # 掃描 A:\processed_md 目錄
    processed_dir = Path("A:\\processed_md")
    if not processed_dir.exists():
        print("找不到 A:\processed_md 目錄。")
        return
        
    for f in processed_dir.glob("*.md"):
        if f.is_file():
            # 檢查是否為健康檔案 (大於 5KB 代表至少有一點內容)
            size_kb = f.stat().st_size / 1024
            if size_kb < 5.0:
                continue
                
            name = f.stem
            
            # 嘗試切分出課程名稱與檔名
            # 檔名格式通常為 [課程名稱_ch1]_預約 1 ...
            course_label = "未知分類"
            if name.startswith("[") and "]" in name:
                course_label = name.split("]")[0] + "]"
                
            processed_files.append({
                "course": course_label,
                "file_name": f.name,
                "size_kb": round(size_kb, 1)
            })

    try:
        from run_workflow import get_legal_priority_score
    except ImportError:
        def get_legal_priority_score(name): return 100

    processed_files.sort(key=lambda x: (get_legal_priority_score(x['course']), x['course'], x['file_name']))
    
    report_lines = [
        "# ☁️ 已成功上傳雲端並完成轉譯之正規課程清單",
        "",
        f"目前系統中共找到 **{len(processed_files)}** 堂已經完美生成 Markdown 筆記的課程：",
        "",
        "| 編號 | 優先權重 | 課程標籤 | 產出筆記檔名 | 大小 (KB) |",
        "|---|---|---|---|---|"
    ]
    
    for idx, item in enumerate(processed_files, 1):
        score = get_legal_priority_score(item['course'])
        report_lines.append(f"| {idx} | {score} | {item['course']} | {item['file_name']} | {item['size_kb']} |")
        
    out_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
    with open(out_path, "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(report_lines))
        
    print(f"成功掃描！共發現 {len(processed_files)} 堂已處理課程。報表已輸出至 {out_path}")

if __name__ == '__main__':
    generate_processed_list()
