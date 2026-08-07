import os
import sys
import json
import time

sys.path.append("C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6")
from auto_ingest_bot import is_file_already_ingested, record_file_ingested, get_file_hash, HISTORY_FILE

print("=== 1. 初始化防重複過濾測試 ===")
# 清除舊的測試 history
if os.path.exists(HISTORY_FILE):
    os.remove(HISTORY_FILE)

test_file = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6/test_data/測試課程_民事訴訟法.mp4"
os.makedirs(os.path.dirname(test_file), exist_ok=True)
with open(test_file, 'w') as f:
    f.write("mock media content bytes")

history = {}

print(f"\n[第一次掃描] 檔案: {os.path.basename(test_file)}")
is_processed = is_file_already_ingested(test_file, history)
if not is_processed:
    print("✅ 結果: 尚未處理過，允許進入吸收管線！")
    print("-> 模擬吸收完畢，將檔案寫入 history...")
    record_file_ingested(test_file, history)
else:
    print("❌ 結果: 已經處理過，跳過。")

print(f"\n[第二次掃描] (同一檔案，內容不變)")
is_processed2 = is_file_already_ingested(test_file, history)
if is_processed2:
    print("❌ 結果: 成功攔截！系統發現已存在於 ingested_history.json，跳過重複吸收。")
else:
    print("✅ 結果: 錯誤，沒有攔截到！")

print(f"\n[第三次掃描] (同一檔案，但內容發生改變：假設被覆蓋為新檔案)")
# 改變檔案內容以改變 Hash
with open(test_file, 'w') as f:
    f.write("mock media content bytes WITH NEW DATA")

is_processed3 = is_file_already_ingested(test_file, history)
if not is_processed3:
    print("✅ 結果: 成功放行！系統偵測到 Hash 值改變，視為新版本重新吸收。")
else:
    print("❌ 結果: 錯誤，依然被攔截！")

print("\n=== 清理測試環境 ===")
os.remove(test_file)
if os.path.exists(HISTORY_FILE):
    os.remove(HISTORY_FILE)
print("測試完成！")
