import re

file_path = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6/auto_ingest_bot.py"
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

old_func = '''def is_file_content_legal(f_path):
    """智能分析檔案名稱、路徑或實際內容，精確判別是否為法律教材，杜絕亂抓資料"""
    f_path_lower = str(f_path).lower()
    f_name = os.path.basename(f_path_lower)'''

new_func = '''def is_file_content_legal(f_path):
    """智能分析檔案名稱、路徑或實際內容，精確判別是否為法律教材，杜絕亂抓資料"""
    f_path_lower = str(f_path).lower()
    f_name = os.path.basename(f_path_lower)
    
    # [黑名單防護]：絕對禁止吸入任何系統產生的暫存檔、切片檔與輸出檔案，防止遞迴與 KPI 統計異常
    if any(bad in f_name for bad in ["chunk_", "temp_", "extracted_", "_chunks", "逐字稿"]):
        return False
'''

text = text.replace(old_func, new_func)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("auto_ingest_bot blacklist added.")
