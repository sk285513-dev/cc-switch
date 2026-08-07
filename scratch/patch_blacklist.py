import re

# 1. Patch auto_ingest_bot.py
file_path = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6/auto_ingest_bot.py"
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Delete txt, md, pdf semantic parsing completely to stop recursive ingestion of outputs
text = re.sub(r"^\s*# 2\. 如果檔名特徵不足，針對文本檔/PDF讀取內容進行語意分析.*?elif ext == '\.pdf':.*?pass\n", "", text, flags=re.MULTILINE | re.DOTALL)
# Also need to handle the rest of the pdf block
text = re.sub(r"^\s*# 2\. 如果檔名特徵不足.*?pass\s*\n", "", text, flags=re.MULTILINE | re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)


# 2. Patch file_watcher.py
file_path2 = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6/file_watcher.py"
with open(file_path2, 'r', encoding='utf-8') as f:
    text2 = f.read()

# Add blacklist check
old_scan = '''    for item in raw_path.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            abs_item_path = os.path.abspath(str(item))'''

new_scan = '''    for item in raw_path.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            # 加入檔名黑名單過濾，阻擋切片與暫存檔 (解決遞迴與 KPI 統計異常)
            fname = item.name.lower()
            if any(bad in fname for bad in ["chunk_", "temp_", "extracted_", "_chunks"]):
                continue
            
            abs_item_path = os.path.abspath(str(item))'''
            
text2 = text2.replace(old_scan, new_scan)

with open(file_path2, 'w', encoding='utf-8') as f:
    f.write(text2)

print("Patch applied to both files.")
