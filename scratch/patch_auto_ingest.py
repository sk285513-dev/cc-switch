import re

file_path = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6/auto_ingest_bot.py"
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add COURSE_KEYWORDS
course_kws = '''LAW_KEYWORDS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法"]
COURSE_KEYWORDS = ["第", "講", "堂", "ch", "chapter", "課程", "總複習", "正規班", "爭點班", "解題班", "題庫班", "函授", "面授", "高點", "保成", "讀享", "學稔", "司律", "司法官", "律師"]'''
text = text.replace('LAW_KEYWORDS = ["憲法", "民法", "身分法", "刑法", "行政法", "程序法", "民事訴訟法", "刑事訴訟法", "家事事件法", "民訴", "刑訴", "家事", "土地法", "土地法規", "商事法", "公司法", "票據法", "證交法", "證券交易法", "稅法"]', course_kws)

# 2. Update is_file_content_legal Step 3
old_step_3 = '''    # 3. 影音與圖像檔案在尚未進行 ASR/OCR 之前僅以路徑做為防護線，必須在完整路徑中包含法律關鍵字
    if ext in {'.png', '.jpg', '.jpeg', '.mp3', '.mp4', '.wav'}:
        if any(kw.lower() in f_path_lower for kw in LAW_KEYWORDS):
            return True'''

new_step_3 = '''    # 3. 影音與圖像檔案在尚未進行 ASR/OCR 之前僅以路徑做為防護線，必須在完整路徑中同時包含【法律科目】與【課程特徵】
    if ext in {'.png', '.jpg', '.jpeg', '.mp3', '.mp4', '.wav'}:
        has_law = any(kw.lower() in f_path_lower for kw in LAW_KEYWORDS)
        has_course = any(kw.lower() in f_path_lower for kw in COURSE_KEYWORDS)
        if has_law and has_course:
            return True'''
text = text.replace(old_step_3, new_step_3)

# 3. Update scan_drives logic
old_scan_1 = '''            # 檢查完整路徑是否含有法律相關關鍵字 (解決課程名稱通常建立在父資料夾的實務情況)
            folder_matches = any(kw in root for kw in LAW_KEYWORDS)
            
            has_valid_media = False
            file_matches = False
            
            try:
                # 遍歷旗下檔案
                for f in os.listdir(root):
                    f_ext = os.path.splitext(f)[1].lower()
                    if f_ext in SUPPORTED_EXTS:
                        has_valid_media = True
                        # 如果檔案名稱包含法律關鍵字
                        if any(kw in f for kw in LAW_KEYWORDS):
                            file_matches = True
            except Exception:
                pass
                
            # 雙重特徵匹配：資料夾名稱匹配且含有媒體，或檔案本身符合媒體且名稱匹配
            if has_valid_media and (folder_matches or file_matches):'''

new_scan_1 = '''            # 檢查完整路徑是否含有法律相關關鍵字 (解決課程名稱通常建立在父資料夾的實務情況)
            folder_has_law = any(kw in root for kw in LAW_KEYWORDS)
            folder_has_course = any(kw.lower() in root.lower() for kw in COURSE_KEYWORDS)
            
            has_valid_media = False
            file_matches = False
            
            try:
                # 遍歷旗下檔案
                for f in os.listdir(root):
                    f_ext = os.path.splitext(f)[1].lower()
                    if f_ext in SUPPORTED_EXTS:
                        has_valid_media = True
                        # 如果檔案名稱包含法律關鍵字
                        f_lower = f.lower()
                        has_file_law = any(kw in f for kw in LAW_KEYWORDS)
                        has_file_course = any(kw in f_lower for kw in COURSE_KEYWORDS)
                        if has_file_law and has_file_course:
                            file_matches = True
            except Exception:
                pass
                
            # 嚴格雙重特徵匹配：(資料夾具備法律+課程特徵) 或 (檔案本身具備法律+課程特徵)
            if has_valid_media and ((folder_has_law and folder_has_course) or file_matches):'''
text = text.replace(old_scan_1, new_scan_1)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("auto_ingest_bot.py strict filters patched successfully!")
