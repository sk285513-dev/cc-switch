# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 1: 領域防護與前端物流 (Ingestion & Rules)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 1】。
# 依賴 national_exam_rules.py 作為 SSOT。修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import os
import sys
import datetime
from pathlib import Path

sys.path.append('C:\\LocalAI_Workstation\\scripts')
from national_exam_rules import SUPPORTED_EXTS, is_file_content_legal, get_exam_score
from auto_ingest_bot import scan_drives, get_video_duration_and_size, is_file_already_ingested, load_ingested_history, get_processed_stems

def generate_perfect_list():
    folders = scan_drives()
    history = load_ingested_history()
    
    stems_cache = get_processed_stems()
    
    perfect_files = []
    
    for folder in folders:
        p_obj = Path(folder)
        if not p_obj.exists(): continue
        
        for f in p_obj.rglob("*"):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
                abs_p = str(f.resolve())
                if not is_file_content_legal(abs_p):
                    continue
                    
                duration_min, size_mb, ratio = get_video_duration_and_size(abs_p)
                if duration_min <= 0:
                    continue
                    
                is_video = f.suffix.lower() == '.mp4'
                lower_bound = 2.0 if is_video else 0.1
                if duration_min < 20.0 or ratio < lower_bound or ratio > 50.0:
                    continue
                    
                if is_file_already_ingested(abs_p, history):
                    parts = list(f.parts)
                    dirs = parts[1:-1]
                    
                    class_name = "預設課程"
                    lesson_name = "預設課堂"
                    
                    if len(dirs) >= 2:
                        if dirs[-1].lower() in ['bandicam', 'record', '錄音', '錄影']:
                            lesson_name = dirs[-2]
                            class_name = dirs[-3] if len(dirs) >= 3 else dirs[-2]
                        else:
                            lesson_name = dirs[-1]
                            class_name = dirs[-2]
                    elif len(dirs) == 1:
                        class_name = dirs[0]
                        lesson_name = dirs[0]
                        
                    prefix = f"[{class_name}_{lesson_name}]"
                    
                    stem = f.stem
                    matching_md = next((p for p in stems_cache if stem in p), None)
                    srt_size_kb = 0
                    mtime_str = "N/A"
                    srt_name = "N/A"
                    
                    if matching_md:
                        srt_name = matching_md.replace('.md', '.srt')
                        srt_path = Path("A:\\processed_md") / srt_name
                        if srt_path.exists():
                            srt_size_kb = srt_path.stat().st_size / 1024
                            mtime = srt_path.stat().st_mtime
                            mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            mtime_str = "SRT 遺失"
                    
                    perfect_files.append({
                        "course": prefix,
                        "file_name": srt_name,
                        "size_kb": round(srt_size_kb, 1),
                        "dur_min": round(duration_min, 1),
                        "mtime": mtime_str
                    })

    perfect_files.sort(key=lambda x: (get_exam_score(x['course']), x['course'], x['file_name']))
    
    report_lines = [
        "# 🥇 真正完美過關之正規課程清單 (附帶 SRT 字幕完成時間)",
        "",
        f"經過嚴格把關，目前系統中共有 **{len(perfect_files)}** 堂真正健康的筆記，以下為對應的 **SRT 字幕檔** 完成時間：",
        "",
        "| 編號 | 優先權重 | 課程標籤 | SRT 字幕檔名 | SRT 大小 (KB) | 原始時長 (分) | SRT 寫入完成時間 |",
        "|---|---|---|---|---|---|---|"
    ]
    
    for idx, item in enumerate(perfect_files, 1):
        score = get_exam_score(item['course'])
        report_lines.append(f"| {idx} | {score} | {item['course']} | {item['file_name']} | {item['size_kb']} | {item['dur_min']} | {item['mtime']} |")
        
    out_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\clean_processed_list.md"
    with open(out_path, "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(report_lines))
        
    print(f"成功掃描！共發現 {len(perfect_files)} 堂已處理課程。SRT 報表已輸出至 {out_path}")

if __name__ == '__main__':
    generate_perfect_list()
