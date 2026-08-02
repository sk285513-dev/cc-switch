import os
import glob
import time
import re
from pathlib import Path
from collections import Counter

PROCESSED_DIR = r"A:\processed_md"
REPORT_PATH = r"C:\LocalAI_Workstation\Obsidian_Vault\04_教材圖表校對\新版限度評估報告.md"
# 基準時間：在此時間之後產生的檔案才算數
START_TIME = time.time()
TARGET_COUNT = 6

def check_hallucination(text):
    # 檢查是否有瘋狂重複的長句 (長度>50)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 50]
    if not lines:
        return "無重複 (安全)"
    c = Counter(lines)
    most_common, count = c.most_common(1)[0]
    if count > 5:
        return f"🚨 疑似幻覺! 重複 {count} 次: {most_common[:30]}..."
    return "無重複 (安全)"

def main():
    print(f"開始監聽 {PROCESSED_DIR}，等待 {TARGET_COUNT} 個新檔案產生...")
    processed_files = set()
    
    while True:
        current_mds = glob.glob(os.path.join(PROCESSED_DIR, "*.md"))
        new_mds = []
        for md in current_mds:
            if os.path.getmtime(md) > START_TIME:
                new_mds.append(md)
        
        if len(new_mds) >= TARGET_COUNT:
            print(f"已收集到 {len(new_mds)} 個新檔案，開始產生報告！")
            break
            
        time.sleep(60)
        
    report_lines = [
        "# 📊 Vertex AI (Gemini 2.5 Pro) 檔案容量與幻覺觀測報告",
        f"> **觀測目標**：放寬上限至 20.0 KB/min，下限維持 0.6 KB/min 狀態下，前 {TARGET_COUNT} 堂完成的課程。",
        "",
        "| 檔名 | 檔案大小 (KB) | 影片時長 (分) | 實際比例 (KB/分) | 幻覺偵測 (重複文字) |",
        "|---|---|---|---|---|"
    ]
    
    for md_path in new_mds[:TARGET_COUNT]:
        size_kb = os.path.getsize(md_path) / 1024.0
        try:
            with open(md_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content = f.read()
                
            # 抓取教材時長
            match = re.search(r'教材時長.*[:：]\s*(\d+)\s*分', content)
            duration = max(1, int(match.group(1))) if match else 1
            ratio = size_kb / duration
            
            hal_status = check_hallucination(content)
            name = os.path.basename(md_path)
            
            report_lines.append(f"| {name} | {size_kb:.1f} | {duration} | {ratio:.2f} | {hal_status} |")
        except Exception as e:
            report_lines.append(f"| {os.path.basename(md_path)} | {size_kb:.1f} | 解析失敗 | N/A | {str(e)} |")
            
    report_lines.extend([
        "",
        "## 結論與建議",
        "請根據上述實際產出的 `KB/分`，決定我們最終要寫死在 `file_watcher.py` 的新版上限值。"
    ])
    
    with open(REPORT_PATH, 'w', encoding='utf-8-sig') as f:
        f.write('\n'.join(report_lines))
        
    print(f"報告已產出至: {REPORT_PATH}")

if __name__ == "__main__":
    main()
