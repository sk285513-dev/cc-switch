import os
import sys

sys.path.append("C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6")
from auto_ingest_bot import scan_drives, is_file_content_legal, SUPPORTED_EXTS

test_dir = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/sandbox_test_strict"
os.makedirs(test_dir, exist_ok=True)

# Create mock files
mock_files = [
    "民事訴訟法_第01講.mp4",        # Valid (Law + Course)
    "生活法律諮詢_民法.mp3",        # Invalid (Law only, no Course keyword)
    "我的家事紀錄.mp4",             # Invalid (Law '家事' only, no Course keyword)
    "高點_行政法_總複習.wav",       # Valid (Law + Course)
    "行政法_重點.txt",              # Invalid (Extension txt)
    "完全無關的純音樂.wav"          # Invalid (None)
]

print("=== 1. 建立嚴格沙盒測試環境 ===")
for f in mock_files:
    path = os.path.join(test_dir, f)
    with open(path, 'w') as file:
        file.write("mock content")
    print(f"建立測試檔案: {f}")

print("\n=== 2. 測試檔案合法性判定 (雙重驗證: 科目+課程特徵) ===")
for f in mock_files:
    path = os.path.join(test_dir, f)
    ext = os.path.splitext(f)[1].lower()
    is_supported = ext in SUPPORTED_EXTS
    is_legal = is_file_content_legal(path)
    status = "✅ 放行" if is_supported and is_legal else "❌ 阻擋"
    print(f"[{status}] {f} ")

print("\n=== 清理環境 ===")
for f in mock_files:
    os.remove(os.path.join(test_dir, f))
os.rmdir(test_dir)
print("測試完成！")
