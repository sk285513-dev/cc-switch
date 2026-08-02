# -*- coding: utf-8 -*-
import json
"""
LexMind-Omni 法律教材工作站 - 本地 IDE 自動化驗收與測試套件
自動掃描 A:\manifests 下所有已完成的真實任務，驗證實體檔案落地、格式品質、RAG索引完整度與 J 碟雙目錄備份。
"""
import os
import sys
import json
import time
import re
from pathlib import Path

# 強制終端機以 UTF-8 輸出，避免 cp950 亂碼崩潰
sys.stdout.reconfigure(encoding='utf-8-sig')

# ANSI 顏色配置
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def log_info(msg):
    print(f"{BLUE}[INFO]{RESET} {msg}")

def log_success(msg):
    print(f"{GREEN}[PASS]{RESET} {msg}")

def log_warning(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")

def log_error(msg):
    print(f"{RED}[FAIL]{RESET} {msg}")

def check_file_quality(file_path, file_type):
    """檢測特定落地檔案的實體大小與格式規範"""
    if not os.path.exists(file_path):
        return False, "檔案未落地（不存在）"
    
    size_kb = os.path.getsize(file_path) / 1024
    if size_kb == 0:
        return False, "檔案大小為 0 內容為空"
    
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except Exception as e:
        return False, f"UTF-8 解碼失敗: {e}"
        
    # 各類別檔案的格式驗證
    if file_type == "markdown":
        # 檢查是否有 Markdown 標題階層
        if not re.search(r"^#+ ", content, re.MULTILINE):
            return False, "缺乏 Markdown 標題階層 (#, ##)"
        # 檢查是否有時間戳記
        if not re.search(r"\[\d+:\d+\]|\[\d+:\d+:\d+\]", content):
            return False, "缺乏時間戳記對齊"
        # 檢查同音錯字排除度
        errors = ["格論", "地政治", "消滅實效"]
        found_errs = [err for err in errors if err in content]
        if found_errs:
            return False, f"檢測到殘留同音錯字: {found_errs}"
            
    elif file_type == "srt":
        # 檢查標準 SRT 結構
        if not re.search(r"^\d+\s*\n\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->", content, re.MULTILINE):
            return False, "不符合標準 SRT 字幕格式時間軸"
            
    elif file_type == "vtt":
        if not content.startswith("WEBVTT"):
            return False, "缺乏 WebVTT 標頭"
            
    elif file_type == "json_index":
        try:
            data = json.loads(content)
            # 檢查 RAG 關鍵欄位
            required_keys = ["task_id", "original_name", "summary", "full_text_cleaned", "segments"]
            missing = [k for k in required_keys if k not in data]
            if missing:
                return False, f"JSON 索引缺乏核心 RAG 欄位: {missing}"
        except Exception as e:
            return False, f"JSON 格式解析出錯: {e}"
            
    return True, f"正常 ({size_kb:.2f} KB)"

def run_verification():
    print("=" * 70)
    print(f"{BOLD}LexMind-Omni 本地 IDE 自動化驗收與品管工具啟動{RESET}")
    print(f"執行時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    manifests_dir = "A:\\manifests"
    processed_dir = "A:\\processed_md"
    
    if not os.path.exists(manifests_dir):
        log_error(f"Manifest 目錄 {manifests_dir} 不存在，驗收終止。")
        return False
        
    expected_files = {
        "output_markdown": ("markdown", "Markdown 講義 (.md)"),
        "output_srt": ("srt", "SRT 字幕 (.srt)"),
        "output_vtt": ("vtt", "WebVTT 字幕 (.vtt)"),
        "output_txt": ("txt", "純文字逐字稿 (.txt)"),
        "output_json_index": ("json_index", "RAG JSON 索引 (_index.json)")
    }

    # 1. 掃描所有已完成 (completed) 的任務
    completed_manifests = []
    try:
        for f in os.listdir(manifests_dir):
            if f.endswith(".json") and not f.endswith("_chunks.json") and f.startswith("task_"):
                try:
                    mpath = os.path.join(manifests_dir, f)
                    with open(mpath, "r", encoding="utf-8-sig") as jf:
                        data = json.load(jf)
                    source_path = data.get("source_path", "")
                    # 只驗收真實教材任務
                    if "mock_course_dir" in source_path or "raw_data" in source_path:
                        continue
                    if data.get("status") == "completed":
                        completed_manifests.append((mpath, data))
                except Exception:
                    pass
    except Exception as e:
        log_error(f"掃描 manifests 資料夾失敗: {e}")
        return False

    log_info(f"偵測到已完成的真實教材任務數量: {len(completed_manifests)}")

    all_tasks_ok = True
    report_lines = []
    
    if not completed_manifests:
        log_warning("目前尚無已端到端完成 (completed) 的真實課程任務。")
        all_tasks_ok = False
        report_lines.append("### ⚠️ 目前尚無端到端完成之真實課程任務。")
    else:
        for idx, (mpath, manifest) in enumerate(completed_manifests):
            task_id = manifest.get("task_id")
            source_name = manifest.get("source_name")
            source_path = manifest.get("source_path")
            
            print("-" * 50)
            log_info(f"[{idx+1}/{len(completed_manifests)}] 開始驗收檢測任務 {task_id}: {source_name}")
            
            task_ok = True
            v_report = []
            
            # A 碟檢測
            for key, (ftype, label) in expected_files.items():
                fpath = manifest.get(key)
                if not fpath:
                    log_error(f"  {label}: Manifest 中未指定輸出路徑")
                    task_ok = False
                    v_report.append(f"- {label}: Manifest 未指定路徑 ❌")
                    continue
                success, info = check_file_quality(fpath, ftype)
                if success:
                    log_success(f"  {label}: {info}")
                    v_report.append(f"- {label}: {info} (`{os.path.basename(fpath)}`)  ")
                else:
                    log_error(f"  {label}: {info}")
                    v_report.append(f"- {label}: {info} ❌")
                    task_ok = False
            
            # J 碟備份檢測
            backup_status = "未核對"
            if source_path:
                backup_dir = os.path.dirname(source_path)
                if os.path.exists(backup_dir):
                    backup_ok = True
                    for key, (ftype, label) in expected_files.items():
                        fpath = manifest.get(key)
                        if fpath:
                            backup_fpath = os.path.join(backup_dir, os.path.basename(fpath))
                            success, info = check_file_quality(backup_fpath, ftype)
                            if not success:
                                backup_ok = False
                    if backup_ok:
                        log_success("  J 碟原始目錄備份：5 檔案完整落地，同源備份通過！")
                        backup_status = "5 檔完整備份且同步成功"
                    else:
                        log_error("  J 碟原始目錄備份：檔案缺失或毀損！")
                        backup_status = "備份缺失或檢驗失敗 ❌"
                        task_ok = False
                else:
                    log_warning(f"  J 碟影片原始目錄離線或未掛載: {backup_dir}")
                    backup_status = "影片目錄未掛載或不存在 ⚠️"
                    
            if not task_ok:
                all_tasks_ok = False
                
            status_symbol = "✅ PASS" if task_ok else "❌ FAIL"
            report_lines.append(f"### 課程 {idx+1}: {source_name} ({status_symbol})")
            report_lines.append(f"- **Task ID**: `{task_id}`")
            report_lines.append(f"- **原目錄備份**: {backup_status}")
            report_lines.append("#### 落地檔案檢驗詳情:")
            report_lines.extend(v_report)
            report_lines.append("")

    # 3. 輸出本機驗收報告檔案
    target_lessons = 30
    meets_target = len(completed_manifests) >= target_lessons
    final_pass = all_tasks_ok and meets_target
    
    report_md = f"""# ⚖️ LexMind-Omni 法律國考 AI 教材批次自動驗收品管報告
生成時間: {time.strftime('%Y-%m-%d %H:%M:%S')}
端到端完成進度: {len(completed_manifests)}/{target_lessons}真實教材
最終驗收結果: {"**【100% 驗收通過，完全達標】** 🎉" if final_pass else "**【未通過，尚有錯誤或未達目標堂數】** ❌"}

## 📝 各課程詳細品質檢驗狀況
{chr(10).join(report_lines)}

## 🛠️ 本地復原與維護指引
1. 若有檔案 FAIL 或是任務狀態顯示為失敗，請至 `A:\\logs\\workflow.log` 檢視對應 Task ID 的錯誤日誌。
2. 守護進程與 watchdog (每 60 秒自癒) 正在後台運行消化佇列，請耐心等待全部 {target_lessons} 堂課程完成。
"""
    
    try:
        report_out_path = os.path.join(processed_dir, "local_verification_report.md")
        os.makedirs(processed_dir, exist_ok=True)
        with open(report_out_path, "w", encoding="utf-8-sig") as wf:
            wf.write(report_md)
        log_success(f"驗收報告已更新並寫入: {report_out_path}")
    except Exception as ree:
        log_error(f"無法寫入驗收報告: {ree}")
        
    print("=" * 70)
    if final_pass:
        print(f"{GREEN}{BOLD}🎉 驗收結論：所有 {len(completed_manifests)} 份實體檔案與格式指標 100% 達標！通過測試！{RESET}")
    else:
        print(f"{RED}{BOLD}❌ 驗收結論：未達標（已完成: {len(completed_manifests)}/30，或有檔案檢測失敗）。請查閱日誌排除錯誤。{RESET}")
    print("=" * 70)
    return final_pass

if __name__ == "__main__":
    run_verification()

