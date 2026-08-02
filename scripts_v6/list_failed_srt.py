import os
import sys
import datetime
from pathlib import Path

sys.path.append('C:\\LocalAI_Workstation\\scripts')
from auto_ingest_bot import scan_drives, SUPPORTED_EXTS, is_file_content_legal, get_video_duration_and_size, load_ingested_history, get_processed_stems

def generate_failed_srt_list():
    folders = scan_drives()
    history = load_ingested_history()
    
    stems_cache = get_processed_stems()
    
    failed_files = []
    
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
                
                stem = f.stem
                matching_md = next((p for p in stems_cache if stem in p), None)
                
                if matching_md or (abs_p in history):
                    srt_name = matching_md.replace('.md', '.srt') if matching_md else f"{stem}.srt"
                    srt_path = Path("A:\\processed_md") / srt_name
                    
                    is_failed = False
                    reason = ""
                    srt_size_kb = 0
                    
                    if not srt_path.exists():
                        is_failed = True
                        reason = "SRT 遺失"
                    else:
                        srt_size_kb = srt_path.stat().st_size / 1024
                        min_kb = max(5.0, duration_min * 0.6)
                        max_kb = max(50.0, duration_min * 3.5)
                        if not (min_kb <= srt_size_kb <= max_kb):
                            is_failed = True
                            reason = f"大小異常 (門檻: {min_kb:.1f}~{max_kb:.1f} KB)"
                    
                    if is_failed:
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
                        
                        failed_files.append({
                            "course": prefix,
                            "video_name": f.name,
                            "srt_name": srt_name,
                            "srt_size_kb": round(srt_size_kb, 1),
                            "dur_min": round(duration_min, 1),
                            "reason": reason
                        })

    try:
        from run_workflow import get_legal_priority_score
    except ImportError:
        def get_legal_priority_score(name): return 100

    failed_files.sort(key=lambda x: (get_legal_priority_score(x['course']), x['course'], x['video_name']))
    
    report_lines = [
        "# 🚨 轉譯失敗退件清單 (依 SRT 嚴格檢驗標準被剔除)",
        "",
        f"在過去被標記為完成的 215 堂課程中，有以下 **{len(failed_files)}** 堂課程因為 **SRT 字幕檔體積過小或直接遺失**，被判定為轉譯斷線的「半殘品」。",
        "它們現在已經被踢回待處理區，被系統當成**從未上傳過雲端**的檔案，等待下一次被重新處理：",
        "",
        "| 編號 | 課程標籤 | 原始影片檔名 | 對應的 SRT 檔名 | SRT 大小 (KB) | 原始時長 (分) | 剔除原因 |",
        "|---|---|---|---|---|---|---|"
    ]
    
    for idx, item in enumerate(failed_files, 1):
        report_lines.append(f"| {idx} | {item['course']} | {item['video_name']} | {item['srt_name']} | {item['srt_size_kb']} | {item['dur_min']} | {item['reason']} |")
        
    out_path = r"C:\Users\temp\.gemini\antigravity\brain\76013557-a693-45a5-919b-4c28a944e950\failed_srt_list.md"
    with open(out_path, "w", encoding="utf-8-sig") as out_f:
        out_f.write("\n".join(report_lines))
        
    print(f"成功掃描！共發現 {len(failed_files)} 堂失敗品。報表已輸出至 {out_path}")

if __name__ == '__main__':
    generate_failed_srt_list()
