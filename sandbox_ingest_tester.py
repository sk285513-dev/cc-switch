import os
import sys

# Ensure imports work
sys.path.append("C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/scripts_v6")
from auto_ingest_bot import scan_drives, is_file_content_legal, SUPPORTED_EXTS

test_dir = "C:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/sandbox_test_data"
os.makedirs(test_dir, exist_ok=True)

# Create mock files
mock_files = [
    "民事訴訟法_第01講.mp4",        # Valid law video
    "我的暑假日記_無關.mp4",        # Invalid non-law video
    "土地法規_重點複習.mp3",        # Valid law audio
    "土地法規_重點複習.txt",        # Invalid extension (txt)
    "刑法_總則_課程.wav",           # Valid law audio
    "完全無關的純音樂.wav"          # Invalid non-law audio
]

print("=== 1. 建立測試沙盒環境 ===")
for f in mock_files:
    path = os.path.join(test_dir, f)
    with open(path, 'w') as file:
        file.write("mock content")
    print(f"建立測試檔案: {f}")

print("\n=== 2. 測試檔案合法性判定 (is_file_content_legal) ===")
for f in mock_files:
    path = os.path.join(test_dir, f)
    ext = os.path.splitext(f)[1].lower()
    is_supported = ext in SUPPORTED_EXTS
    is_legal = is_file_content_legal(path)
    status = "✅ 允許吸入" if is_supported and is_legal else "❌ 阻擋吸入"
    print(f"[{status}] {f} (副檔名合法: {is_supported}, 內容/檔名合法: {is_legal})")

print("\n=== 3. 測試 scan_drives 掃描過濾結果 ===")
# Capture stdout to prevent clutter if needed, or just let it print
results = scan_drives(test_dir)
print(f"\nScan Results (Valid Folders Found): {results}")

# Clean up
for f in mock_files:
    os.remove(os.path.join(test_dir, f))
os.rmdir(test_dir)
print("\n沙盒測試完成並清理完畢！")
