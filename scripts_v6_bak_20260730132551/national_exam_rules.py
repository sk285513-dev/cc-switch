# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 1: 領域防護與前端物流 (Ingestion & Rules)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 1】。
# 作為系統唯一真相來源 (SSOT)，負責掃描、吸收及國考權重判定與黑白名單。
# 任何打分邏輯或科目變更，唯一只能修改此腳本。修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import os
import re
import subprocess

# 單一真相來源 (SSOT): 國家考試科目權重邏輯
# 分數越低優先權越高
NATIONAL_EXAM_WEIGHTS = {
    "憲法": 10,
    "身分法": 20,
    "民法": 20,
    "刑法": 25,
    "行政法": 30,
    "民事訴訟法": 40,
    "民訴": 40,
    "刑事訴訟法": 40,
    "刑訴": 40,
    "家事事件法": 40,
    "家事": 40,
    "土地法規": 50,
    "土地法": 50,
    "公司法": 60,
    "票據法": 60,
    "證券交易法": 60,
    "證交法": 60,
    "稅法": 60,
}

# 副檔名白名單
SUPPORTED_EXTS = {'.mp3', '.mp4', '.wav'}  # 嚴格依照使用者要求：規定除非有特殊原因，否則預設就是只能吸入國家考試「司法官與律師」等法律相關專業科目的純影音格式

# 法律相關專業科目白名單
LAW_KEYWORDS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法", "強制執行法", "智慧財產權法", "土地稅法", "土地登記", "不動產估價", "立法程序與技術", "法院組織法", "海商法", "海洋法", "勞動社會法", "關稅法規"]

# 廣義法律關鍵字 (供外部爬蟲使用)
SCRAPER_LAW_KEYWORDS = ["法律", "法規", "法庭", "訴訟", "案情", "教材", "民法", "刑法", "行政法", "家事", "司法", "考官", "律師", "刑事", "民事", "開庭", "法學", "判決", "起訴", "憲法", "條文", "契約", "侵權", "時效", "抗辯", "答辯", "裁判", "罪"]

# 封殺黑名單
BLACKLIST = ["法規庫", "空大", "協調", "不動產經紀", "房仲", "法院證物"]

# 台灣法律特有正則特徵
TAIWAN_LEGAL_PATTERNS = [
    r"\d+\s*年\s*[^\d\s]+\s*字第\s*\d+\s*號",  # 裁判字號，例如 112年上字第10號
    r"第\s*\d+\s*條",                       # 法條，例如 第197條
    r"民法|刑法|民事訴訟法|刑事訴訟法|行政程序法|司法院|法院|最高法院|檢察署|檢察官|起訴書|判決書|裁定書|訴狀|聲請書|答辯狀"
]

def get_exam_score(subject_name: str) -> int:
    """
    依據科目名稱回傳國考權重分數。
    分數越小代表優先級越高 (10 分為最高優先級)。
    如果非國考科目，則回傳 999 視為最低優先級。
    """
    if not subject_name:
        return 999
        
    score = 999
    for subject, weight in NATIONAL_EXAM_WEIGHTS.items():
        if subject in subject_name:
            if weight < score:
                score = weight
    return score

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

def get_usb_drives():
    """動態偵測並回傳目前所有插在電腦上的外接 USB 磁碟機代號 (例如 ['H:\\', 'J:\\'])，絕對排除內建硬碟"""
    cmd = "Get-Partition | Where-Object { $_.DriveLetter } | Select-Object DriveLetter, @{Name='BusType';Expression={(Get-Disk -Number $_.DiskNumber).BusType}} | Where-Object { $_.BusType -eq 'USB' } | Select-Object -ExpandProperty DriveLetter"
    try:
        # 使用 CREATE_NO_WINDOW (0x08000000) 避免彈出黑色視窗
        result = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, creationflags=0x08000000)
        drives = result.stdout.strip().split('\n')
        usb_list = [f"{d.strip()}:\\" for d in drives if d.strip()]
        return usb_list
    except Exception as e:
        print(f"Error detecting USB drives: {e}")
        return []

def is_file_content_legal(f_path):
    """智能分析檔案名稱、路徑或實際內容，精確判別是否為法律教材，杜絕亂抓資料"""
    f_path_lower = str(f_path).lower()
    f_name = os.path.basename(f_path_lower)
    ext = os.path.splitext(f_path_lower)[1]
    
    # 0. 絕對封殺黑名單 (私人協調錄音、空大、房仲、法規庫等雜訊)
    if any(bl in f_path_lower for bl in BLACKLIST):
        return False
    
    # 1. 首先檢查路徑或檔名是否包含國家考試科目 (無條件放行)
    for subject in NATIONAL_EXAM_WEIGHTS.keys():
        if subject.lower() in f_path_lower:
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
            for i in range(min(3, len(reader.pages))):
                text = reader.pages[i].extract_text()
                if text:
                    pages_text.append(text)
            if check_text_for_legal_relevance("\n".join(pages_text)):
                return True
        except ImportError:
            # 如果沒有 pypdf，依賴檔名判斷
            pass
        except Exception:
            pass
            
    return False
