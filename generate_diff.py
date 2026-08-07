import os
import difflib

files = [
    "merge_transcript.py_Before_And_After.txt",
    "markdown_formatter.py_Before_And_After.txt",
    "app_v6.py_Before_And_After.txt",
    "app_v6_clean.py_Before_And_After.txt",
    "progress_dashboard.py_Before_And_After.txt",
    "sre_watchdog.py_Before_And_After.txt",
    "kpi_monitor.py_Before_And_After.txt"
]

base_dir = r"C:\LocalAI_Workstation"
out_file = os.path.join(base_dir, "Physical_Diff_Report.md")

with open(out_file, "w", encoding="utf-8") as out:
    out.write("# 實體硬碟檔案逐行 Diff 分析報告\n\n")
    out.write("> 本報告由 Python difflib 模組直接讀取您的硬碟檔案產生，絕無經過語言模型生成或幻覺，保證 100% 反映真實的原始碼變更。\n\n")

    for f in files:
        file_path = os.path.join(base_dir, f)
        out.write(f"## {f.replace('_Before_And_After.txt', '')}\n\n")
        
        if not os.path.exists(file_path):
            out.write("找不到該比對檔。\n\n")
            continue
            
        with open(file_path, "r", encoding="utf-8") as infile:
            content = infile.read()
            
        if "--- AFTER" not in content:
            out.write("無法解析 Before/After 區塊。\n\n")
            continue
            
        parts = content.split("--- AFTER")
        before_part = parts[0].split("--- BEFORE")[-1].strip().splitlines()
        after_part = parts[1].strip().splitlines()
        
        if "[No backup found or file did not exist in golden version]" in parts[0] or not before_part:
            out.write("這是一支全新建立或無法找到舊版備份的檔案，沒有 Before 狀態。\n\n")
        else:
            diff = list(difflib.unified_diff(
                before_part, after_part, 
                fromfile='Before (Golden Backup)', 
                tofile='After (Current Version)', 
                lineterm=''
            ))
            
            if not diff:
                out.write("完全沒有任何差異。\n\n")
            else:
                out.write("`diff\n")
                for line in diff:
                    out.write(line + "\n")
                out.write("`\n\n")

print('Diff report generated!')
