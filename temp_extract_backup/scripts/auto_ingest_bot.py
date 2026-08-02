# -*- coding: utf-8 -*-
import os
import sys
import time
import re
import json
import gc
import subprocess
from pathlib import Path

def get_video_duration_and_size(file_path):
    """
    呼叫 ffprobe 取得影片分鐘數，並計算檔案大小 (MB)
    回傳 (分鐘數, 大小MB, MB/分比例)
    """
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        duration_sec = float(result.stdout.strip())
        duration_min = duration_sec / 60.0
        
        if duration_min <= 0:
            return 0, size_mb, 0
            
        ratio = size_mb / duration_min
        return duration_min, size_mb, ratio
    except Exception as e:
        return 0, 0, 0

# 將 root 與 scripts 目錄納入 PATH，確保子模組順利載入
curr_dir = Path(__file__).resolve().parent
if curr_dir.name in ("新程式碼", "scripts", "extracted_sources"):
    base_dir = curr_dir.parent
else:
    base_dir = curr_dir

sys.path.append(str(base_dir))
sys.path.append(str(base_dir / "scripts"))
sys.path.append(str(base_dir / "extracted_sources" / "scripts"))

# 強制 stdout / stderr 採用 UTF-8 輸出，防止 Windows cp950 編碼錯誤崩潰
if sys.platform == "win32":
    try:
        import io
        # if hasattr(sys.stdout, 'buffer'):
        #     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        # if hasattr(sys.stderr, 'buffer'):
        #     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

from agent_core_pro import LocalLegalAgent
from multimodal_input import MultimodalLegalInput
from visual_analyzer import VisualLegalAnalyzer

# 套用 48GB DRAM 環境硬體優化配置 (Single Source of Truth)
try:
    from scripts.config_loader import apply_hardware_config
    cfg = apply_hardware_config()
    CHROMA_TEXT_LIMIT = cfg.get("chroma_text_limit", 150000)
except Exception:
    import os
    os.environ["OMP_NUM_THREADS"] = "4"
    os.environ["MKL_NUM_THREADS"] = "4"
    CHROMA_TEXT_LIMIT = 150000

import hashlib

SUPPORTED_EXTS = {'.mp3', '.mp4', '.wav'}  # 嚴格依照使用者要求：規定除非有特殊原因，否則預設就是只能吸入國家考試「司法官與律師」等法律相關專業科目的純影音格式
# 嚴格依照使用者要求：前提是必須嚴格封鎖非國家考試「司法官與律師」等法律相關專業科目以外的雜訊檔案
LAW_KEYWORDS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法", "強制執行法", "智慧財產權法", "土地稅法", "土地登記", "不動產估價", "立法程序與技術", "法院組織法", "海商法", "海洋法", "勞動社會法", "關稅法規"]

TAIWAN_LEGAL_PATTERNS = [
    r"\d+\s*年\s*[^\d\s]+\s*字第\s*\d+\s*號",  # 裁判字號，例如 112年上字第10號
    r"第\s*\d+\s*條",                       # 法條，例如 第197條
    r"民法|刑法|民事訴訟法|刑事訴訟法|行政程序法|司法院|法院|最高法院|檢察署|檢察官|起訴書|判決書|裁定書|訴狀|聲請書|答辯狀"
]

def get_file_hash(f_path):
    """計算檔案的 SHA-256 雜湊值，作為智能資料記憶的核心憑據"""
    sha256 = hashlib.sha256()
    try:
        if not os.path.exists(f_path):
            return None
        with open(f_path, 'rb') as f:
            while True:
                data = f.read(65536) # 64KB blocks
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    except Exception:
        return None

def check_text_for_legal_relevance(text):
    """分析文字內容，利用正則表達式與關鍵字密度判定是否為法律相關教材"""
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

def is_file_content_legal(f_path):
    """智能分析檔案名稱、路徑或實際內容，精確判別是否為法律教材，杜絕亂抓資料"""
    f_path_lower = str(f_path).lower()
    f_name = os.path.basename(f_path_lower)
    ext = os.path.splitext(f_path_lower)[1]
    
    # 0. 絕對封殺黑名單 (私人協調錄音、空大、房仲、法規庫等雜訊)
    BLACKLIST = ["法規庫", "空大", "協調", "不動產經紀", "房仲"]
    if any(bl in f_path_lower for bl in BLACKLIST):
        return False
    
    # 1. 首先檢查檔名本身是否符合法律特徵
    name_kws = [kw for kw in LAW_KEYWORDS if kw.lower() in f_name]
    if len(name_kws) >= 2:
        return True
        
    # 2. 如果檔名特徵不足，針對文本檔/PDF讀取內容進行語意分析
    if ext in {'.txt', '.md'}:
        try:
            with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                head = f.read(3000)
                if check_text_for_legal_relevance(head):
                    return True
        except Exception:
            pass
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(f_path)
            pages_text = []
            for i in range(min(2, len(reader.pages))):
                text = reader.pages[i].extract_text()
                if text:
                    pages_text.append(text)
            combined_text = "\n".join(pages_text)
            if check_text_for_legal_relevance(combined_text):
                return True
        except Exception:
            pass
            
    # 3. 影音與圖像檔案在尚未進行 ASR/OCR 之前僅以路徑做為防護線，必須在完整路徑中包含法律關鍵字
    if ext in {'.png', '.jpg', '.jpeg', '.mp3', '.mp4', '.wav'}:
        if any(kw.lower() in f_path_lower for kw in LAW_KEYWORDS):
            return True
            
    return False

EXCLUDE_DIRS = {
    "system volume information", "$recycle.bin", "windows", "program files", 
    "program files (x86)", "appdata", ".gemini", "node_modules", ".git", 
    "localai_workstation", "localaio_workstation", "temp", "cache", "anaconda3", "miniconda3", 
    ".conda", ".cargo", ".rustup", "pycache", "__pycache__", ".vscode", 
    "venv", ".venv", "build", "dist", "obj", "bin",
    "chunks", "chunks_backup", "processed_md", "manifests", "distillation_data"
}

BUFFER_FILE = "C:\\LocalAI_Workstation\\chosen_paths_buffer.json"

def scan_drives(scan_path=None):
    """搜尋指定的路徑或本機所有有效磁碟機中符合條件的法律教材資料夾，嚴防指定 H: 卻掃描其他磁碟之問題"""
    valid_folders = []
    drives = []
    
    # 如果傳入了指定路徑（防止亂抓其他磁碟）
    if scan_path:
        scan_path = str(scan_path).strip()
        # 移除引號
        if (scan_path.startswith('"') and scan_path.endswith('"')) or (scan_path.startswith("'") and scan_path.endswith("'")):
            scan_path = scan_path[1:-1].strip()
        
        # 處理 Windows 磁碟機，例如 H -> H:\ 或 H: -> H:\
        if len(scan_path) == 1 and scan_path.isalpha():
            scan_path = scan_path + ":\\"
        elif len(scan_path) == 2 and scan_path[1] == ':' and scan_path[0].isalpha():
            scan_path = scan_path + "\\"
            
        scan_path = os.path.abspath(scan_path)
        if not os.path.exists(scan_path):
            print(f"\n[Step 1] ❌ 指定的路徑不存在: {scan_path}")
            return []
            
        print(f"\n[Step 1] 開始精確掃描指定的路徑/資料夾: {scan_path}...")
        
        # 如果是單一檔案
        if os.path.isfile(scan_path):
            f_name = os.path.basename(scan_path)
            f_ext = os.path.splitext(f_name)[1].lower()
            if f_ext in SUPPORTED_EXTS:
                if is_file_content_legal(scan_path):
                    parent_dir = os.path.dirname(scan_path)
                    print(f"      [找到有效教材檔案] {scan_path}")
                    return [parent_dir]
            return []
            
        # 如果是特定資料夾且不是磁碟根目錄，先直接加入以防其命名沒有法律關鍵字但使用者刻意指定
        is_drive_root = (len(scan_path) == 3 and scan_path[1:] == ":\\") or scan_path == "/"
        if not is_drive_root and os.path.isdir(scan_path):
            try:
                # 檢查資料夾下是否有法律教材檔案
                has_legal_file = False
                for f in os.listdir(scan_path):
                    f_path = os.path.join(scan_path, f)
                    if os.path.isfile(f_path) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTS:
                        if is_file_content_legal(f_path):
                            has_legal_file = True
                            break
                if has_legal_file:
                    valid_folders.append(scan_path)
            except Exception:
                pass
                
        # 以此為起點
        drives = [scan_path]
    else:
        print("\n[Step 1] 開始掃描本機磁碟尋找法律教材資料夾...")
        # 獲取本機所有存在的磁碟機字母，排除未準備好的磁碟（例如光碟機）
        if sys.platform == "win32":
            try:
                import ctypes
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for i in range(26):
                    if bitmask & (1 << i):
                        drive_letter = chr(65+i)
                        if drive_letter in ('C', 'E'): continue
                        drive_path = f"{drive_letter}:\\"
                        # 取得磁碟類型並進行唯讀/準備狀態測試
                        dtype = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                        # 2: REMOVABLE, 3: FIXED, 4: REMOTE
                        if dtype in (2, 3, 4):
                            try:
                                # 測試是否可讀，不可讀會拋出異常
                                os.listdir(drive_path)
                                drives.append(drive_path)
                            except Exception:
                                pass
            except Exception:
                # 備用方案
                import string
                for letter in string.ascii_uppercase:
                    if letter in ('C', 'E'): continue
                    drive_path = f"{letter}:\\"
                    if os.path.exists(drive_path):
                        drives.append(drive_path)
        else:
            drives = ["/"]
            
        print(f"   -> 偵測到可讀取之本機磁碟機: {', '.join(drives)}")
    
    for drive in drives:
        print(f"   -> 正在掃描路徑 {drive} (最大深度限制為 8)...")
        # 遍歷目錄
        for root, dirs, files in os.walk(drive, topdown=True):
            # 計算當前深度
            try:
                rel_path = os.path.relpath(root, drive)
                depth = 0 if rel_path == "." else len(Path(rel_path).parts)
            except Exception:
                continue
            
            # 限制掃描最大深度為 8
            if depth >= 8:
                dirs.clear() # 停止遞迴其子目錄
                continue
                
            # 過濾掉敏感與系統目錄，防止掃描時卡死或速度極慢
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIRS and not d.startswith('.')]
            
            # 檢查完整路徑是否含有法律相關關鍵字 (解決課程名稱通常建立在父資料夾的實務情況)
            folder_matches = any(kw in root for kw in LAW_KEYWORDS)
            
            has_valid_media = False
            file_matches = False
            
            try:
                # 遍歷旗下檔案
                for f in os.listdir(root):
                    # 排除系統自行產生的中間暫存檔 (避免把自己的殘骸當成新課吃進去)
                    if f.startswith("chunk_") or f.startswith("temp_extract_"):
                        continue
                        
                    f_ext = os.path.splitext(f)[1].lower()
                    if f_ext in SUPPORTED_EXTS:
                        file_abs_path = os.path.join(root, f)
                        # 動態影片健康度檢查
                        duration_min, size_mb, ratio = get_video_duration_and_size(file_abs_path)
                        if duration_min > 0:
                            is_video = f_ext == '.mp4'
                            lower_bound = 2.0 if is_video else 0.1  # mp3/wav 語音檔每分鐘只需 0.1MB
                            
                            # 嚴格過濾：依據您定義的「正常教材（兩到三小時）」
                            if duration_min < 20.0 or ratio < lower_bound or ratio > 50.0:
                                print(f"      [異常廢片警告] 跳過檔案 {f} (比例: {ratio:.2f} MB/分, 體積: {size_mb:.1f} MB, 片長: {duration_min:.1f} 分)")
                                continue
                            elif duration_min < 60.0:
                                print(f"      [⚠️ 需手動核准的補充課] 發現 20~60 分鐘檔案 {f} (比例: {ratio:.2f} MB/分, 片長: {duration_min:.1f} 分)")
                                # 不跳過，讓它繼續被收集，但 watcher 會將其標記為 pending_approval
                            else:
                                print(f"      [✅ 健康媒體] {f} (比例: {ratio:.2f} MB/分, 體積: {size_mb:.1f} MB, 片長: {duration_min:.1f} 分)")
                                
                        has_valid_media = True
                        # 如果檔案名稱包含法律關鍵字
                        if any(kw in f for kw in LAW_KEYWORDS):
                            file_matches = True
            except Exception as e:
                pass
                
            # 雙重特徵匹配：資料夾名稱匹配且含有媒體，或檔案本身符合媒體且名稱匹配
            if has_valid_media and (folder_matches or file_matches):
                abs_path = os.path.abspath(root)
                if abs_path not in valid_folders:
                    valid_folders.append(abs_path)
                    reason = "資料夾名稱符合" if folder_matches else "檔案名稱符合"
                    print(f"      [找到有效教材資料夾 ({reason}, 深度: {depth})] {abs_path}")
                        
    return valid_folders

def update_buffer_file(paths):
    """將搜尋到的路徑寫入 chosen_paths_buffer.json"""
    try:
        os.makedirs(os.path.dirname(BUFFER_FILE), exist_ok=True)
        with open(BUFFER_FILE, "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=4)
        print(f"\n[Step 2] 成功將 {len(paths)} 個路徑寫入介面快取 buffer 檔案中。")
    except Exception as e:
        print(f"\n[Step 2] ❌ 寫入快取檔失敗: {e}")

HISTORY_FILE = "C:\\LocalAI_Workstation\\ingested_history.json"

def load_ingested_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                if isinstance(history, dict):
                    return history
        except Exception:
            pass
    return {}

def save_ingested_history(history):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
PROCESSED_STEMS_CACHE = None

def get_processed_stems():
    """快取所有已處理的檔案名稱，避免每次都掃描硬碟，造成 I/O 瓶頸"""
    global PROCESSED_STEMS_CACHE
    if PROCESSED_STEMS_CACHE is None:
        PROCESSED_STEMS_CACHE = set()
        processed_dir = Path("A:\\processed_md")
        if processed_dir.exists():
            for md_file in processed_dir.glob("*.md"):
                if md_file.name != "00_已處理清單_Agent請查閱此表.md":
                    try:
                        PROCESSED_STEMS_CACHE.add(md_file.name)
                    except Exception:
                        pass
    return PROCESSED_STEMS_CACHE

def generate_processed_report_table():
    """為未來的 Agent 與使用者產生一份總結表格，放在 A:\\processed_md 中方便查閱避免重複"""
    processed_dir = Path("A:\\processed_md")
    if not processed_dir.exists():
        return
        
    md_files = list(processed_dir.glob("*.md"))
    md_files = [f for f in md_files if f.name != "00_已處理清單_Agent請查閱此表.md"]
    
    report_lines = [
        "# 📚 全域已處理課程總表 (Source of Truth)",
        "本表由自動機器人維護，列出所有已經成功消化並產出講義的實體課程檔案。**任何 AI Agent 在進行處理前，請優先查閱此表以避免重複做工！**",
        "",
        f"**最後更新時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**已處理總數**: {len(md_files)} 堂課",
        "",
        "| 課程檔案名稱 | 大小 (KB) | 產出講義時間 |",
        "|---|---|---|"
    ]
    
    # 依時間排序 (最新的在最上面)
    try:
        md_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        for f in md_files:
            size_kb = round(os.path.getsize(f) / 1024, 2)
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(f)))
            report_lines.append(f"| {f.name} | {size_kb} | {mtime} |")
            
        report_path = processed_dir / "00_已處理清單_Agent請查閱此表.md"
        with open(report_path, "w", encoding="utf-8") as out_f:
            out_f.write("\n".join(report_lines))
    except Exception:
        pass

def is_file_already_ingested(f_path, history):
    # 1. 終極真實來源 (Source of Truth) 檢查：比對記憶體快取中的 A:\processed_md 產物
    try:
        stem = Path(f_path).stem
        stems_cache = get_processed_stems()
        matching_md = next((p for p in stems_cache if stem in p), None)
        
        if matching_md:
            srt_name = matching_md.replace('.md', '.srt')
            srt_path = Path("A:\\processed_md") / srt_name
            
            if not srt_path.exists():
                print(f"      [SRT 遺失] {srt_name} 不存在。判定為失敗重做。")
                return False
                
            srt_size_kb = srt_path.stat().st_size / 1024
            
            duration_min, _, _ = get_video_duration_and_size(f_path)
            if duration_min > 0:
                min_kb = max(5.0, duration_min * 0.6)
                max_kb = max(50.0, duration_min * 3.5) # increased max because some SRTs are 600KB+
                if min_kb <= srt_size_kb <= max_kb:
                    return True
                else:
                    print(f"      [SRT 異常] {srt_name} 大小 {srt_size_kb:.1f}KB 與時長 {duration_min:.1f}分鐘 不符。判定為失敗重做。")
                    return False
            return True
    except Exception:
        pass

    # 2. 若實體檔案不存在，退回檢查 JSON 紀錄檔
    if f_path not in history:
        return False
    try:
        current_hash = get_file_hash(f_path)
        if not current_hash:
            return False
        record = history[f_path]
        
        # 1. 優先使用 SHA-256 雜湊比對（黃金標準）
        if "hash" in record:
            if record["hash"] == current_hash:
                return True
        else:
            # 2. 相容舊版：比對大小與修改時間，若一致則補算並升級 hash 紀錄
            current_size = os.path.getsize(f_path)
            current_mtime = os.path.getmtime(f_path)
            if record.get("size") == current_size and record.get("mtime") == current_mtime:
                record["hash"] = current_hash
                save_ingested_history(history)
                return True
    except Exception:
        pass
    return False

def record_file_ingested(f_path, history):
    try:
        f_hash = get_file_hash(f_path)
        history[f_path] = {
            "size": os.path.getsize(f_path),
            "mtime": os.path.getmtime(f_path),
            "hash": f_hash,
            "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_ingested_history(history)
    except Exception:
        pass

def run_ingest(folders):
    """執行一鍵吸收與消化"""
    print("\n[Step 3] 開始全自動批次教材消化建置流程...")
    
    # 1. 收集資料夾下所有有效檔案
    valid_files_info = []
    seen_paths = set()
    
    for folder in folders:
        p_obj = Path(folder)
        if not p_obj.exists():
            continue
        # 遞迴掃描旗下所有支援的檔案
        for f in p_obj.rglob("*"):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
                abs_p = str(f.resolve())
                if abs_p not in seen_paths:
                    # 智能資料比對：分析是否是法律相關的資料來源，不逆向亂抓無關資料
                    if not is_file_content_legal(abs_p):
                        print(f"   [跳過無關檔案] {f.name} (經智慧防護判定非法律相關內容)")
                        continue
                    seen_paths.add(abs_p)
                    valid_files_info.append((f.name, abs_p, folder))
                    
    total = len(valid_files_info)
    if total == 0:
        print("   -> ❌ 未在此等資料夾下發現任何可消化的影音或文件教材！結束。")
        return
        
    print(f"   -> 收集完畢，共計 {total} 個教材檔案待處理。")
    
    # 刷新並產生給 Agent 看的總結報表
    generate_processed_report_table()
    
    # 產生比對報表 (Table)
    history = load_ingested_history()
    print("\n" + "="*85)
    print(" 📊 自動掃描檔案比對狀態總覽表 (Processed vs Unprocessed)")
    print("-" * 85)
    
    pending_files = []
    for disp_name, f_path, parent_folder in valid_files_info:
        is_processed = is_file_already_ingested(f_path, history)
        status_text = "[已處理 - 跳過]" if is_processed else "[待處理 - 佇列中]"
        
        # 簡單縮排處理以因應中文字元長度不定
        print(f" {status_text} | {Path(parent_folder).name} -> {disp_name}")
        
        if not is_processed:
            pending_files.append((disp_name, f_path, parent_folder))
            
    print("="*85)
    print(f"\n   -> 報表總結: 共找到 {total} 個檔案，其中 {total - len(pending_files)} 個已消化過，準備處理 {len(pending_files)} 個新檔案。")
    
    if not pending_files:
        print("   -> 🟢 所有檔案皆已處理完畢，無新檔案需消化！結束。")
        update_buffer_file([])
        return
        
    # 2. 初始化 AI 與處理器 (延後到確定有檔案要處理才載入，節省資源)
    print("   -> 正在初始化核心 AI 代理人與多模態處理器...")
    agent = LocalLegalAgent()
    processor = MultimodalLegalInput(model_size="small")
    analyzer = VisualLegalAnalyzer()
    
    transcripts_dir = "C:\\LocalAI_Workstation\\Transcripts"
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # 3. 逐一處理待辦檔案
    total_pending = len(pending_files)
    for idx, (disp_name, f_path, parent_folder) in enumerate(pending_files):
            
        print(f"\n------------------------------------------------------------")
        print(f" [進度: {idx+1} / {total}] 正在吸收: {disp_name}")
        print(f" 檔案路徑: {f_path}")
        print(f"------------------------------------------------------------")
        
        try:
            # 推定課程與課堂名稱 (依據資料夾結構)
            parent_dir = Path(f_path).parent
            grandparent_dir = parent_dir.parent if parent_dir else None
            
            lesson_name = parent_dir.name if parent_dir else "預設課堂"
            
            # 修復原本嚴重的邏輯錯誤，避免 class_name 被強制降級為 "預設課程"
            try:
                if grandparent_dir and grandparent_dir.name and not str(grandparent_dir).endswith(":\\") and str(grandparent_dir) != "/":
                    class_name = grandparent_dir.name
                else:
                    class_name = "預設課程"
            except Exception:
                class_name = "預設課程"
            
            p_file = Path(f_path)
            file_size_mb = os.path.getsize(f_path) / (1024 * 1024)
            
            raw_text = ""
            pages_list = []
            
            # 處理轉錄或 OCR
            if p_file.suffix.lower() in ['.mp3', '.mp4', '.wav']:
                print("   [1/3] 正在進行影音 Whisper 實時轉錄...")
                raw_text = processor.transcribe_audio(f_path)
                
                if p_file.suffix.lower() == '.mp4':
                    print("   [1.5] 偵測到影片，正在擷取板書圖表筆記...")
                    video_notes = analyzer.track_video_blackboard(f_path, class_name, lesson_name)
                    
                print("   [2/3] 正在使用 LLM 校正拼音與裁判錯字...")
                final_text = processor.post_refine_using_llm(raw_text)
            elif p_file.suffix.lower() == '.txt':
                with open(f_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                    raw_text = f_in.read(CHROMA_TEXT_LIMIT)
                print("   [2/3] 正在使用 LLM 進行校正...")
                final_text = processor.post_refine_using_llm(raw_text)
            else:
                print("   [1/3] 正在進行書面文件 OCR 辨識與視覺版面分析...")
                pages_list = processor.ocr_document(f_path)
                combined_ocr_text = "\n".join([p["text"] for p in pages_list])
                print("   [2/3] 正在使用 LLM 進行校正...")
                final_text = processor.post_refine_using_llm(combined_ocr_text)
                
            # 儲存逐字稿文字檔
            def sanitize_filename(name: str) -> str:
                for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    name = name.replace(char, '')
                return name.strip()
                
            out_filename = f"{sanitize_filename(class_name)}_{sanitize_filename(lesson_name)}_{sanitize_filename(p_file.stem)}_逐字稿.txt"
            out_filepath = os.path.join(transcripts_dir, out_filename)
            with open(out_filepath, "w", encoding="utf-8") as f_out:
                f_out.write(final_text)
            print(f"   -> [逐字稿存檔] {out_filepath}")
            
            # 摘要並上傳向量資料庫
            print("   [3/3] 正在利用大模型提煉核心爭點與推理路徑並建檔...")
            payload_prompt = f"分析以下文本，提煉出：核心爭點、推理路徑、結論：\n\n{final_text[:2000]}"
            res = agent.chat(payload_prompt) # 調用 agent 做推理
            summary = res[0] if isinstance(res, tuple) else str(res)
            
            # 儲存到智商庫
            safe_chroma_text = final_text[:CHROMA_TEXT_LIMIT]
            doc_to_store = f"【自動吸收消化精華】\n{summary}\n\n【原始校對文本】\n{safe_chroma_text}"
            doc_embedding = agent._get_embedding(doc_to_store)
            if doc_embedding:
                agent.intel_coll.add(
                    ids=[f"auto_ref_{p_file.name}_{idx}_{int(time.time())}"],
                    documents=[doc_to_store],
                    embeddings=[doc_embedding],
                    metadatas=[{"source": disp_name, "mode": "機器人全自動吸收", "size_mb": round(file_size_mb, 2), "type": "summary", "class_name": class_name, "lesson_name": lesson_name}]
                )
                print("   -> [成功] 向量智商庫 Upsert 成功，該教材已吸收完畢。")
                record_file_ingested(f_path, history)
                
            # 記憶體清理
            if 'raw_text' in locals(): del raw_text
            if 'final_text' in locals(): del final_text
            if 'pages_list' in locals(): del pages_list
            gc.collect()
            time.sleep(0.5)
            
        except Exception as file_e:
            print(f"   -> ❌ 教材 {disp_name} 消化失敗，原因: {file_e}")
            
    # 全數成功後清空快取
    update_buffer_file([])
    print("\n[Bot SUCCESS] 本批本機法律教材已全自動搜尋並吸收消化完畢！快取已清空。")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="本機法律教材全自動搜尋與一鍵吸收機器人")
    parser.add_argument("--dry-run", action="store_true", help="乾衣模式：僅掃描並列出符合條件的法律資料夾，不進行實際寫入與消化。")
    parser.add_argument("--path", type=str, default=None, help="指定掃描與吸取的路徑（精確位址，例如：H: 或 H:\\foo）")
    args = parser.parse_args()
    
    folders = scan_drives(scan_path=args.path)
    
    if not folders:
        print("\n❌ 本機磁碟中未找到任何名稱含有法律關鍵字且包含影音/文件的教材資料夾。")
        return
        
    print(f"\n本次共掃描出 {len(folders)} 個符合條件的法律資料夾。")
    
    if args.dry_run:
        print("\n[Mode: Dry-Run] 已成功列出所有符合的資料夾。乾衣模式結束，不進行寫入與消化。")
        return
        
    # 寫入介面快取，這樣前台重新整理時能看見
    update_buffer_file(folders)
    
    # 執行全自動吸收
    run_ingest(folders)

if __name__ == "__main__":
    main()

